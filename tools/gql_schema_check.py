#!/usr/bin/env python3
"""
Static schema check for the hand-coded `reporting` GraphQL queries.

Why this exists
---------------
The `reporting` group is hand-coded against the CCC GraphQL endpoint
(``POST /api/reporting/v1/data``), which is deliberately NOT in the OpenAPI
spec. It is therefore **not regenerated** when the spec is bumped — so a CCC
release can change the GraphQL schema underneath it while every static check we
own stays green: the suite passes, the spec diff is clean, the generated code is
correct, and the commands are dead on arrival against the live tenant.

That is exactly what CCC 26.7 did:

  * ``zeroTrustMetrics(macAddress: …)`` moved into a ``filters`` input object
    → ``Validation error (UnknownArgument@[policyMetrics/zeroTrustMetrics])``
  * ``countNeeded`` and ``policySetEnforcementScore`` were removed outright
    → ``Validation error (FieldUndefined@[policyMetrics/countNeeded])``

This module closes that hole. It parses every GraphQL query literal in
``commands/reporting.py`` and validates the fields and arguments it selects
against a **staged introspection** of the live schema, so the next schema drift
fails the suite instead of shipping.

Arguments AND selection sets
----------------------------
The first version of this check validated arguments and stopped at the first
return type it had no staging for. That let the SECOND CCC 26.7 breakage through
untouched: ``zeroTrustMetrics``'s own arguments were correct, so the check
passed, while the *fields it selected* — ``avgDeviceCoverage`` and
``avgPolicyCoverage`` — no longer existed on ``ZeroTrustMetrics`` and the server
rejected the query one layer deeper::

    Validation error (FieldUndefined@[policyMetrics/zeroTrustMetrics/avgDeviceCoverage])

A check that reports UNVERIFIED for the part that actually broke is not much
better than no check. So this module now:

* validates **every selected field at every depth**, following return types
  through the staged type graph;
* resolves **named fragments and inline fragments** against their type
  condition, instead of parsing and discarding them;
* counts **field paths**, not just queries, so the coverage denominator is the
  thing that matters — "how many of the N fields we actually select did we
  check", not "how many queries mention a root we know";
* **fails** when a type listed in ``REQUIRED_STAGED_TYPES`` is missing from the
  staged schema, so coverage cannot silently shrink back to the state that let
  the reshape through. Deleting staging is a test failure, not a quieter report.

Honest coverage
---------------
Only types we have staged introspection for are *checked*. Everything else is
reported as ``UNVERIFIED`` — never silently as passing. ``--json`` emits the
full per-query breakdown plus the field-path denominator, so "what fraction of
what we send did we verify" is always visible rather than assumed.

Two limits this check cannot see, stated so nobody reads a PASS as more than it
is: it does not execute anything against a live tenant, and the staged
introspection carries field names only, not type *kinds* — so it cannot tell
that a selected field is an object needing a sub-selection (or a scalar that
must not have one). Both are settled only by a live run.

    python3 tools/gql_schema_check.py            # human-readable, exit 1 on error
    python3 tools/gql_schema_check.py --json
    python3 tools/gql_schema_check.py --schema <introspection.json>
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTING_MODULE = REPO_ROOT / "src" / "elisity_cli" / "commands" / "reporting.py"
DEFAULT_SCHEMA = REPO_ROOT / "tests" / "data" / "ccc-26.7-reporting-introspection.json"

# Root-level query fields we have a staged type for. The reporting endpoint
# exposes four metric domains; only `policyMetrics` has been introspected, and
# it is the one all three 26.7 breakages lived in. Add an entry here (plus its
# staged introspection) to widen coverage.
ROOT_FIELD_TYPES = {"policyMetrics": "PolicyMetrics"}

# The other three roots are known to exist but are unintrospected. Listing them
# explicitly means a *typo'd* root (e.g. `polcyMetrics`) is still an error,
# rather than being waved through as "unverified".
KNOWN_UNVERIFIED_ROOTS = {
    "identityGraphMetrics",
    "topologyMetrics",
    "trafficVectorsMetrics",
}

# Types the staged schema MUST contain. Every one of these is a type a shipped
# query selects fields on; if staging for it disappears, those fields stop being
# checked and this module would go on printing PASS over a shrinking
# denominator. That is precisely how the 26.7 reshape shipped, so it is an
# error rather than a softer report.
REQUIRED_STAGED_TYPES = frozenset({
    "PolicyMetrics",
    "ZeroTrustMetrics",
    "PolicyDeploymentMetrics",
    "L4Metrics",
    "ThreatVectorMetrics",
})


# --------------------------------------------------------------------------
# A minimal GraphQL query parser
# --------------------------------------------------------------------------
# Only the subset our queries use: operations with variable definitions,
# selection sets, arguments, directives, fragment definitions/spreads and
# inline fragments. Deliberately dependency-free — graphql-core is not a
# dependency of this CLI and one static check does not justify adding it.

_TOKEN_RE = re.compile(
    r"""
      (?P<skip>[\s,]+|\#[^\n]*)
    | (?P<spread>\.\.\.)
    | (?P<string>"(?:\\.|[^"\\])*")
    | (?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
    | (?P<name>[_A-Za-z][_0-9A-Za-z]*)
    | (?P<punct>[{}()\[\]:$@=!])
    """,
    re.VERBOSE,
)


class GraphQLParseError(ValueError):
    """The query literal is not GraphQL we can parse."""


class Field:
    """One selected field: its name, the argument NAMES it passes, subfields."""

    __slots__ = ("name", "alias", "arguments", "selections")

    def __init__(self, name, alias=None):
        self.name = name
        self.alias = alias
        self.arguments = []
        self.selections = []

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<Field {self.name} args={self.arguments} sel={len(self.selections)}>"


class FragmentSpread:
    """`...SomeFragment` — resolved against the document's fragment definitions."""

    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<Spread ...{self.name}>"


class InlineFragment:
    """`... on SomeType { … }` — validated against its type condition."""

    __slots__ = ("type_condition", "selections")

    def __init__(self, type_condition, selections):
        self.type_condition = type_condition
        self.selections = selections

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"<Inline on {self.type_condition} sel={len(self.selections)}>"


class Fragment:
    """A named fragment definition: `fragment F on T { … }`."""

    __slots__ = ("name", "type_condition", "selections")

    def __init__(self, name, type_condition, selections):
        self.name = name
        self.type_condition = type_condition
        self.selections = selections


class Document:
    """Parsed GraphQL document: top-level selections + fragment definitions."""

    __slots__ = ("selections", "fragments")

    def __init__(self, selections, fragments):
        self.selections = selections
        self.fragments = fragments


def _tokenize(source):
    tokens, pos, end = [], 0, len(source)
    while pos < end:
        match = _TOKEN_RE.match(source, pos)
        if not match:
            raise GraphQLParseError(f"unexpected character {source[pos]!r} at offset {pos}")
        pos = match.end()
        if match.lastgroup == "skip":
            continue
        tokens.append((match.lastgroup, match.group()))
    return tokens


class _Parser:
    def __init__(self, source):
        self.tokens = _tokenize(source)
        self.i = 0

    # -- token helpers ----------------------------------------------------
    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def next(self):
        token = self.peek()
        self.i += 1
        return token

    def at(self, value):
        return self.peek()[1] == value

    def expect(self, value):
        kind, text = self.next()
        if text != value:
            raise GraphQLParseError(f"expected {value!r}, got {text!r}")
        return text

    # -- grammar ----------------------------------------------------------
    def parse_document(self):
        """Return a Document: top-level selections + every fragment definition.

        Fragments are kept, not discarded. The dashboard's Zero Trust query puts
        its entire threat-vector selection behind `...ThreatVectorMetricsFields`,
        so a checker that throws fragments away cannot see a whole branch of
        what it claims to validate.
        """
        selections, fragments = [], {}
        while self.peek()[0] is not None:
            _, text = self.peek()
            if text == "fragment":
                fragment = self.parse_fragment_definition()
                fragments[fragment.name] = fragment
            elif text in ("query", "mutation", "subscription"):
                self.next()
                if self.peek()[0] == "name":
                    self.next()  # operation name
                if self.at("("):
                    self.skip_balanced("(", ")")
                self.skip_directives()
                selections.extend(self.parse_selection_set())
            elif text == "{":  # anonymous operation
                selections.extend(self.parse_selection_set())
            else:
                raise GraphQLParseError(f"unexpected top-level token {text!r}")
        return Document(selections, fragments)

    def parse_fragment_definition(self):
        self.expect("fragment")
        name = self.next()[1]
        self.expect("on")
        type_condition = self.next()[1]
        self.skip_directives()
        return Fragment(name, type_condition, self.parse_selection_set())

    def parse_selection_set(self):
        self.expect("{")
        selections = []
        while not self.at("}"):
            if self.peek()[0] is None:
                raise GraphQLParseError("unterminated selection set")
            if self.peek()[0] == "spread":
                self.next()
                if self.at("on"):  # inline fragment
                    self.next()
                    type_condition = self.next()[1]
                    self.skip_directives()
                    selections.append(
                        InlineFragment(type_condition, self.parse_selection_set())
                    )
                else:
                    spread_name = self.next()[1]
                    self.skip_directives()
                    selections.append(FragmentSpread(spread_name))
                continue
            selections.append(self.parse_field())
        self.expect("}")
        return selections

    def parse_field(self):
        kind, name = self.next()
        if kind != "name":
            raise GraphQLParseError(f"expected a field name, got {name!r}")
        alias = None
        if self.at(":"):
            self.next()
            alias, name = name, self.next()[1]
        field = Field(name, alias)
        if self.at("("):
            field.arguments = self.parse_arguments()
        self.skip_directives()
        if self.at("{"):
            field.selections = self.parse_selection_set()
        return field

    def parse_arguments(self):
        """Collect argument NAMES. Values are skipped — the schema check is
        about which arguments exist, and the values are runtime variables."""
        self.expect("(")
        names = []
        while not self.at(")"):
            if self.peek()[0] is None:
                raise GraphQLParseError("unterminated argument list")
            kind, text = self.next()
            if kind != "name":
                raise GraphQLParseError(f"expected an argument name, got {text!r}")
            names.append(text)
            self.expect(":")
            self.skip_value()
        self.expect(")")
        return names

    def skip_value(self):
        if self.at("$"):
            self.next()
            self.next()
            return
        if self.at("["):
            self.skip_balanced("[", "]")
            return
        if self.at("{"):
            self.skip_balanced("{", "}")
            return
        self.next()

    def skip_directives(self):
        while self.at("@"):
            self.next()
            self.next()  # directive name
            if self.at("("):
                self.skip_balanced("(", ")")

    def skip_balanced(self, open_token, close_token):
        self.expect(open_token)
        depth = 1
        while depth:
            kind, text = self.next()
            if kind is None:
                raise GraphQLParseError(f"unbalanced {open_token}")
            if text == open_token:
                depth += 1
            elif text == close_token:
                depth -= 1


def parse_query(source):
    """Parse a GraphQL document. Returns a :class:`Document`."""
    return _Parser(source).parse_document()


# --------------------------------------------------------------------------
# Schema loading
# --------------------------------------------------------------------------


def _unwrap_type_name(type_node):
    """Peel NON_NULL / LIST wrappers down to the named type, if any."""
    while isinstance(type_node, dict):
        name = type_node.get("name")
        if name:
            return name
        type_node = type_node.get("ofType") or {}
        if not type_node:
            return None
    return None


def load_schema(path=DEFAULT_SCHEMA):
    """Load staged introspection into {typeName: {fieldName: {...}}}.

    Accepts the verbatim response of
    ``{ __type(name: "X") { fields { name args { name type } type } } }`` —
    either a single response object or a list of them, so widening coverage is
    a matter of appending another introspection payload.
    """
    payload = json.loads(Path(path).read_text())
    responses = payload if isinstance(payload, list) else [payload]

    types = {}
    for response in responses:
        node = response.get("data", response).get("__type") or {}
        type_name = node.get("name")
        if not type_name:
            raise ValueError(f"{path}: introspection payload has no __type.name")
        types[type_name] = {
            field["name"]: {
                "args": {arg["name"] for arg in field.get("args") or []},
                "type": _unwrap_type_name(field.get("type")),
            }
            for field in node.get("fields") or []
        }
    return types


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def _count_leaves(selections, fragments, seen=None):
    """How many field paths a selection subtree contains, fragments included.

    Used as the denominator: an unchecked subtree must be reported as the N
    fields it really is, not as one line that looks like a single gap.
    """
    seen = set() if seen is None else seen
    total = 0
    for node in selections:
        if isinstance(node, FragmentSpread):
            if node.name in seen:            # cyclic spread — count it once
                continue
            fragment = fragments.get(node.name)
            if fragment is not None:
                total += _count_leaves(fragment.selections, fragments, seen | {node.name})
            continue
        if isinstance(node, InlineFragment):
            total += _count_leaves(node.selections, fragments, seen)
            continue
        total += 1 + _count_leaves(node.selections, fragments, seen)
    return total


def validate_selections(selections, type_name, schema, path, fragments, stats,
                        active_fragments=frozenset()):
    """Validate a selection set against `type_name`, recursing where we can.

    Returns (errors, unverified). `unverified` records every path we could not
    check, with the number of field paths it covers, so coverage is never
    overstated. `stats` accumulates {"verified": n, "unverified": n} over field
    paths — the denominator the report prints.
    """
    errors, unverified = [], []
    for node in selections:
        if isinstance(node, FragmentSpread):
            fragment = fragments.get(node.name)
            if fragment is None:
                errors.append({
                    "kind": "UnknownFragment",
                    "path": path,
                    "message": f"fragment '{node.name}' is spread but never defined",
                })
                continue
            if node.name in active_fragments:   # cycle: GraphQL forbids it
                errors.append({
                    "kind": "CyclicFragment",
                    "path": path,
                    "message": f"fragment '{node.name}' spreads into itself",
                })
                continue
            # A fragment's type condition is what its body is validated against.
            # Where it matches the type we are already in, nothing changes; where
            # it names another type, that type is the correct context.
            sub_errors, sub_unverified = validate_selections(
                fragment.selections, fragment.type_condition, schema, path,
                fragments, stats, active_fragments | {node.name},
            )
            errors.extend(sub_errors)
            unverified.extend(sub_unverified)
            continue

        if isinstance(node, InlineFragment):
            sub_errors, sub_unverified = validate_selections(
                node.selections, node.type_condition, schema, path, fragments,
                stats, active_fragments,
            )
            errors.extend(sub_errors)
            unverified.extend(sub_unverified)
            continue

        child_errors, child_unverified = _validate_field(
            node, type_name, schema, f"{path}/{node.name}", fragments, stats,
            active_fragments,
        )
        errors.extend(child_errors)
        unverified.extend(child_unverified)

    return errors, unverified


def _validate_field(field, type_name, schema, path, fragments, stats,
                    active_fragments=frozenset()):
    """Validate one field against `type_name`, then recurse into its selections."""
    errors, unverified = [], []
    type_fields = schema.get(type_name)

    if type_fields is None:
        covered = 1 + _count_leaves(field.selections, fragments)
        stats["unverified"] += covered
        unverified.append({
            "path": path,
            "fields": covered,
            "reason": (
                f"type {type_name or '(unnamed)'} not introspected — "
                f"{covered} field path(s) unchecked"
            ),
        })
        return errors, unverified

    if field.name.startswith("__"):
        # `__typename` and friends are meta-fields valid on every object type
        # and are not part of a type's introspected field set.
        stats["verified"] += 1
        return errors, unverified

    definition = type_fields.get(field.name)
    if definition is None:
        stats["verified"] += 1
        errors.append(
            {
                "kind": "FieldUndefined",
                "path": path,
                "message": f"field '{field.name}' does not exist on {type_name}",
            }
        )
        return errors, unverified

    stats["verified"] += 1
    for argument in field.arguments:
        if argument not in definition["args"]:
            errors.append(
                {
                    "kind": "UnknownArgument",
                    "path": path,
                    "message": (
                        f"unknown argument '{argument}' on {type_name}.{field.name} "
                        f"(valid: {sorted(definition['args']) or 'none'})"
                    ),
                }
            )

    if field.selections:
        # `type` is None when the staged payload did not resolve the return type
        # name; passing it down produces one honest unverified entry per child
        # rather than a silent pass.
        child_errors, child_unverified = validate_selections(
            field.selections, definition["type"], schema, path, fragments, stats,
            active_fragments,
        )
        errors.extend(child_errors)
        unverified.extend(child_unverified)
    return errors, unverified


def validate_document(source, schema):
    """Validate one GraphQL document. Returns a per-document result dict."""
    errors, unverified, verified_paths = [], [], []
    stats = {"verified": 0, "unverified": 0}
    document = parse_query(source)
    fragments = document.fragments

    for root in document.selections:
        if not isinstance(root, Field):
            errors.append({
                "kind": "UnknownRoot",
                "path": "(fragment at operation root)",
                "message": "a fragment cannot be an operation's root selection",
            })
            continue
        type_name = ROOT_FIELD_TYPES.get(root.name)
        if type_name is None:
            covered = 1 + _count_leaves(root.selections, fragments)
            if root.name in KNOWN_UNVERIFIED_ROOTS:
                stats["unverified"] += covered
                unverified.append({
                    "path": root.name,
                    "fields": covered,
                    "reason": f"root type not introspected — {covered} field path(s) unchecked",
                })
            else:
                errors.append(
                    {
                        "kind": "UnknownRoot",
                        "path": root.name,
                        "message": (
                            f"'{root.name}' is not a known reporting root "
                            f"(known: {sorted(ROOT_FIELD_TYPES) + sorted(KNOWN_UNVERIFIED_ROOTS)})"
                        ),
                    }
                )
            continue
        # The root field *returns* the staged type, so its children are what we
        # validate against it (`policyMetrics { zeroTrustMetrics(...) }`).
        verified_paths.append(root.name)
        stats["verified"] += 1
        root_errors, root_unverified = validate_selections(
            root.selections, type_name, schema, root.name, fragments, stats,
        )
        errors.extend(root_errors)
        unverified.extend(root_unverified)

    # Every fragment the document defines must actually be reachable; a stale
    # one is dead weight that stops being validated the moment its last spread
    # is deleted.
    unused = sorted(set(fragments) - _spread_names(document))
    for name in unused:
        errors.append({
            "kind": "UnusedFragment",
            "path": name,
            "message": (
                f"fragment '{name}' is defined but never spread — the server "
                "rejects an unused fragment definition"
            ),
        })

    return {
        "errors": errors,
        "unverified": unverified,
        "verifiedRoots": verified_paths,
        "fieldPaths": dict(stats),
    }


def _spread_names(document):
    """Every fragment name spread anywhere in the document (fragments included)."""
    found = set()

    def walk(selections):
        for node in selections:
            if isinstance(node, FragmentSpread):
                if node.name not in found:
                    found.add(node.name)
                    fragment = document.fragments.get(node.name)
                    if fragment is not None:
                        walk(fragment.selections)
            elif isinstance(node, InlineFragment):
                walk(node.selections)
            else:
                walk(node.selections)

    walk(document.selections)
    return found


# --------------------------------------------------------------------------
# Query extraction
# --------------------------------------------------------------------------


def extract_queries(module_path=REPORTING_MODULE):
    """Return {constantName: querySource} for every module-level ``*_QUERY``.

    Uses the AST rather than a regex so a query added tomorrow is picked up
    automatically — the check must not depend on someone remembering to
    register it.
    """
    tree = ast.parse(Path(module_path).read_text())
    queries = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Name)
                and target.id.endswith("_QUERY")
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                queries[target.id] = node.value.value
    return queries


def missing_required_types(schema):
    """Staged types a shipped query depends on that are absent from the schema."""
    return sorted(REQUIRED_STAGED_TYPES - set(schema))


def check_module(module_path=REPORTING_MODULE, schema_path=DEFAULT_SCHEMA):
    """Check every query literal in a command module. Returns a report dict."""
    schema = load_schema(schema_path)
    queries = extract_queries(module_path)

    results, error_count, verified_count = {}, 0, 0
    verified_fields, unverified_fields = 0, 0
    for name, source in sorted(queries.items()):
        result = validate_document(source, schema)
        results[name] = result
        error_count += len(result["errors"])
        if result["verifiedRoots"]:
            verified_count += 1
        verified_fields += result["fieldPaths"]["verified"]
        unverified_fields += result["fieldPaths"]["unverified"]

    missing = missing_required_types(schema)
    # A missing required type is counted as an error so the exit code, the test
    # suite and the printed verdict all agree: coverage that quietly shrank is
    # a failure, not a footnote.
    error_count += len(missing)

    total_fields = verified_fields + unverified_fields
    return {
        "module": str(Path(module_path).relative_to(REPO_ROOT)),
        "schema": str(Path(schema_path).relative_to(REPO_ROOT)),
        "stagedTypes": sorted(schema),
        "missingRequiredTypes": missing,
        "queries": results,
        "totals": {
            "queries": len(queries),
            "queriesWithVerifiedRoot": verified_count,
            "queriesUnverified": len(queries) - verified_count,
            "fieldPaths": total_fields,
            "fieldPathsVerified": verified_fields,
            "fieldPathsUnverified": unverified_fields,
            "fieldCoveragePercent": (
                round(100.0 * verified_fields / total_fields, 1) if total_fields else 0.0
            ),
            "errors": error_count,
        },
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _print_report(report):
    totals = report["totals"]
    print(f"GraphQL schema check — {report['module']}")
    print(f"  staged schema : {report['schema']}  (types: {', '.join(report['stagedTypes'])})")
    print(
        f"  queries       : {totals['queries']} total, "
        f"{totals['queriesWithVerifiedRoot']} verified against staged types, "
        f"{totals['queriesUnverified']} unverified (root type not introspected)"
    )
    print(
        f"  field paths   : {totals['fieldPathsVerified']}/{totals['fieldPaths']} "
        f"checked against a staged type ({totals['fieldCoveragePercent']}%), "
        f"{totals['fieldPathsUnverified']} unchecked"
    )
    print()
    for name, result in report["queries"].items():
        if result["errors"]:
            status = "FAIL"
        elif result["verifiedRoots"]:
            status = "OK"
        else:
            status = "UNVERIFIED"
        counts = result["fieldPaths"]
        print(
            f"  [{status:^10}] {name}  "
            f"({counts['verified']} checked / {counts['unverified']} unchecked)"
        )
        for error in result["errors"]:
            print(f"      {error['kind']} @[{error['path']}]: {error['message']}")
        for item in result["unverified"]:
            print(f"      unverified @[{item['path']}]: {item['reason']}")
    print()
    if report["missingRequiredTypes"]:
        print(
            "REQUIRED STAGING MISSING: "
            + ", ".join(report["missingRequiredTypes"])
            + "\n  A shipped query selects fields on each of these. Without staged "
            "introspection\n  those fields stop being checked while this report keeps "
            "printing a percentage\n  over a shrinking denominator — which is exactly "
            "how the 26.7 reshape shipped."
        )
    if totals["errors"]:
        print(f"FAIL — {totals['errors']} schema error(s).")
    else:
        print("PASS — every query validated against a staged type is schema-clean.")
    print(
        "NOTE: this is a STATIC check against staged introspection. It does not "
        "execute\nanything against a live tenant, and the staged payloads carry field "
        "names only —\nnot type kinds — so a scalar selected as an object (or the "
        "reverse) is NOT caught\nhere. Only a live run settles that."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--module", default=str(REPORTING_MODULE))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    report = check_module(args.module, args.schema)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_report(report)
    return 1 if report["totals"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
