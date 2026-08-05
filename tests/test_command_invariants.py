"""
Mechanical invariants of the generated command surface.

These are the properties that must survive every regeneration from a new CCC
OpenAPI spec. They are enforced here rather than by review because a spec bump
adds commands in bulk and a reviewer scanning a 400-command diff will not
reliably notice a single DELETE that lost its --confirm guard.

Covered:
  1. Delete gate  — 100% of commands issuing client.delete() require --confirm,
                    both in the committed tree and in freshly generated code.
  2. Hand-coded   — the `reporting` (GraphQL) and `glossary` (CLI-native) groups
     survival       are never overwritten or unregistered by regeneration.
  3. Doc counts   — tools/audit_counts.py agrees with the source tree.
  4. Loadability  — every registered group imports and exposes its commands.
"""

import re
import subprocess
import sys
import warnings
from pathlib import Path

import pytest
from click.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generate_commands import (  # noqa: E402
    HANDCODED_GROUPS,
    build_groups,
    generate_module,
    render_init_module,
)
from tools.audit_counts import (  # noqa: E402
    audit_group_modules,
    check_docs,
    check_invariants,
    collect_counts,
)

from elisity_cli.commands import COMMAND_GROUPS  # noqa: E402
from elisity_cli.main import cli  # noqa: E402

COMMANDS_DIR = REPO_ROOT / "src" / "elisity_cli" / "commands"


@pytest.fixture(scope="module")
def counts():
    return collect_counts()


# --------------------------------------------------------------------------
# 1. Delete gate — the security invariant
# --------------------------------------------------------------------------


class TestDeleteGate:
    def test_every_delete_command_requires_confirm(self, counts):
        """100% --confirm coverage. Names the offenders when it slips."""
        gate = counts["deleteGate"]
        assert gate["ungatedDeletes"] == [], (
            f"{len(gate['ungatedDeletes'])} DELETE command(s) can run without "
            f"--confirm: {', '.join(gate['ungatedDeletes'])}. "
            "Every command issuing client.delete() must be gated — fix "
            "generate_commands.py, not the generated module."
        )
        assert gate["coveragePercent"] == 100.0

    def test_delete_commands_actually_exist(self, counts):
        """Guards against the audit trivially passing on an empty set."""
        assert counts["deleteGate"]["deleteCommands"] > 0

    def test_generated_delete_command_is_gated(self):
        """Regeneration itself must emit the guard, not just today's tree."""
        spec = {
            "paths": {
                "/api/topology/v2/sites/{id}": {
                    "delete": {
                        "tags": ["site-controller"],
                        "operationId": "deleteSiteV2",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True,
                             "schema": {"type": "string"}}
                        ],
                        "responses": {"204": {}},
                    }
                }
            }
        }
        groups, _ = build_groups(spec)
        module = generate_module("topology", groups["topology"])

        assert "--confirm/--no-confirm" in module
        assert "Use --confirm to execute this destructive operation." in module
        assert "client.delete(" in module

    def test_freshly_generated_module_passes_the_gate_scan(self, tmp_path):
        """The audit's own scan must find zero ungated deletes in new output."""
        spec = {
            "paths": {
                f"/api/topology/v2/thing{i}/{{id}}": {
                    "delete": {
                        "tags": ["site-controller"],
                        "operationId": f"deleteThing{i}",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True,
                             "schema": {"type": "string"}}
                        ],
                        "responses": {"204": {}},
                    }
                }
                for i in range(5)
            }
        }
        groups, _ = build_groups(spec)
        module_text = generate_module("topology", groups["topology"])

        ungated = [
            block.split('"')[1]
            for block in module_text.split("@group.command(")[1:]
            if "client.delete(" in block and "Use --confirm" not in block
        ]
        assert ungated == []

    def test_delete_command_refuses_without_confirm(self):
        """Behavioural check — the guard actually blocks, it isn't just text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["topology", "delete-site-v2", "some-id"])

        assert result.exit_code == 1
        assert "Use --confirm" in result.output

    def test_delete_help_advertises_confirm(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["topology", "delete-site-v2", "--help"])

        assert result.exit_code == 0
        assert "--confirm" in result.output


# --------------------------------------------------------------------------
# 1b. Parameter-name collisions
# --------------------------------------------------------------------------


def _generate_one(method: str, path: str, params: list, tag: str = "site-controller"):
    """Generate a single-command module for a synthetic operation."""
    spec = {"paths": {path: {method: {
        "tags": [tag], "operationId": "doThing",
        "parameters": params, "responses": {"200": {}},
    }}}}
    groups, _ = build_groups(spec)
    group_name = next(iter(groups))
    return generate_module(group_name, groups[group_name])


class TestParameterCollisions:
    """A spec parameter must never collide with an identifier the command owns.

    Every case below produced `def cmd_x(ctx, foo, ..., foo)` — a SyntaxError.
    _register_groups() catches import errors and only prints a warning, so the
    whole group (up to 117 commands) would vanish from the CLI silently. On a
    DELETE that also means losing the --confirm gate.
    """

    def test_delete_with_a_confirm_query_param_still_compiles_and_stays_gated(self):
        module = _generate_one("delete", "/api/topology/v2/sites/{id}", [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
            {"name": "confirm", "in": "query", "schema": {"type": "boolean"}},
        ])
        compile(module, "topology.py", "exec")

        assert "Use --confirm to execute this destructive operation." in module
        assert '@click.option("--confirm/--no-confirm"' in module
        # The spec parameter is renamed, but still sent under its wire name.
        assert 'params["confirm"]' in module

    def test_path_and_query_param_sharing_a_name_compiles(self):
        module = _generate_one("get", "/api/topology/v2/x/{id}", [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
            {"name": "id", "in": "query", "schema": {"type": "string"}},
        ])
        compile(module, "topology.py", "exec")
        assert 'params["id"]' in module

    def test_params_normalizing_to_the_same_identifier_compile(self):
        """`foo.bar` and `foo-bar` both sanitize to `foo_bar`."""
        module = _generate_one("get", "/api/topology/v2/y", [
            {"name": "foo.bar", "in": "query", "schema": {"type": "string"}},
            {"name": "foo-bar", "in": "query", "schema": {"type": "string"}},
        ])
        compile(module, "topology.py", "exec")
        assert 'params["foo.bar"]' in module
        assert 'params["foo-bar"]' in module

    def test_format_and_query_params_are_renamed_but_sent_verbatim(self):
        """`format`/`query` collide with the CLI's own output overrides."""
        module = _generate_one("get", "/api/topology/v2/z", [
            {"name": "format", "in": "query", "schema": {"type": "string"}},
            {"name": "query", "in": "query", "schema": {"type": "string"}},
        ])
        compile(module, "topology.py", "exec")

        assert '"--format-param"' in module
        assert '"--query-param"' in module
        assert 'params["format"]' in module
        assert 'params["query"]' in module

    @pytest.mark.parametrize("label,names", [
        ("context arg", ["ctx"]),
        ("body args", ["body", "body_file"]),
        ("output override dests", ["cmd_fmt", "cmd_query"]),
        ("python keywords", ["from", "class", "type"]),
        ("all at once", ["ctx", "confirm", "format", "query", "cmd_fmt", "body_file"]),
    ])
    def test_reserved_identifier_names_do_not_break_generation(self, label, names):
        """Any spec param name must be absorbable, not just the ones seen so far."""
        module = _generate_one("get", "/api/topology/v2/w", [
            {"name": n, "in": "query", "schema": {"type": "string"}} for n in names
        ])
        compile(module, "topology.py", "exec")
        for n in names:
            assert f'params["{n}"]' in module, f"{n} is no longer sent on the wire"

    def test_worst_case_delete_keeps_its_gate(self):
        """Path param, query param and the guard all named `confirm`."""
        module = _generate_one("delete", "/api/topology/v2/v/{confirm}", [
            {"name": "confirm", "in": "path", "required": True, "schema": {"type": "string"}},
            {"name": "confirm", "in": "query", "schema": {"type": "string"}},
            {"name": "format", "in": "query", "schema": {"type": "string"}},
        ])
        compile(module, "topology.py", "exec")

        assert "Use --confirm to execute this destructive operation." in module
        assert '@click.option("--confirm/--no-confirm"' in module
        assert 'params["confirm"]' in module

    def test_every_committed_module_compiles(self):
        """Net that catches any collision class not enumerated above."""
        for path in sorted(COMMANDS_DIR.glob("*.py")):
            compile(path.read_text(), str(path), "exec")

    def test_no_command_declares_a_duplicate_flag(self):
        """The live regression this caught: `flows get-pg-data` declared
        --format twice, so the required spec param could never be satisfied and
        the command was impossible to invoke (exit 2, 'Missing option')."""
        offenders = []
        for group_name in COMMAND_GROUPS:
            mod = __import__(f"elisity_cli.commands.{group_name}", fromlist=["group"])
            for cmd_name, cmd in mod.group.commands.items():
                seen = set()
                for param in cmd.params:
                    for opt in param.opts + param.secondary_opts:
                        if opt in seen:
                            offenders.append(f"{group_name} {cmd_name}: {opt}")
                        seen.add(opt)
        assert offenders == [], "duplicate option flags: " + ", ".join(offenders)

    def test_loading_every_group_emits_no_click_warnings(self):
        """Click warns 'parameter used more than once' on a duplicate flag."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            runner = CliRunner()
            for group_name in COMMAND_GROUPS:
                runner.invoke(cli, [group_name, "--help"])
        duplicates = [str(w.message) for w in caught if "more than once" in str(w.message)]
        assert duplicates == [], f"Click duplicate-parameter warnings: {duplicates}"

    def test_renamed_flag_still_sends_the_spec_parameter_name(self):
        """End-to-end through Click: --format-param must put `format` on the wire."""
        captured = {}

        class FakeClient:
            def post(self, endpoint, data=None, params=None):
                captured["params"] = params
                return [{"ok": True}]

        import elisity_cli.context as ctxmod
        original = ctxmod.CliContext.ensure_client
        ctxmod.CliContext.ensure_client = lambda self: FakeClient()
        try:
            result = CliRunner().invoke(
                cli, ["flows", "get-pg-data", "--format-param", "csv", "--size", "10"]
            )
        finally:
            ctxmod.CliContext.ensure_client = original

        assert result.exit_code == 0, result.output
        assert captured["params"] == {"format": "csv", "size": "10"}


# --------------------------------------------------------------------------
# 2. Hand-coded surface survival
# --------------------------------------------------------------------------


class TestHandCodedGroupsSurvive:
    def test_handcoded_groups_are_registered(self):
        for name in HANDCODED_GROUPS:
            assert name in COMMAND_GROUPS, (
                f"hand-coded group '{name}' is missing from COMMAND_GROUPS — "
                "regeneration unregistered it"
            )

    def test_handcoded_modules_exist_and_have_commands(self, counts):
        for name in HANDCODED_GROUPS:
            assert (COMMANDS_DIR / f"{name}.py").exists()
            assert counts["perGroup"].get(name, 0) > 0

    def test_handcoded_modules_are_not_marked_auto_generated(self):
        """A hand-coded module carrying the generator header means it was clobbered."""
        for name in HANDCODED_GROUPS:
            source = (COMMANDS_DIR / f"{name}.py").read_text()
            assert "Auto-generated from the Elisity CCC OpenAPI specification" not in source

    def test_render_init_keeps_handcoded_groups_when_spec_yields_none(self):
        """The regression this guards: __init__.py was rebuilt from generated
        groups only, silently dropping `reporting` and `glossary`."""
        rendered = render_init_module(["topology", "policy"])

        for name in HANDCODED_GROUPS:
            assert f'"{name}",' in rendered

    def test_render_init_is_deterministic_and_sorted(self):
        rendered = render_init_module(["topology", "ad", "policy"])
        names = re.findall(r'^\s*"([a-z_]+)",$', rendered, re.MULTILINE)

        assert names == sorted(names)
        assert rendered == render_init_module(["policy", "ad", "topology"])

    def test_generator_refuses_to_overwrite_a_handcoded_group(self, tmp_path):
        """If a future spec tag ever maps onto `reporting`/`glossary`, the
        generator must abort rather than overwrite hand-written commands."""
        import generate_commands

        spec_file = tmp_path / "spec.json"
        spec_file.write_text('{"paths": {"/api/reporting/v1/data": {"get": '
                             '{"tags": ["Bogus Reporting"], "operationId": "x", '
                             '"responses": {}}}}}')

        original = dict(generate_commands.TAG_TO_GROUP)
        generate_commands.TAG_TO_GROUP["Bogus Reporting"] = "reporting"
        try:
            with pytest.raises(SystemExit) as exc:
                generate_commands.main([
                    "--spec", str(spec_file), "--output-dir", str(tmp_path / "out"),
                ])
            assert "hand-coded" in str(exc.value)
            assert not (tmp_path / "out" / "reporting.py").exists()
        finally:
            generate_commands.TAG_TO_GROUP.clear()
            generate_commands.TAG_TO_GROUP.update(original)


# --------------------------------------------------------------------------
# 3. Documentation counts
# --------------------------------------------------------------------------


class TestDocumentedCounts:
    def test_docs_agree_with_source(self, counts):
        """README.md / command-reference.md numbers match a fresh source audit."""
        failures = [r for r in check_docs(counts) if r["status"] != "OK"]
        detail = "\n".join(f"  {r['claim']}: {r['detail']}" for r in failures)
        assert not failures, (
            f"{len(failures)} documented count(s) disagree with the source "
            f"tree:\n{detail}\n"
            "Run `python3 tools/audit_counts.py` and update the docs."
        )

    def test_structural_invariants_hold(self, counts):
        assert check_invariants(counts) == []

    def test_audit_script_exits_zero(self):
        """The script is wired into CI — it must be runnable standalone."""
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "audit_counts.py")],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_audit_script_json_mode_is_parseable(self):
        import json

        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "audit_counts.py"), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        payload = json.loads(proc.stdout)

        assert payload["counts"]["totals"]["total"] > 0
        assert payload["invariantFailures"] == []

    def test_audit_detects_injected_doc_drift(self, tmp_path, monkeypatch):
        """Negative test: the audit must FAIL on a wrong number, or it is
        worthless as a guard."""
        import tools.audit_counts as ac

        original = ac.README.read_text()
        fake = tmp_path / "README.md"
        fake.write_text(original.replace("**466 commands** total",
                                         "**999 commands** total"))
        monkeypatch.setattr(ac, "README", fake)

        failures = [r for r in ac.check_docs(collect_counts()) if r["status"] != "OK"]
        assert any("total commands" in r["claim"] for r in failures)


# --------------------------------------------------------------------------
# 4. Loadability
# --------------------------------------------------------------------------


class TestGroupsLoad:
    def test_every_registered_group_imports(self):
        for name in COMMAND_GROUPS:
            mod = __import__(f"elisity_cli.commands.{name}", fromlist=["group"])
            assert hasattr(mod, "group"), f"{name} module exposes no `group`"

    def test_root_help_lists_every_registered_group(self):
        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        for name in COMMAND_GROUPS:
            assert name in result.output, f"group '{name}' missing from root --help"

    def test_no_group_fails_to_load(self):
        """_register_groups swallows import errors with a warning — catch that."""
        result = CliRunner().invoke(cli, ["--help"])

        assert "Failed to load" not in result.output

    def test_every_module_on_disk_is_registered(self, counts):
        assert counts["registration"]["onDiskNotRegistered"] == []
        assert counts["registration"]["registeredNotOnDisk"] == []

    def test_group_command_counts_match_click_registry(self, counts):
        """Source-scan counts must equal what Click actually registered."""
        modules = audit_group_modules()
        for name, info in modules.items():
            mod = __import__(f"elisity_cli.commands.{name}", fromlist=["group"])
            assert len(mod.group.commands) == info["commands"], (
                f"{name}: source scan found {info['commands']} commands but "
                f"Click registered {len(mod.group.commands)}"
            )
