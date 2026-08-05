#!/usr/bin/env python3
"""
Authoritative command-count audit for the Elisity CLI.

Walks the source tree, counts what is actually there, and cross-checks every
numeric claim in README.md against it. Exits non-zero on any disagreement, so
documentation drift fails the build instead of accumulating silently.

    python3 tools/audit_counts.py            # human-readable, exit 1 on drift
    python3 tools/audit_counts.py --json     # machine-readable
    python3 tools/audit_counts.py --no-readme-check

The source tree is the source of truth. When this script and README.md
disagree, README.md is the thing that is wrong.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generate_commands import HANDCODED_GROUPS  # noqa: E402

COMMANDS_DIR = REPO_ROOT / "src" / "elisity_cli" / "commands"
MAIN_PY = REPO_ROOT / "src" / "elisity_cli" / "main.py"
README = REPO_ROOT / "README.md"
COMMAND_REFERENCE = REPO_ROOT / "docs" / "command-reference.md"

# The confirmation guard the generator emits for every DELETE operation.
CONFIRM_MARKER = "Use --confirm"
DELETE_MARKER = "client.delete("


def split_command_blocks(source: str, decorator: str = "@group.command(") -> list:
    """Split a module into one text block per command, keyed by command name."""
    blocks = []
    for chunk in source.split(decorator)[1:]:
        name_match = re.match(r'\s*["\']([^"\']+)["\']', chunk)
        blocks.append((name_match.group(1) if name_match else "<unnamed>", chunk))
    return blocks


def audit_group_modules() -> dict:
    """Count commands and delete-gate coverage per command-group module."""
    groups = {}
    for path in sorted(COMMANDS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        source = path.read_text()
        blocks = split_command_blocks(source)
        deletes, gated, ungated = 0, 0, []
        for cmd_name, block in blocks:
            if DELETE_MARKER not in block:
                continue
            deletes += 1
            if CONFIRM_MARKER in block:
                gated += 1
            else:
                ungated.append(f"{path.stem} {cmd_name}")
        groups[path.stem] = {
            "commands": len(blocks),
            "kind": "hand-coded" if path.stem in HANDCODED_GROUPS else "generated",
            "deleteCommands": deletes,
            "gatedDeletes": gated,
            "ungatedDeletes": ungated,
        }
    return groups


def audit_native_groups() -> dict:
    """Count the CLI-native groups defined inline in main.py (auth, config)."""
    source = MAIN_PY.read_text()
    return {
        "auth": len(split_command_blocks(source, "@auth_group.command(")),
        "config": len(split_command_blocks(source, "@config_group.command(")),
    }


def audit_registration(group_modules: dict) -> dict:
    """Confirm every module on disk is registered in COMMAND_GROUPS, and vice versa."""
    init_source = (COMMANDS_DIR / "__init__.py").read_text()
    registered = set(re.findall(r'^\s*"([a-z_]+)",\s*$', init_source, re.MULTILINE))
    on_disk = set(group_modules)
    return {
        "registered": sorted(registered),
        "onDiskNotRegistered": sorted(on_disk - registered),
        "registeredNotOnDisk": sorted(registered - on_disk),
    }


def collect_counts() -> dict:
    group_modules = audit_group_modules()
    native = audit_native_groups()

    generated = sum(g["commands"] for g in group_modules.values() if g["kind"] == "generated")
    handcoded = sum(g["commands"] for g in group_modules.values() if g["kind"] == "hand-coded")
    group_total = generated + handcoded
    native_total = sum(native.values())

    delete_commands = sum(g["deleteCommands"] for g in group_modules.values())
    gated = sum(g["gatedDeletes"] for g in group_modules.values())
    ungated = [name for g in group_modules.values() for name in g["ungatedDeletes"]]

    per_group = {name: g["commands"] for name, g in group_modules.items()}
    per_group.update(native)

    return {
        "perGroup": per_group,
        "groupModules": group_modules,
        "nativeGroups": native,
        "registration": audit_registration(group_modules),
        "totals": {
            "generated": generated,
            "handcodedGroups": handcoded,
            "groupCommands": group_total,
            "cliNativeAuthConfig": native_total,
            "total": group_total + native_total,
            "groupCount": len(per_group),
        },
        "deleteGate": {
            "deleteCommands": delete_commands,
            "gatedDeletes": gated,
            "ungatedDeletes": sorted(ungated),
            "coveragePercent": round(100.0 * gated / delete_commands, 2) if delete_commands else 100.0,
        },
    }


# --------------------------------------------------------------------------
# README cross-check
# --------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Collapse whitespace and markdown blockquote wrapping.

    Lets a single regex match a claim that the source file wraps across lines
    (`> **463 commands** total: 436 auto-generated REST + 20 hand-coded\n> GraphQL`).
    """
    return re.sub(r"\s+", " ", re.sub(r"\n\s*>", " ", text))


def _readme_claims(counts: dict) -> list:
    """(label, regex, expected) for every numeric claim README.md makes.

    Each regex must have exactly one capture group holding the number.
    """
    t = counts["totals"]
    g = counts["perGroup"]
    claims = [
        ("intro: REST endpoints from spec",
         r"all (\d+) REST endpoints from the OpenAPI spec", t["generated"]),
        ("intro: hand-coded GraphQL commands",
         r"(\d+) hand-coded GraphQL commands", g.get("reporting", 0)),
        ("intro: CLI-native glossary group",
         r"a (\d+)-command CLI-native `glossary` group", g.get("glossary", 0)),
        ("features: total commands",
         r"\*\*(\d+) commands\*\* total", t["total"]),
        ("features: auto-generated",
         r"\((\d+) auto-generated from the CCC OpenAPI spec", t["generated"]),
        ("features: hand-coded GraphQL reporting",
         r"\+ (\d+) hand-coded GraphQL reporting commands", g.get("reporting", 0)),
        ("features: CLI-native auth/config",
         r"\+ (\d+) CLI-native auth/config", t["cliNativeAuthConfig"]),
        ("features: CLI-native glossary",
         r"\+ (\d+) CLI-native glossary commands", g.get("glossary", 0)),
        ("docs link: command reference total",
         r"All (\d+) commands with descriptions", t["total"]),
    ]
    for group_name in sorted(g):
        claims.append((
            f"group table: {group_name}",
            rf"\|\s*`{re.escape(group_name)}`\s*\|\s*(\d+)\s*\|",
            g[group_name],
        ))
    return claims


def _command_reference_claims(counts: dict) -> list:
    """Numeric claims made by docs/command-reference.md.

    This file carried the same `reporting` drift the README did, so it is
    checked mechanically too. Its totals deliberately EXCLUDE the CLI-native
    `glossary` group — it documents remote-API commands plus auth/config.
    """
    t = counts["totals"]
    g = counts["perGroup"]
    documented_total = t["generated"] + g.get("reporting", 0) + t["cliNativeAuthConfig"]
    return [
        ("cmd-ref: REST commands listed",
         r"The (\d+) REST commands below", t["generated"]),
        ("cmd-ref: reporting group size",
         r"The `reporting` group \((\d+) commands\)", g.get("reporting", 0)),
        ("cmd-ref: documented total",
         r"\*\*(\d+) commands\*\* total", documented_total),
        ("cmd-ref: auto-generated REST",
         r"(\d+) auto-generated REST", t["generated"]),
        ("cmd-ref: hand-coded GraphQL reporting",
         r"\+ (\d+) hand-coded GraphQL reporting", g.get("reporting", 0)),
        ("cmd-ref: CLI-native auth+config",
         r"\+ (\d+) CLI-native \(auth \+ config\)", t["cliNativeAuthConfig"]),
        ("cmd-ref: excluded glossary commands",
         r"Excludes the (\d+) CLI-native `glossary` commands", g.get("glossary", 0)),
        ("cmd-ref: full command count",
         r"the full (\d+)-command count", t["total"]),
    ]


def check_doc(path: Path, claims: list) -> list:
    """Compare a doc's numeric claims against the source. Returns a result list."""
    label = path.name
    if not path.exists():
        return [{"claim": f"{label}: file present", "status": "MISSING",
                 "expected": None, "found": None,
                 "detail": f"{path} does not exist"}]

    text = _normalize(path.read_text())
    results = []
    for claim, pattern, expected in claims:
        found = re.findall(pattern, text)
        if not found:
            results.append({
                "claim": claim, "status": "MISSING", "expected": expected,
                "found": None,
                "detail": f"no text in {label} matches /{pattern}/",
            })
            continue
        values = sorted({int(v) for v in found})
        if values == [expected]:
            results.append({"claim": claim, "status": "OK", "expected": expected,
                            "found": expected, "detail": ""})
        else:
            results.append({
                "claim": claim, "status": "MISMATCH", "expected": expected,
                "found": values,
                "detail": f"{label} says {values}, source says {expected}",
            })
    return results


def check_docs(counts: dict) -> list:
    """Cross-check every documented count against the source tree."""
    return (
        check_doc(README, _readme_claims(counts))
        + check_doc(COMMAND_REFERENCE, _command_reference_claims(counts))
    )


# --------------------------------------------------------------------------
# Invariants that do not depend on README
# --------------------------------------------------------------------------


def check_invariants(counts: dict) -> list:
    """Structural invariants of the CLI itself."""
    problems = []

    gate = counts["deleteGate"]
    if gate["ungatedDeletes"]:
        problems.append(
            "delete gate: "
            f"{len(gate['ungatedDeletes'])} DELETE command(s) missing --confirm: "
            + ", ".join(gate["ungatedDeletes"])
        )

    reg = counts["registration"]
    if reg["onDiskNotRegistered"]:
        problems.append(
            "registration: module(s) on disk but not in COMMAND_GROUPS: "
            + ", ".join(reg["onDiskNotRegistered"])
        )
    if reg["registeredNotOnDisk"]:
        problems.append(
            "registration: COMMAND_GROUPS names a missing module: "
            + ", ".join(reg["registeredNotOnDisk"])
        )

    for name in HANDCODED_GROUPS:
        if counts["perGroup"].get(name, 0) == 0:
            problems.append(
                f"hand-coded group '{name}' has 0 commands — regeneration "
                "may have overwritten it"
            )

    return problems


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def render(counts: dict, readme_results: list, problems: list) -> str:
    t, gate = counts["totals"], counts["deleteGate"]
    lines = [
        "Elisity CLI — command count audit",
        "=" * 60,
        f"Source of truth: {COMMANDS_DIR.relative_to(REPO_ROOT)} + "
        f"{MAIN_PY.relative_to(REPO_ROOT)}",
        "",
        "Per group:",
    ]
    kinds = {name: g["kind"] for name, g in counts["groupModules"].items()}
    for name in sorted(counts["perGroup"]):
        kind = kinds.get(name, "cli-native")
        lines.append(f"  {name:<12} {counts['perGroup'][name]:>4}  {kind}")

    lines += [
        "",
        "Totals:",
        f"  generated (OpenAPI)      {t['generated']:>4}",
        f"  hand-coded groups        {t['handcodedGroups']:>4}",
        f"  CLI-native auth/config   {t['cliNativeAuthConfig']:>4}",
        f"  TOTAL                    {t['total']:>4}  across {t['groupCount']} groups",
        "",
        "Delete gate:",
        f"  delete commands          {gate['deleteCommands']:>4}",
        f"  gated with --confirm     {gate['gatedDeletes']:>4}",
        f"  coverage                 {gate['coveragePercent']:>6}%",
    ]
    if gate["ungatedDeletes"]:
        lines.append("  UNGATED: " + ", ".join(gate["ungatedDeletes"]))

    if readme_results is not None:
        lines += ["", "Documentation cross-check:"]
        for r in readme_results:
            mark = "OK  " if r["status"] == "OK" else "FAIL"
            detail = f"  <- {r['detail']}" if r["detail"] else ""
            lines.append(f"  [{mark}] {r['claim']:<40} {r['expected']}{detail}")

    lines.append("")
    if problems:
        lines.append("INVARIANT FAILURES:")
        lines.extend(f"  - {p}" for p in problems)
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit Elisity CLI command counts.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--no-readme-check", action="store_true",
                        help="Report counts without cross-checking the docs")
    args = parser.parse_args(argv)

    counts = collect_counts()
    problems = check_invariants(counts)
    readme_results = None if args.no_readme_check else check_docs(counts)
    readme_failures = [r for r in (readme_results or []) if r["status"] != "OK"]

    if args.json:
        print(json.dumps(
            {"counts": counts, "readme": readme_results, "invariantFailures": problems},
            indent=2, sort_keys=True,
        ))
    else:
        print(render(counts, readme_results, problems))

    if problems:
        print(f"FAIL: {len(problems)} invariant failure(s).", file=sys.stderr)
    if readme_failures:
        print(
            f"FAIL: {len(readme_failures)} README.md claim(s) disagree with the "
            "source tree. Update README.md to match the source.",
            file=sys.stderr,
        )
    if problems or readme_failures:
        return 1

    if not args.json:
        # Keep --json output pure JSON on stdout so it can be piped.
        print("PASS: source counts and documentation agree; delete gate at 100%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
