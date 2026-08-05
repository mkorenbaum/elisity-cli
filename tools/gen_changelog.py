#!/usr/bin/env python3
"""Render a command-level changelog from a spec_diff.py --json report.

Mike's requirement for the 26.7 bump was that the README say *what commands
were added or changed*, not just carry refreshed totals. A hand-maintained list
of 192 additions drifts the moment anyone regenerates, so this renders it from
the diff instead: `spec_diff.py --json` is the input, markdown is the output,
and the next CCC bump is the same one command.

    python3 tools/spec_diff.py old.json new.json --json > diff.json
    python3 tools/gen_changelog.py --diff diff.json --version 26.7 \
        --source insights-demo.idp01.elisity.io > changelog.md

Changes are split by whether they can break a caller, which is the distinction
a reader actually needs:

* **Signature** changes alter the command's flags — a script can stop working.
* **Request body** changes alter the JSON passed to `--body`/`--body-file`.
  The generator emits the body as one opaque JSON option rather than per-field
  flags, so these never change the command's signature, but they do change what
  a caller must send.
* **Response-only** changes cannot break an invocation at all, so they are
  counted rather than enumerated.
"""

import argparse
import collections
import json
import sys


def _load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _describe(op: dict) -> str:
    """One-line description of an operation, sourced only from the spec.

    Falls back to `METHOD /path` when the spec carries no summary — inventing a
    description would put words in the API's mouth.
    """
    summary = (op.get("summary") or "").strip()
    if summary:
        # Keep it to one line; some CCC summaries embed newlines.
        return " ".join(summary.split())
    return f"`{op['method']} {op['path']}`"


def _classify_change(entry: dict) -> str:
    """Bucket a changed operation: signature | body | response-only."""
    changes = entry.get("changes", {})
    if "parameters" in changes or "command" in changes or "group" in changes:
        return "signature"
    if "requestBody" in changes:
        return "body"
    return "response-only"


def _signature_detail(entry: dict) -> str:
    """Human phrasing of what changed about a command's signature."""
    changes = entry.get("changes", {})
    bits = []

    renamed = changes.get("command")
    if renamed:
        bits.append(f"renamed from `{renamed['from']}`")

    moved = changes.get("group")
    if moved:
        bits.append(f"moved from `{moved['from']}` to `{moved['to']}`")

    params = changes.get("parameters") or {}
    for p in params.get("added", []):
        req = "required" if p.get("required") else "optional"
        bits.append(f"new {req} `--{p['name']}` ({_type_label(p.get('type'))})")
    for p in params.get("removed", []):
        bits.append(f"dropped `--{p['name']}`")
    for p in params.get("changed", []):
        # spec_diff emits {"parameter": "query:size", "from": {...}, "to": {...}}
        old, new = p.get("from") or {}, p.get("to") or {}
        name = new.get("name") or old.get("name") or p.get("parameter", "?")
        if old.get("type") != new.get("type"):
            bits.append(
                f"`--{name}` {_type_label(old.get('type'))} -> "
                f"{_type_label(new.get('type'))}"
            )
        if old.get("required") != new.get("required"):
            became = "required" if new.get("required") else "optional"
            bits.append(f"`--{name}` became {became}")

    return "; ".join(bits) or "parameters changed"


def _type_label(t) -> str:
    """Render a spec_diff parameter type for humans.

    spec_diff reports `unknown` when the parameter's schema carries no `type`
    key at all. That is not a mystery type — the generator can only treat it as
    a string — so say so, because "unknown -> integer" reads like a tooling gap
    when it is really the spec gaining a type it was always missing.
    """
    if t in (None, "", "unknown"):
        return "untyped (sent as string)"
    return str(t)


def render(diff: dict, version: str, source: str, baseline: str) -> str:
    summary = diff.get("summary", {})
    added = diff.get("added", [])
    removed = diff.get("removed", [])
    changed = diff.get("changed", [])

    out = []
    w = out.append

    w(f"## What changed in CCC {version}")
    w("")
    w(
        f"The command set is generated from the CCC {version} OpenAPI spec, pulled from "
        f"`{source}`. The previous set came from the {baseline} spec."
    )
    w("")
    w(
        f"| | {baseline} | {version} |\n"
        f"|---|---:|---:|\n"
        f"| Spec paths | {summary.get('oldPathCount', '?')} | {summary.get('newPathCount', '?')} |\n"
        f"| Spec operations | {summary.get('oldOperationCount', '?')} | {summary.get('newOperationCount', '?')} |"
    )
    w("")
    w(
        f"**{len(added)} commands added, {len(removed)} removed, "
        f"{len(changed)} operations changed.**"
    )
    w("")

    # ---- Removed: breaking, so it leads. -------------------------------
    w("### Removed commands (breaking)")
    w("")
    if not removed:
        w("None.")
    else:
        w(
            f"These {len(removed)} commands are gone because the operation was removed "
            "from the CCC spec. Any script invoking one will now fail with "
            "`No such command`."
        )
        w("")
        by_tag = collections.defaultdict(list)
        for op in removed:
            by_tag[(op.get("tags") or ["untagged"])[0]].append(op)
        for tag in sorted(by_tag):
            ops = sorted(by_tag[tag], key=lambda o: o["command"])
            w(f"**{tag}** ({len(ops)})")
            w("")
            for op in ops:
                w(f"- `elisity {op['group']} {op['command']}` — {_describe(op)}")
            w("")
    w("")

    # ---- Renames / signature changes: also breaking. --------------------
    sig = [c for c in changed if _classify_change(c) == "signature"]
    body = [c for c in changed if _classify_change(c) == "body"]
    resp = [c for c in changed if _classify_change(c) == "response-only"]

    w("### Changed command signatures")
    w("")
    if not sig:
        w("None.")
    else:
        w(
            f"{len(sig)} commands changed shape — a renamed command or a changed flag "
            "can break an existing script."
        )
        w("")
        by_group = collections.defaultdict(list)
        for c in sig:
            by_group[c["group"]].append(c)
        for group in sorted(by_group):
            w(f"**`{group}`**")
            w("")
            for c in sorted(by_group[group], key=lambda x: x["command"]):
                w(f"- `elisity {group} {c['command']}` — {_signature_detail(c)}")
            w("")
    w("")

    w("### Changed request bodies")
    w("")
    if not body:
        w("None.")
    else:
        w(
            f"{len(body)} commands take a different request body. The command's flags are "
            "unchanged — the body is passed as opaque JSON via `--body` / `--body-file` — "
            "but the JSON you send must match the new schema."
        )
        w("")
        by_group = collections.defaultdict(list)
        for c in body:
            by_group[c["group"]].append(c)
        for group in sorted(by_group):
            cmds = ", ".join(f"`{c['command']}`" for c in sorted(by_group[group], key=lambda x: x["command"]))
            w(f"- **`{group}`** — {cmds}")
        w("")
    w("")

    if resp:
        w(
            f"A further {len(resp)} operations changed only in their response schema or "
            "status codes. Invocation is unaffected, so they are not listed."
        )
        w("")

    # ---- Added. ---------------------------------------------------------
    w("### Added commands")
    w("")
    if not added:
        w("None.")
    else:
        w(f"{len(added)} new commands, grouped by CLI group.")
        w("")
        by_group = collections.defaultdict(list)
        for op in added:
            by_group[op["group"]].append(op)
        for group in sorted(by_group):
            ops = sorted(by_group[group], key=lambda o: o["command"])
            w(f"#### `{group}` (+{len(ops)})")
            w("")
            for op in ops:
                w(f"- `{op['command']}` — {_describe(op)}")
            w("")

    return "\n".join(out).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--diff", required=True, help="spec_diff.py --json output")
    ap.add_argument("--version", required=True, help="New CCC version, e.g. 26.7")
    ap.add_argument("--source", required=True, help="Tenant the spec was pulled from")
    ap.add_argument("--baseline", default="previous", help="Previous CCC version label")
    args = ap.parse_args(argv)

    sys.stdout.write(render(_load(args.diff), args.version, args.source, args.baseline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
