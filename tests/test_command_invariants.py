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

import json
import os
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
    assert_every_tag_mapped,
    is_destructive_operation,
    resolve_group,
    resolve_parameter_names,
    unmapped_tags,
    generate_module,
    merge_path_templates,
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

# The OpenAPI specs are not committed (1-2 MB each, and the repo generates FROM
# them rather than shipping them). Where a checkout has them staged, a few tests
# assert against the real thing; where it does not, they skip and the synthetic
# equivalents still run. $ELISITY_API_SPEC is the same variable the generator
# reads.
SPEC_267 = Path(
    os.environ.get("ELISITY_API_SPEC", REPO_ROOT.parent / "input" / "api-docs-26.7.json")
)
SPEC_263 = REPO_ROOT.parent / "input" / "api-docs-baseline-26.3.json"


@pytest.fixture(scope="module")
def counts():
    return collect_counts()


# --------------------------------------------------------------------------
# 1. Confirm gate — the security invariant
# --------------------------------------------------------------------------


class TestConfirmGate:
    """The gate keys on DESTRUCTIVENESS, not on the DELETE verb.

    It used to key on the verb, and the audit measured its coverage with the
    same verb-shaped denominator — so `tools/audit_counts.py` certified
    "coverage 100.0%" while ten destructive POST/PUT commands ran ungated, four
    of them added by the 26.7 bump. `topology bulk-force-delete-ve-ns` (POST,
    many VENs) was ungated while `topology force-delete-ven` (DELETE, one VEN)
    was gated, and both docs told agents every delete required --confirm.

    Widening the gate without widening the denominator would have reproduced
    exactly that bug one layer out, so these tests pin BOTH: the gate covers
    every destructive command, and the denominator is derived from the same
    single predicate the generator emits from.
    """

    def test_every_destructive_command_requires_confirm(self, counts):
        gate = counts["confirmGate"]
        assert gate["ungatedDestructive"] == [], (
            f"{len(gate['ungatedDestructive'])} destructive command(s) can run "
            f"without --confirm: {', '.join(gate['ungatedDestructive'])}. "
            "Fix generate_commands.py, not the generated module."
        )
        assert gate["coveragePercent"] == 100.0

    def test_denominator_is_wider_than_the_delete_verb(self, counts):
        """The number that matters: destructive commands, not DELETEs.

        52 DELETEs was the old denominator. If this ever equals the DELETE count
        again, the gate has silently narrowed back to the verb.
        """
        gate = counts["confirmGate"]
        deletes = sum(
            1
            for module in COMMANDS_DIR.glob("*.py")
            if module.name != "__init__.py"
            for block in module.read_text().split("@group.command(")[1:]
            if "client.delete(" in block
        )
        assert deletes == 52, deletes
        assert gate["destructiveCommands"] == 67, gate["destructiveCommands"]
        assert gate["destructiveCommands"] > deletes

    def test_the_non_delete_destructive_commands_are_named(self, counts):
        """Pin the 15 the verb-shaped gate missed, so a silent loss fails here."""
        gated_non_delete = set()
        for module in sorted(COMMANDS_DIR.glob("*.py")):
            if module.name == "__init__.py":
                continue
            for block in module.read_text().split("@group.command(")[1:]:
                name = block.split('"')[1]
                if "Use --confirm" in block and "client.delete(" not in block:
                    gated_non_delete.add(f"{module.stem} {name}")
        assert gated_non_delete == {
            "devices detach",
            "devices detach-by-mac",
            "insights recreate-policy-suggestions",
            "insights recreate-suggestions",
            "insights reset-policy-suggestions-to-default",
            "insights reset-suggestions-to-default",
            "insights reset-suggestions-to-default-post",
            "policy bulk-delete",
            "topology bulk-delete-distribution-zone",
            "topology bulk-delete-site",
            "topology bulk-delete-site-v2",
            "topology bulk-delete-ve-ns",
            "topology bulk-delete-virtual-edges",
            "topology bulk-force-delete-ve-ns",
            "topology decommission-virtual-edge-node",
        }

    def test_destructive_commands_actually_exist(self, counts):
        """Guards against the audit trivially passing on an empty set."""
        assert counts["confirmGate"]["destructiveCommands"] > 0

    def test_dry_run_siblings_are_not_gated(self, counts):
        """`.../bulk/delete/validate` reports what a delete would do.

        Gating it would be friction with no safety value, and would teach users
        that --confirm on these paths means nothing.
        """
        assert not is_destructive_operation(
            "POST", "/api/topology/v1/virtual-edges/bulk/delete/validate"
        )
        assert is_destructive_operation(
            "POST", "/api/topology/v1/virtual-edges/bulk/delete"
        )
        assert counts["confirmGate"]["gatedButNotClassifiedDestructive"] == []

    def test_whole_segment_matching_not_substring(self):
        """`/devices/purge-settings` configures the purge policy; it purges nothing."""
        assert not is_destructive_operation(
            "PUT", "/api/identity-graph/v2/devices/purge-settings"
        )
        assert is_destructive_operation(
            "DELETE", "/api/identity-graph/v1/devices/bulk/purge"
        )

    def test_every_destructive_sounding_name_has_been_ruled_on(self, counts):
        """The denominator's own watchdog.

        A command whose NAME reads destructive while its PATH does not classify
        is the gap the path matcher cannot see by itself. Each one must be an
        explicit human ruling, not an emergent property — so an unruled
        `bulk-nuke-sites` on an unrecognised path fails the build.
        """
        assert counts["confirmGate"]["nameDestructivePathNot"] == []
        assert set(counts["confirmGate"]["ruledNonDestructiveDespiteName"]) == {
            "policy force-sync",
            "topology validate-virtual-edge-bulk-delete",
            "topology validate-virtual-edge-node-bulk-delete",
        }

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

    @pytest.mark.parametrize("path", [
        "/api/topology/v1/virtual-edge-nodes/bulk/force-delete",
        "/api/topology/v1/sites/bulk/delete",
        "/api/identity-graph/v1/labels/bulk-delete",
        "/api/identity-graph/v1/devices/{id}/detach",
        "/api/policy/v1/insights/policy-groups/reset-to-default",
        "/api/policy/v1/insights/policy-groups/recreate",
    ])
    def test_generated_destructive_post_is_gated(self, path):
        """A POST that destroys must be gated exactly like the DELETE would be."""
        spec = {"paths": {path: {"post": {
            "tags": ["site-controller"], "operationId": "doTheThing",
            "parameters": [
                {"name": p.strip("{}"), "in": "path", "required": True,
                 "schema": {"type": "string"}}
                for p in path.split("/") if p.startswith("{")
            ],
            "responses": {"200": {}},
        }}}}
        groups, _ = build_groups(spec)
        module = generate_module("topology", groups["topology"])

        assert '@click.option("--confirm/--no-confirm"' in module, path
        assert "Use --confirm to execute this destructive operation." in module, path
        assert "client.post(" in module

    def test_dry_run_post_is_not_gated(self):
        spec = {"paths": {"/api/topology/v1/virtual-edges/bulk/delete/validate": {
            "post": {"tags": ["site-controller"], "operationId": "validateBulkDelete",
                     "responses": {"200": {}}}}}}
        groups, _ = build_groups(spec)
        module = generate_module("topology", groups["topology"])
        assert "--confirm" not in module

    def test_freshly_generated_module_passes_the_gate_scan(self, tmp_path):
        """The audit's own scan must find zero ungated destructives in new output."""
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

    @pytest.mark.parametrize("argv", [
        ["topology", "bulk-force-delete-ve-ns", "--body", '{"ids":["v1","v2"]}'],
        ["topology", "bulk-delete-site", "--body", '{"ids":["s1"]}'],
        ["topology", "decommission-virtual-edge-node", "ven-1"],
        ["policy", "bulk-delete", "--body", '{"ids":["l1"]}'],
        ["devices", "detach-by-mac", "--body", '{"mac":"00:11:22:33:44:55"}'],
        ["insights", "recreate-suggestions"],
    ])
    def test_destructive_non_delete_refuses_with_no_http_call(self, argv):
        """The newly gated commands refuse, and refuse BEFORE touching the API.

        Leia's reproduction of the original defect was
        `elisity topology bulk-delete-site --body '{"ids":[...]}'` -> exit 0 with
        the POST actually sent. This is that reproduction, inverted.
        """
        calls = []

        class RecordingClient:
            def __getattr__(self, verb):
                def call(*args, **kwargs):
                    calls.append((verb, args, kwargs))
                    return {}
                return call

        import elisity_cli.context as ctxmod
        original = ctxmod.CliContext.ensure_client
        ctxmod.CliContext.ensure_client = lambda self: RecordingClient()
        try:
            result = CliRunner().invoke(cli, argv)
        finally:
            ctxmod.CliContext.ensure_client = original

        assert result.exit_code == 1, result.output
        assert "Use --confirm" in result.output
        assert calls == [], f"HTTP call made despite the gate: {calls}"

    def test_confirm_flag_is_advertised_on_a_gated_post(self):
        result = CliRunner().invoke(
            cli, ["topology", "bulk-force-delete-ve-ns", "--help"]
        )
        assert result.exit_code == 0
        assert "--confirm" in result.output

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


class TestUnmappedTagGuard:
    """A new CCC tag is a human decision, not something to route by accident.

    resolve_group() takes the first tag that hits TAG_TO_GROUP, so an unmapped
    tag riding along with a mapped one gets routed by whichever mapped tag comes
    first — which may have nothing to do with what the new tag means. The guard
    used to `continue` on any operation carrying a mapped tag, which made
    exactly that case invisible. 21 operations in the 26.7 spec already carry
    two tags (20 in 26.3), so this is the shape the next bump will have.

    The guard itself has never had a committed test; Leia proved it non-vacuous
    by hand and found the hole. These are the two specs that walked through it.
    """

    def _spec(self, path, tags):
        return {"paths": {path: {"get": {
            "tags": tags, "operationId": "doThing", "responses": {"200": {}},
        }}}}

    def test_unmapped_tag_alone_is_caught(self):
        """The case that always worked — kept so a regression is visible."""
        spec = self._spec("/api/topology/v1/x", ["Totally New Tag"])
        assert unmapped_tags(spec) == {"Totally New Tag": 1}
        with pytest.raises(SystemExit):
            assert_every_tag_mapped(spec)

    def test_unmapped_tag_beside_a_mapped_sibling_is_caught(self):
        """Leia's case (a): a new tag hiding behind a known one.

        `Site Templates (NEW 26.8)` is invisible if the guard skips any
        operation that has at least one mapped tag.
        """
        spec = self._spec(
            "/api/topology/v1/site-templates/{id}",
            ["Sites", "Site Templates (NEW 26.8)"],
        )
        assert unmapped_tags(spec) == {"Site Templates (NEW 26.8)": 1}
        with pytest.raises(SystemExit):
            assert_every_tag_mapped(spec)

    def test_incidental_sibling_routing_the_wrong_way_is_caught(self):
        """Leia's case (b), the damaging shape.

        The operation is a flows operation by path, carries a brand-new flow
        tag, and routes to `policy` on an incidental `Device` tag. The routing
        is not corrected here — resolve_group()'s first-match behaviour is
        deliberately untouched so this fix re-routes nothing — but generation
        now refuses until a human maps the tag.
        """
        spec = self._spec("/api/flows/v1/newthing", ["Brand New Flow Tag", "Device"])
        group, matched_by = resolve_group(["Brand New Flow Tag", "Device"],
                                          "/api/flows/v1/newthing")
        assert (group, matched_by) == ("policy", "tag")   # unchanged behaviour
        assert unmapped_tags(spec) == {"Brand New Flow Tag": 1}
        with pytest.raises(SystemExit):
            assert_every_tag_mapped(spec)

    def test_counts_are_per_tag_not_per_operation(self):
        spec = {"paths": {
            "/api/topology/v1/a": {"get": {"tags": ["Sites", "New A"],
                                           "operationId": "a", "responses": {"200": {}}}},
            "/api/topology/v1/b": {"get": {"tags": ["New A", "New B"],
                                           "operationId": "b", "responses": {"200": {}}}},
        }}
        assert unmapped_tags(spec) == {"New A": 2, "New B": 1}

    def test_fully_mapped_specs_still_generate(self):
        """The fix must not turn either shipped spec into a generation failure.

        Both 26.3 and 26.7 have every tag mapped, including on the 20/21
        double-tagged operations, so widening the guard changes nothing for them
        — asserted rather than assumed.
        """
        for spec_path in (SPEC_267, SPEC_263):
            if not spec_path.exists():
                pytest.skip(f"{spec_path.name} not staged in this checkout")
            spec = json.loads(spec_path.read_text())
            assert unmapped_tags(spec) == {}
            assert_every_tag_mapped(spec)   # must not raise

    def test_double_tagged_but_fully_mapped_still_generates(self):
        """The real 26.7 double-tag pair, without needing the spec file.

        PUT /api/policy/v1/insights/policy-groups/{id} carries
        ["Suggestion", "Dynamic Policy Group Insights"] — both mapped. Widening
        the guard must not turn a fully-mapped co-tagged operation into a
        failure.
        """
        spec = self._spec(
            "/api/policy/v1/insights/policy-groups/{id}",
            ["Suggestion", "Dynamic Policy Group Insights"],
        )
        assert unmapped_tags(spec) == {}
        assert_every_tag_mapped(spec)

    def test_double_tagged_operations_exist_in_the_shipped_specs(self):
        """Guards the test above against being vacuous on a single-tag spec."""
        if not SPEC_267.exists():
            pytest.skip("api-docs-26.7.json not staged in this checkout")
        spec = json.loads(SPEC_267.read_text())
        multi = [
            (path, method)
            for path, methods in spec.get("paths", {}).items()
            for method, op in methods.items()
            if isinstance(op, dict) and len(op.get("tags") or []) > 1
        ]
        assert len(multi) >= 20, len(multi)


def _drive_generated_command(module_source, argv):
    """Run a generated command through Click against a recording fake client.

    Returns the endpoint and params the command actually put on the wire. This
    is the only way to catch the silent-wrong-request class: the code compiles,
    exits 0, and sends something other than what the user typed.
    """
    import types

    import click as _click

    from elisity_cli import context as ctxmod

    namespace = types.ModuleType("generated_under_test")
    namespace.__dict__["__name__"] = "generated_under_test"
    exec(compile(module_source, "generated_under_test.py", "exec"), namespace.__dict__)

    sent = {}

    class RecordingClient:
        def _record(self, endpoint, params=None, data=None):
            sent.update({"endpoint": endpoint, "params": params, "data": data})
            return [{"ok": True}]

        get = post = put = patch = delete = get_ndjson = _record

    @_click.group()
    @_click.pass_context
    def root(ctx):
        ctx.obj = ctxmod.CliContext()

    root.add_command(namespace.group)

    original = ctxmod.CliContext.ensure_client
    ctxmod.CliContext.ensure_client = lambda self: RecordingClient()
    try:
        result = CliRunner().invoke(root, [namespace.group.name] + argv)
    finally:
        ctxmod.CliContext.ensure_client = original

    assert result.exit_code == 0, result.output
    return sent


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
        ("body locals", ["params", "endpoint"]),
        ("every body local", ["endpoint", "params", "body", "client", "result"]),
        ("all at once", ["ctx", "confirm", "format", "query", "cmd_fmt", "body_file"]),
    ])
    def test_reserved_identifier_names_reach_the_wire(self, label, names):
        """Any spec param name must be absorbable, not just the ones seen so far.

        Asserted by DRIVING the generated command, not by scanning its source.
        The source-text version of this test passed on code that corrupted the
        request: for a parameter named `params` the broken module emits
        `params["params"] = params` — which contains the literal the assertion
        looked for, compiles, and at exit 0 sends the params dict as its own
        value while the user's input never leaves the process. A test that
        cannot fail on the bug it names is worse than no test; it is a claim of
        coverage.
        """
        module = _generate_one("get", "/api/topology/v2/w", [
            {"name": n, "in": "query", "schema": {"type": "string"}} for n in names
        ])
        compile(module, "topology.py", "exec")
        for n in names:
            assert f'params["{n}"]' in module, f"{n} is no longer sent on the wire"

        # Drive with the flags the generator ACTUALLY emits: a name colliding
        # with one of the CLI's own flags (--format, --body, ...) is renamed,
        # while the wire name stays the spec name.
        _, resolved = resolve_parameter_names(
            "get", [], [(n, "str", False, "", None) for n in names],
            "/api/topology/v2/w",
        )
        argv = ["do-thing"]
        for spec in resolved:
            argv += [spec["flag"], f"VALUE-{spec['spec_name']}"]
        sent = _drive_generated_command(module, argv)
        assert sent["params"] == {n: f"VALUE-{n}" for n in names}, (
            f"{label}: the user's values did not reach the wire intact"
        )
        assert sent["endpoint"] == "/api/topology/v2/w"

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

    def test_undeclared_path_template_gets_an_argument(self):
        """The spec's path declares {id} but omits the parameter. Without a
        synthesized argument the f-string resolved `id` to Python's builtin and
        sent '<built-in function id>' in the URL, at exit code 0."""
        module = _generate_one("post", "/api/x/{id}/import/{uploadId}/cancel", [
            {"name": "uploadId", "in": "path", "required": True,
             "schema": {"type": "string"}},
        ])
        compile(module, "topology.py", "exec")

        assert '@click.argument("id")' in module
        assert '@click.argument("uploadid")' in module
        assert "def cmd_do_thing(ctx, id, uploadid," in module

    def test_no_committed_endpoint_has_an_unsubstituted_placeholder(self):
        """Whole-tree sweep: every f-string placeholder in a generated endpoint
        must correspond to an argument of its own function."""
        offenders = []
        for path in sorted(COMMANDS_DIR.glob("*.py")):
            source = path.read_text()
            for block in source.split("@group.command(")[1:]:
                name = block.split('"')[1]
                sig = re.search(r"def cmd_\w+\(([^)]*)\):", block)
                endpoint = re.search(r'endpoint = f"([^"]*)"', block)
                if not sig or not endpoint:
                    continue
                args = {a.strip() for a in sig.group(1).split(",")}
                for placeholder in re.findall(r"\{([^}]*)\}", endpoint.group(1)):
                    if placeholder not in args:
                        offenders.append(f"{path.stem} {name}: {{{placeholder}}}")
        assert offenders == [], (
            "endpoint placeholders with no matching function argument (these "
            "resolve against builtins or raise NameError at runtime): "
            + ", ".join(offenders)
        )

    def test_cancel_import_builds_a_correct_url(self):
        """Regression for the live bug — end-to-end through Click."""
        captured = {}

        class FakeClient:
            def post(self, endpoint, data=None, params=None):
                captured["endpoint"] = endpoint
                return {}

        import elisity_cli.context as ctxmod
        original = ctxmod.CliContext.ensure_client
        ctxmod.CliContext.ensure_client = lambda self: FakeClient()
        try:
            result = CliRunner().invoke(
                cli, ["connectors", "cancel-import", "CONN42", "UPLOAD123"]
            )
        finally:
            ctxmod.CliContext.ensure_client = original

        assert result.exit_code == 0, result.output
        assert captured["endpoint"] == (
            "/api/identity-graph/v1/custom-connector/CONN42/import/UPLOAD123/cancel"
        )

    def test_unusable_path_template_is_a_generation_error(self):
        """A template with no usable name must fail generation, not emit
        code that cannot compile."""
        with pytest.raises(ValueError, match="no usable name"):
            merge_path_templates("/api/x/{}/y", [])

    def test_declared_path_param_absent_from_template_is_kept(self):
        merged = merge_path_templates("/api/x/{id}", [
            ("id", "str", ""), ("orphan", "str", ""),
        ])
        assert [m[0] for m in merged] == ["id", "orphan"]

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
        # `size` goes on the wire as an int, not a string: CCC 26.7 declares it
        # {"type": "integer", "format": "int32"} where 26.3 declared only
        # {"format": "int32"} with no `type` key, which the generator could only
        # treat as a string. Seven query parameters gained a type this way in
        # 26.7. The renamed --format-param flag must still send `format`.
        assert captured["params"] == {"format": "csv", "size": 10}


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

    def test_command_reference_is_regenerated(self):
        """docs/command-reference.md must match what the source would produce.

        It is a generated file, but nothing stops a regeneration from landing
        without it. When that happened on the 26.7 bump the doc listed 45
        commands that no longer existed and none of the 192 new ones — and a
        command reference that confidently documents removed commands is worse
        than none, because a reader cannot tell which entries are real.
        """
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "gen_command_reference.py"), "--check"],
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

        # Derive the claim from the source rather than hardcoding it. A literal
        # count here goes stale on the next spec bump, and a stale literal makes
        # the replace a no-op: no drift is injected, the audit correctly reports
        # nothing, and this negative test fails for the wrong reason. That is
        # exactly what happened on the 26.7 bump (466 -> 613).
        total = collect_counts()["totals"]["total"]
        marker = f"**{total} commands** total"
        original = ac.README.read_text()
        assert marker in original, (
            f"README does not state its total as {marker!r}; this test can no "
            "longer inject drift and must be updated with the README's wording."
        )

        fake = tmp_path / "README.md"
        fake.write_text(original.replace(marker, "**999999 commands** total"))
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
