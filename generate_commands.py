#!/usr/bin/env python3
"""
Auto-generate Click CLI commands from the Elisity CCC OpenAPI spec.
Reads an OpenAPI JSON spec and produces Python modules under
src/elisity_cli/commands/.

Spec resolution (first match wins):
    1. --spec <path>            explicit CLI argument
    2. $ELISITY_API_SPEC        environment variable
    3. DEFAULT_SPEC_PATH        the historical host location

Usage:
    python3 generate_commands.py --spec ./api-docs-26.7.json
    ELISITY_API_SPEC=./api-docs-26.7.json python3 generate_commands.py
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# Historical host path. Kept as the last-resort default so existing host
# workflows (`python3 generate_commands.py` with no arguments) keep working,
# but it is no longer the only way to point the generator at a spec — it does
# not exist inside agent containers or CI.
DEFAULT_SPEC_PATH = os.path.expanduser("~/.claude/skills/elisity-api-expert/api-docs.json")
SPEC_PATH_ENV_VAR = "ELISITY_API_SPEC"

DEFAULT_OUTPUT_DIR = Path(__file__).parent / "src" / "elisity_cli" / "commands"

# Hand-written command groups that are NOT in the OpenAPI spec and therefore
# can never be produced by this generator. They must survive regeneration:
# their modules are never rewritten, and they stay registered in
# commands/__init__.py's COMMAND_GROUPS. Dropping them here would silently
# unregister `elisity reporting` / `elisity glossary` from the CLI.
HANDCODED_GROUPS = ("glossary", "reporting")

# Map OpenAPI tags to CLI command group names
TAG_TO_GROUP = {
    # Topology
    "site-controller": "topology",
    # NOTE: site-label-controller intentionally NOT mapped here.
    # It is mapped to "policy" below (site labels are a policy concept).
    "distribution-zone-controller": "topology",
    "distribution-zone-controller-v-2": "topology",
    "Virtual Edge Group": "topology",
    "Virtual Edge": "topology",
    "virtual-edge-node-controller": "topology",
    "virtual-edge-node-overview-controller": "topology",
    "virtual-edgne-node-topology-controller": "topology",
    "virtual-edges-logging-controller": "topology",
    "Bulk Update": "topology",
    "Bulk Validation": "topology",
    "flow-exporter-controller": "topology",
    "cloud-controller": "topology",
    "dashboard-controller": "topology",
    "global-credentials-controller": "topology",
    "global-interfaces-settings-controller": "topology",
    "targets-controller": "topology",
    "Task Manager": "topology",
    # Policy
    "Policy": "policy",
    "Policy Bulk": "policy",
    "Policy Set": "policy",
    "policy-set-controller": "policy",
    "Policy Group": "policy",
    "Policy Group Bulk": "policy",
    "Policy Group Label": "policy",
    "Policy Group with Device Group Bulk": "policy",
    "Policy View": "policy",
    "Security Profile": "policy",
    "Evaluator": "policy",
    "Device": "policy",
    "Image": "policy",
    "Matched Assets": "policy",
    "State Sync": "policy",
    "Feature Flag": "policy",
    "site-label-controller": "policy",
    # Insights (policy intelligence)
    "Insights": "insights",
    "Dynamic Policy Group Insights": "insights",
    "Network Policy Group Insights": "insights",
    "Suggestion": "insights",
    # Devices / Identity Graph
    "Device - CRUD": "devices",
    "Device - CRUD - v2": "devices",
    "Device - Bulk": "devices",
    "Device - Attach": "devices",
    "Device - Enrich": "devices",
    "Device - recalculate-attributes": "devices",
    "Device Event History": "devices",
    "Data": "devices",
    "Settings": "devices",
    "Suppression List": "devices",
    "Time-Based Configuration": "devices",
    "Feature Flag - Identity Graph": "devices",
    # Connectors
    "Connectors Configurations": "connectors",
    "Custom Connector Devices": "connectors",
    "Custom Connector Inventory - CRUD": "connectors",
    "Connector - connectivity-status": "connectors",
    # AD Connector Service
    "AD Agent": "ad",
    "AD Attributes": "ad",
    "AD Connector": "ad",
    "AD Device": "ad",
    "AD Domain": "ad",
    "AD Group": "ad",
    "AD Member": "ad",
    "AD User": "ad",
    "ADCS Parameters Configuration": "ad",
    "DC Status": "ad",
    "Entra ID": "ad",
    "IP Attach": "ad",
    "Time": "ad",
    # Flows
    "Device State Cache": "flows",
    "Noise Definitions": "flows",
    "Port Information": "flows",
    "Search API": "flows",
    "materialized-view-information-controller": "flows",
    # System / State
    "Spec controller": "system",
    "Task Broker": "system",
}

GROUP_DESCRIPTIONS = {
    "topology": "Manage network topology — sites, zones, VE groups, VEs, VENs, flow exporters",
    "policy": "Manage microsegmentation policies — policy sets, policies, groups, security profiles",
    "insights": "Policy insights and suggestions — dynamic/network group recommendations",
    "devices": "Device identity and enrichment — CRUD, bulk, attach, enrich, events",
    "connectors": "Connector management — custom connectors, configurations, connectivity",
    "ad": "Active Directory / Entra ID integration — connectors, users, groups, agents",
    "flows": "Traffic analytics — device state, flow search, noise definitions",
    "system": "System operations — tasks, specs, state sync",
}


def sanitize_name(name: str) -> str:
    """Convert an operationId or tag to a Python-safe Click command name."""
    # Remove version suffixes like _1, _2
    name = re.sub(r"_(\d+)$", "", name)
    # camelCase to kebab-case
    name = re.sub(r"([a-z])([A-Z])", r"\1-\2", name)
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
    name = name.lower()
    # Clean up
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")
    return name


PYTHON_KEYWORDS = {
    "from", "import", "class", "return", "def", "if", "else", "elif",
    "for", "while", "try", "except", "finally", "with", "as", "pass",
    "break", "continue", "and", "or", "not", "is", "in", "lambda",
    "global", "nonlocal", "yield", "raise", "del", "True", "False", "None",
    "assert", "async", "await", "type",
}


def python_safe(name: str) -> str:
    """Make a name safe for Python identifiers."""
    safe = name.replace("-", "_")
    if safe in PYTHON_KEYWORDS:
        safe = safe + "_param"
    return safe


# Function-argument names the generated command body owns. A spec parameter that
# normalizes onto one of these would emit `def cmd_x(ctx, confirm, ..., confirm)`
# — a SyntaxError, which _register_groups() swallows as a warning, silently
# dropping the ENTIRE group (up to 117 commands) from the CLI. For a DELETE that
# also means losing the --confirm gate. See _unique_name().
RESERVED_DESTS = frozenset({"ctx", "cmd_fmt", "cmd_query", "body_data", "body_file"})
RESERVED_FLAGS = frozenset({"--format", "-f", "--query", "-q", "--body", "--body-file"})
DELETE_GUARD_DEST = "confirm"
DELETE_GUARD_FLAGS = frozenset({"--confirm", "--no-confirm"})


def _unique_name(base: str, used: set, suffix: str = "") -> str:
    """Return `base` if free, else a numbered variant. Records the result.

    Collisions are rare but real: a path param and a query param sharing a name,
    two query params differing only by a character that normalizes away
    (`foo.bar` / `foo-bar`), or a spec param named `confirm` on a DELETE.
    """
    candidate = f"{base}{suffix}" if base in used and suffix else base
    counter = 2
    while candidate in used:
        candidate = f"{base}{suffix}_{counter}" if suffix else f"{base}_{counter}"
        counter += 1
    used.add(candidate)
    return candidate


def resolve_parameter_names(method: str, path_params: list, query_params: list) -> tuple:
    """Assign a collision-free Click flag + Python dest to every parameter.

    The wire name (what goes into the URL path or query string) is never
    changed — only the Python identifier, and the CLI flag if and only if it
    would collide with one the command already owns.

    The request-body flags are reserved unconditionally, not just when the
    operation has a body — a parameter named `body` on a body-less operation is
    harmless to rename and keeps the rule simple.
    """
    used_dests = set(RESERVED_DESTS)
    used_flags = set(RESERVED_FLAGS)
    if method.upper() == "DELETE":
        used_dests.add(DELETE_GUARD_DEST)
        used_flags |= DELETE_GUARD_FLAGS

    resolved_path = []
    for pname, ptype, pdesc in path_params:
        base = python_safe(pname.replace("-", "_")).lower()
        resolved_path.append({
            "spec_name": pname,
            "dest": _unique_name(base, used_dests),
        })

    resolved_query = []
    for pname, ptype, preq, pdesc, pdefault in query_params:
        base = python_safe(pname.replace(".", "_").replace("-", "_"))
        flag = _unique_name(f"--{pname}", used_flags, suffix="-param")
        resolved_query.append({
            "spec_name": pname,
            "dest": _unique_name(base, used_dests),
            "flag": flag,
            "type": ptype,
            "required": preq,
            "desc": pdesc,
            "default": pdefault,
        })

    return resolved_path, resolved_query


def make_command_name(method: str, op_id: str, path: str, tag: str) -> str:
    """Generate a human-friendly command name from operation context.

    Falls back to method + last path segment when there is no operationId, or
    when the operationId sanitizes to nothing (e.g. an id of only punctuation).
    Without that second check the command would be registered under an empty
    name and be impossible to invoke — a silently lost command.
    """
    name = sanitize_name(op_id) if op_id else ""
    if not name:
        name = f"{method.lower()}-{sanitize_name(path.split('/')[-1])}"
    if not name.strip("-"):
        name = f"{method.lower()}-{sanitize_name(path) or 'unnamed'}"
    return name


def extract_params(op: dict) -> tuple:
    """Extract path params, query params from operation."""
    path_params = []
    query_params = []
    for p in op.get("parameters", []):
        param_in = p.get("in", "")
        param_name = p.get("name", "")
        param_type = "str"
        schema = p.get("schema", {})
        if schema.get("type") == "integer":
            param_type = "int"
        elif schema.get("type") == "boolean":
            param_type = "bool"
        required = p.get("required", False)
        desc = p.get("description", "")

        if param_in == "path":
            path_params.append((param_name, param_type, desc))
        elif param_in == "query":
            query_params.append((param_name, param_type, required, desc, schema.get("default")))
    return path_params, query_params


def merge_path_templates(path: str, path_params: list) -> list:
    """Ensure every `{placeholder}` in the path has a corresponding argument.

    OpenAPI requires each path-template expression to be backed by a declared
    path parameter, but the CCC spec does not always comply. Example from the
    26.3 baseline:

        POST /api/identity-graph/v1/custom-connector/{id}/import/{uploadId}/cancel

    declares only `uploadId`. With `{id}` left unsubstituted, the generated
    f-string resolved it against Python's builtin `id`, producing

        /api/identity-graph/v1/custom-connector/<built-in function id>/import/...

    — a nonsense URL sent with exit code 0. Synthesizing the missing argument
    is not inventing an endpoint: the placeholder is literally in the spec's
    path. Parameters are returned in path order so the positional Click
    arguments read left-to-right like the URL.
    """
    declared = {p[0]: p for p in path_params}
    ordered, seen = [], set()

    for name in re.findall(r"\{([^}]*)\}", path):
        if not sanitize_name(name):
            raise ValueError(
                f"path template {{{name}}} in {path} has no usable name — "
                "cannot generate a safe argument for it"
            )
        if name in seen:
            continue
        seen.add(name)
        if name in declared:
            ordered.append(declared[name])
        else:
            ordered.append((name, "str", f"Path parameter (undeclared in spec) — {name}"))

    # Keep any declared path param that the template does not reference, rather
    # than silently dropping it.
    ordered.extend(p for p in path_params if p[0] not in seen)
    return ordered


def has_request_body(op: dict) -> bool:
    return bool(op.get("requestBody"))


def produces_ndjson(op: dict) -> bool:
    """Check if an endpoint produces NDJSON responses."""
    for code, r in op.get("responses", {}).items():
        content = r.get("content", {})
        for ct in content:
            if "ndjson" in ct:
                return True
    return False


def generate_command(method: str, path: str, op: dict, cmd_name: str) -> str:
    """Generate a single Click command function."""
    path_params, query_params = extract_params(op)
    path_params = merge_path_templates(path, path_params)
    has_body = has_request_body(op)
    is_ndjson = produces_ndjson(op)
    raw_summary = op.get("summary", op.get("description", "")) or f"{method.upper()} {path}"
    summary = raw_summary.split("\n")[0].replace('"', '\\"').replace("\\", "\\\\")[:120]
    func_name = python_safe(cmd_name)

    # Collision-free Click flags + Python identifiers. Wire names are unchanged.
    rpath, rquery = resolve_parameter_names(method, path_params, query_params)

    lines = []

    # Build decorator chain
    lines.append(f'@group.command("{cmd_name}")')

    # Path params as Click arguments
    # Click lowercases argument names when passing as kwargs, so we must
    # use lowercase names everywhere to avoid TypeError mismatches.
    for p in rpath:
        lines.append(f'@click.argument("{p["dest"]}")')

    # Query params as Click options
    for q in rquery:
        type_map = {"int": "int", "bool": "bool", "str": "str"}
        click_type = type_map.get(q["type"], "str")
        pdesc, pname = q["desc"], q["spec_name"]
        help_str = pdesc.replace('"', '\\"').replace('\n', ' ').replace('\r', '')[:80] if pdesc else pname
        if q["flag"] != f"--{pname}":
            # Flag renamed to avoid colliding with one the command already owns
            # (e.g. a spec param named `confirm` on a DELETE). The query string
            # still carries the spec name — say so in the help text.
            help_str = f"[sends {pname}] {help_str}"[:80]
        # Enforce required=True when OpenAPI spec says required and no default value
        if q["required"] and q["default"] is None:
            lines.append(f'@click.option("{q["flag"]}", "{q["dest"]}", type={click_type}, required=True, help="{help_str}")')
        else:
            pdefault = q["default"]
            default_str = f'"{pdefault}"' if isinstance(pdefault, str) else str(pdefault) if pdefault is not None else "None"
            lines.append(f'@click.option("{q["flag"]}", "{q["dest"]}", type={click_type}, default={default_str}, help="{help_str}")')

    # Request body as --data JSON option
    if has_body:
        lines.append('@click.option("--body", "body_data", type=str, default=None, help="Request body as JSON string")')
        lines.append('@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None, help="Read request body from JSON file")')

    # Output format/query overrides (allow per-command -f/-q)
    lines.append('@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)')
    lines.append('@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)')

    # Confirm for destructive ops
    if method.upper() in ("DELETE",):
        lines.append('@click.option("--confirm/--no-confirm", default=False, help="Confirm destructive operation")')

    lines.append("@pass_context")

    # Function signature
    sig_parts = ["ctx"]
    sig_parts.extend(p["dest"] for p in rpath)
    sig_parts.extend(q["dest"] for q in rquery)
    if has_body:
        sig_parts.extend(["body_data", "body_file"])
    sig_parts.extend(["cmd_fmt", "cmd_query"])
    if method.upper() == "DELETE":
        sig_parts.append("confirm")

    lines.append(f'def cmd_{func_name}({", ".join(sig_parts)}):')
    lines.append(f'    """{summary}"""')
    lines.append('    if cmd_fmt:')
    lines.append('        ctx.format = cmd_fmt')
    lines.append('    if cmd_query:')
    lines.append('        ctx.query = cmd_query')

    # Delete confirmation
    if method.upper() == "DELETE":
        lines.append('    if not confirm:')
        lines.append('        click.echo("Use --confirm to execute this destructive operation.", err=True)')
        lines.append('        raise SystemExit(1)')

    # Build the endpoint path with substitutions
    endpoint = path
    for p in rpath:
        endpoint = endpoint.replace("{" + p["spec_name"] + "}", f'{{{p["dest"]}}}')
    lines.append(f'    endpoint = f"{endpoint}"')

    # Build query params dict — keyed by the SPEC name, not the Python dest,
    # so a renamed identifier still sends the parameter the API expects.
    if rquery:
        lines.append("    params = {}")
        for q in rquery:
            lines.append(f'    if {q["dest"]} is not None:')
            lines.append(f'        params["{q["spec_name"]}"] = {q["dest"]}')
    else:
        lines.append("    params = None")

    # Handle request body
    if has_body:
        lines.append("    body = None")
        lines.append("    if body_file:")
        lines.append("        import json as _json")
        lines.append("        with open(body_file) as f:")
        lines.append("            body = _json.load(f)")
        lines.append("    elif body_data:")
        lines.append("        import json as _json")
        lines.append("        body = _json.loads(body_data)")

    # Make the API call
    lines.append("    client = ctx.ensure_client()")
    lines.append("    try:")
    method_lower = method.lower()
    if method_lower == "get":
        if is_ndjson:
            lines.append("        result = client.get_ndjson(endpoint, params=params)")
        else:
            lines.append("        result = client.get(endpoint, params=params)")
    elif method_lower == "post":
        if has_body:
            lines.append("        result = client.post(endpoint, data=body, params=params)")
        else:
            lines.append("        result = client.post(endpoint, params=params)")
    elif method_lower == "put":
        if has_body:
            lines.append("        result = client.put(endpoint, data=body, params=params)")
        else:
            lines.append("        result = client.put(endpoint, params=params)")
    elif method_lower == "patch":
        if has_body:
            lines.append("        result = client.patch(endpoint, data=body)")
        else:
            lines.append("        result = client.patch(endpoint)")
    elif method_lower == "delete":
        if has_body:
            lines.append("        result = client.delete(endpoint, params=params, data=body)")
        else:
            lines.append("        result = client.delete(endpoint, params=params)")

    lines.append("    except Exception as e:")
    lines.append('        click.echo(f"Error: {e}", err=True)')
    lines.append("        raise SystemExit(1)")
    lines.append("    render(result, ctx.format, ctx.query)")

    return "\n".join(lines)


def dedupe_command_names(commands: list) -> list:
    """Resolve command-name collisions within a group.

    On the first collision, append `-<method>`; if that also collides (3-way or
    N-way collision), append `-<method>-<n>` with a counter starting at 2. Every
    emitted name is recorded so downstream collisions are also detected.

    Shared with tools/spec_diff.py so the diff reports the command name the
    generator will actually emit, not the pre-dedup candidate.
    """
    seen_names = set()
    deduped = []
    for method, path, op, cmd_name in commands:
        if cmd_name in seen_names:
            candidate = f"{cmd_name}-{method.lower()}"
            counter = 2
            while candidate in seen_names:
                candidate = f"{cmd_name}-{method.lower()}-{counter}"
                counter += 1
            cmd_name = candidate
        seen_names.add(cmd_name)
        deduped.append((method, path, op, cmd_name))
    return deduped


def generate_module(group_name: str, commands: list) -> str:
    """Generate a full Python module for a command group."""
    desc = GROUP_DESCRIPTIONS.get(group_name, f"{group_name} commands")

    header = f'''"""
{desc}

Auto-generated from the Elisity CCC OpenAPI specification.
"""

import click

from elisity_cli.context import CliContext, pass_context
from elisity_cli.output import render


@click.group("{group_name}")
@pass_context
def group(ctx):
    """{desc}"""
    pass

'''

    deduped_commands = dedupe_command_names(commands)

    cmd_blocks = []
    for method, path, op, cmd_name in deduped_commands:
        try:
            block = generate_command(method, path, op, cmd_name)
            cmd_blocks.append(block)
        except Exception as e:
            cmd_blocks.append(f"# SKIPPED: {cmd_name} — {e}")

    return header + "\n\n".join(cmd_blocks) + "\n"


HTTP_METHODS = ("get", "post", "put", "delete", "patch")


def resolve_spec_path(cli_arg: str = None) -> str:
    """Resolve the OpenAPI spec path: --spec > $ELISITY_API_SPEC > default."""
    if cli_arg:
        return cli_arg
    env_value = os.environ.get(SPEC_PATH_ENV_VAR)
    if env_value:
        return env_value
    return DEFAULT_SPEC_PATH


def load_spec(spec_path: str) -> dict:
    """Load an OpenAPI spec, failing with an actionable message."""
    try:
        with open(spec_path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(
            f"ERROR: OpenAPI spec not found at {spec_path}\n"
            f"Pass --spec <path> or set {SPEC_PATH_ENV_VAR}."
        )
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: {spec_path} is not valid JSON — {e}")


def resolve_group(tags: list, path: str) -> tuple:
    """Map an operation to a CLI group.

    Returns (group_name, matched_by) where matched_by is "tag" when a tag hit
    TAG_TO_GROUP and "path-prefix" when the fallback was used. The path-prefix
    fallback means the tag is unmapped and probably needs a human decision —
    spec_diff.py surfaces those separately.
    """
    for tag in tags:
        if tag in TAG_TO_GROUP:
            return TAG_TO_GROUP[tag], "tag"

    # Default assignment by path prefix
    if "/topology/" in path:
        return "topology", "path-prefix"
    if "/policy/" in path:
        return "policy", "path-prefix"
    if "/identity-graph/" in path:
        return "devices", "path-prefix"
    if "/ad-connector-service/" in path:
        return "ad", "path-prefix"
    if "/flows/" in path or "/nflowsearch/" in path:
        return "flows", "path-prefix"
    if "/state-sync/" in path:
        return "system", "path-prefix"
    return "system", "path-prefix"


def iter_operations(spec: dict):
    """Yield (path, method, op, tags, op_id) for every HTTP operation in a spec.

    This is the single source of truth for "what counts as an operation" —
    generate_commands.py and tools/spec_diff.py both use it so their counts
    can never disagree.
    """
    for path, ops in (spec.get("paths") or {}).items():
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method not in HTTP_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            tags = op.get("tags") or ["untagged"]
            op_id = op.get("operationId", "")
            yield path, method, op, tags, op_id


def build_groups(spec: dict) -> tuple:
    """Bucket every spec operation into its CLI group.

    Returns (groups, unmapped) where groups maps group_name ->
    [(method, path, op, cmd_name)] and unmapped lists the (tags, method, path)
    triples that fell through to the path-prefix fallback.
    """
    groups = defaultdict(list)
    unmapped = []

    for path, method, op, tags, op_id in iter_operations(spec):
        group_name, matched_by = resolve_group(tags, path)
        if matched_by == "path-prefix":
            unmapped.append((tags, method, path))
        cmd_name = make_command_name(method, op_id, path, tags[0])
        groups[group_name].append((method, path, op, cmd_name))

    return groups, unmapped


def render_init_module(generated_groups) -> str:
    """Render commands/__init__.py, keeping hand-coded groups registered."""
    all_groups = sorted(set(generated_groups) | set(HANDCODED_GROUPS))
    lines = [
        '"""Command groups.',
        "",
        "Most groups are auto-generated from the CCC OpenAPI spec by",
        "`generate_commands.py`. `reporting` is hand-coded because the CCC reporting",
        "API at /api/reporting/v1/data is GraphQL and isn't in the OpenAPI spec.",
        "`glossary` is hand-coded — it's a CLI-native group (no remote API surface)",
        "that maps Elisity UI terminology to CLI commands.",
        '"""',
        "",
        "COMMAND_GROUPS = [",
    ]
    lines.extend(f'    "{gn}",' for gn in all_groups)
    lines.append("]")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate Click CLI command modules from the CCC OpenAPI spec."
    )
    parser.add_argument(
        "--spec",
        default=None,
        help=f"Path to the OpenAPI JSON spec (default: ${SPEC_PATH_ENV_VAR}, "
             f"then {DEFAULT_SPEC_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Directory to write command modules into (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args(argv)

    spec_path = resolve_spec_path(args.spec)
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    print(f"Spec:   {spec_path}")
    print(f"Output: {output_dir}")

    spec = load_spec(spec_path)
    groups, unmapped = build_groups(spec)

    # A spec tag must never be allowed to overwrite a hand-coded module.
    collisions = sorted(set(groups) & set(HANDCODED_GROUPS))
    if collisions:
        raise SystemExit(
            "ERROR: spec operations were mapped to hand-coded group(s) "
            f"{', '.join(collisions)}. Regenerating would overwrite hand-written "
            "commands. Fix TAG_TO_GROUP (or HANDCODED_GROUPS) before regenerating."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "__init__.py", "w") as f:
        f.write(render_init_module(groups.keys()))

    # Write each group module
    stats = {}
    skipped = []
    for group_name, commands in sorted(groups.items()):
        module_code = generate_module(group_name, commands)
        module_path = output_dir / f"{group_name}.py"
        with open(module_path, "w") as f:
            f.write(module_code)
        stats[group_name] = len(commands)
        module_skips = re.findall(r"^# SKIPPED: (.+)$", module_code, re.MULTILINE)
        skipped.extend(f"{group_name}: {s}" for s in module_skips)
        print(f"  Generated {group_name}.py — {len(commands)} commands")

    print(f"\nTotal: {sum(stats.values())} commands across {len(stats)} groups")
    print(f"Hand-coded groups preserved: {', '.join(sorted(HANDCODED_GROUPS))}")
    if unmapped:
        print(f"Note: {len(unmapped)} endpoints mapped by path prefix (no direct tag match)")

    if skipped:
        # A skipped command is a silently missing command. Never let this pass quietly.
        print(f"\nERROR: {len(skipped)} command(s) failed to generate:", file=sys.stderr)
        for s in skipped:
            print(f"  - {s}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
