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

Honest coverage
---------------
Only types we have staged introspection for are *checked*. Everything else is
reported as ``UNVERIFIED`` — never silently as passing. ``--json`` emits the
full per-query breakdown so the denominator ("how many of the N queries did we
actually verify") is always visible rather than assumed.

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
DEFAULT_SCHEMA = REPO_ROOT / "tests" / "data" / "ccc-26.7-policymetrics-introspection.json"

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
        """Return the list of top-level selections across every operation.

        Fragment definitions are parsed (so they cannot desync the token
        stream) but not returned: every fragment in this module spreads into a
        type we have no staged introspection for, so validating them is not
        possible and pretending otherwise would be dishonest coverage.
        """
        selections = []
        while self.peek()[0] is not None:
            _, text = self.peek()
            if text == "fragment":
                self.parse_fragment_definition()
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
        return selections

    def parse_fragment_definition(self):
        self.expect("fragment")
        self.next()  # fragment name
        self.expect("on")
        self.next()  # type condition
        self.skip_directives()
        self.parse_selection_set()

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
                    self.next()  # type condition
                    self.skip_directives()
                    self.parse_selection_set()  # unverifiable subtree
                else:
                    self.next()  # fragment spread name
                    self.skip_directives()
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
    """Parse a GraphQL document into its top-level selections."""
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


def validate_selection(field, type_name, schema, path):
    """Validate one field against `type_name`, recursing where we can.

    Returns (errors, unverified). `unverified` records every path we could not
    check so coverage is never overstated.
    """
    errors, unverified = [], []
    type_fields = schema.get(type_name)
    if type_fields is None:
        unverified.append({"path": path, "reason": f"no staged introspection for type {type_name}"})
        return errors, unverified

    if field.name.startswith("__"):
        # `__typename` and friends are meta-fields valid on every object type
        # and are not part of a type's introspected field set.
        return errors, unverified

    definition = type_fields.get(field.name)
    if definition is None:
        errors.append(
            {
                "kind": "FieldUndefined",
                "path": path,
                "message": f"field '{field.name}' does not exist on {type_name}",
            }
        )
        return errors, unverified

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
        child_type = definition["type"]
        if child_type in schema:
            for child in field.selections:
                child_errors, child_unverified = validate_selection(
                    child, child_type, schema, f"{path}/{child.name}"
                )
                errors.extend(child_errors)
                unverified.extend(child_unverified)
        else:
            # One honest entry for the whole subtree rather than one per leaf.
            unverified.append(
                {
                    "path": path,
                    "reason": (
                        f"return type {child_type or '(unnamed)'} not introspected — "
                        f"{len(field.selections)} sub-field(s) unchecked"
                    ),
                }
            )
    return errors, unverified


def validate_document(source, schema):
    """Validate one GraphQL document. Returns a per-document result dict."""
    errors, unverified, verified_paths = [], [], []
    for root in parse_query(source):
        type_name = ROOT_FIELD_TYPES.get(root.name)
        if type_name is None:
            if root.name in KNOWN_UNVERIFIED_ROOTS:
                unverified.append(
                    {"path": root.name, "reason": "root type not introspected"}
                )
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
        for child in root.selections:
            child_errors, child_unverified = validate_selection(
                child, type_name, schema, f"{root.name}/{child.name}"
            )
            errors.extend(child_errors)
            unverified.extend(child_unverified)
    return {"errors": errors, "unverified": unverified, "verifiedRoots": verified_paths}


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


def check_module(module_path=REPORTING_MODULE, schema_path=DEFAULT_SCHEMA):
    """Check every query literal in a command module. Returns a report dict."""
    schema = load_schema(schema_path)
    queries = extract_queries(module_path)

    results, error_count, verified_count = {}, 0, 0
    for name, source in sorted(queries.items()):
        result = validate_document(source, schema)
        results[name] = result
        error_count += len(result["errors"])
        if result["verifiedRoots"]:
            verified_count += 1

    return {
        "module": str(Path(module_path).relative_to(REPO_ROOT)),
        "schema": str(Path(schema_path).relative_to(REPO_ROOT)),
        "stagedTypes": sorted(schema),
        "queries": results,
        "totals": {
            "queries": len(queries),
            "queriesWithVerifiedRoot": verified_count,
            "queriesUnverified": len(queries) - verified_count,
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
    print()
    for name, result in report["queries"].items():
        if result["errors"]:
            status = "FAIL"
        elif result["verifiedRoots"]:
            status = "OK"
        else:
            status = "UNVERIFIED"
        print(f"  [{status:^10}] {name}")
        for error in result["errors"]:
            print(f"      {error['kind']} @[{error['path']}]: {error['message']}")
        for item in result["unverified"]:
            print(f"      unverified @[{item['path']}]: {item['reason']}")
    print()
    if totals["errors"]:
        print(f"FAIL — {totals['errors']} schema error(s).")
    else:
        print("PASS — every query validated against a staged type is schema-clean.")
    print(
        "NOTE: this is a STATIC check against staged introspection. It does not "
        "execute anything against a live tenant."
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
