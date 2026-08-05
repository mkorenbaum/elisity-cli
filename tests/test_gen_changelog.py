"""Tests for tools/gen_changelog.py.

The changelog is the artifact a customer reads to find out what broke, so the
cases that matter are the ones that mislead when rendered wrongly: a removal
that is not flagged breaking, a rename shown as an addition, a body-only change
implying a signature break, and a parameter whose type went missing.
"""

import importlib.util
import json
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def _load_module():
    spec = importlib.util.spec_from_file_location("gen_changelog", TOOLS / "gen_changelog.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load_module()


def _diff(added=None, removed=None, changed=None, **summary):
    base = {
        "oldPathCount": 1,
        "newPathCount": 1,
        "oldOperationCount": 1,
        "newOperationCount": 1,
    }
    base.update(summary)
    return {
        "added": added or [],
        "removed": removed or [],
        "changed": changed or [],
        "summary": base,
    }


def _op(command="do-thing", group="policy", method="GET", path="/api/x", summary="", tags=None):
    return {
        "command": command,
        "group": group,
        "method": method,
        "path": path,
        "summary": summary,
        "tags": tags or ["Some Tag"],
    }


def _changed(command="do-thing", group="policy", changes=None):
    return {
        "command": command,
        "group": group,
        "method": "GET",
        "path": "/api/x",
        "changes": changes or {},
    }


def render(diff):
    return gen.render(diff, version="26.7", source="tenant.example", baseline="26.3")


# --------------------------------------------------------------------------
# Removals — the breaking case
# --------------------------------------------------------------------------


class TestRemovals:
    def test_removed_commands_are_listed_and_flagged_breaking(self):
        out = render(_diff(removed=[_op(command="delete-user", group="ad", summary="Delete AD user")]))
        assert "Removed commands (breaking)" in out
        assert "`elisity ad delete-user` — Delete AD user" in out

    def test_removals_are_grouped_by_spec_tag(self):
        out = render(
            _diff(
                removed=[
                    _op(command="a", tags=["AD User"]),
                    _op(command="b", tags=["AD User"]),
                    _op(command="c", tags=["AD Group"]),
                ]
            )
        )
        assert "**AD User** (2)" in out
        assert "**AD Group** (1)" in out

    def test_no_removals_says_none_rather_than_omitting_the_section(self):
        # A missing section reads as "not checked"; an explicit None reads as
        # "checked, nothing to report".
        out = render(_diff(added=[_op()]))
        removed_section = out.split("### Removed commands (breaking)")[1].split("###")[0]
        assert "None." in removed_section


# --------------------------------------------------------------------------
# Change classification
# --------------------------------------------------------------------------


class TestChangeClassification:
    def test_parameter_change_is_a_signature_change(self):
        entry = _changed(changes={"parameters": {"added": [{"name": "q", "required": False, "type": "string"}]}})
        assert gen._classify_change(entry) == "signature"

    def test_request_body_change_is_not_a_signature_change(self):
        # The generator emits the body as one opaque --body option, so a body
        # schema change cannot alter the command's flags. Calling it a
        # signature change would overstate the breakage.
        entry = _changed(changes={"requestBody": {"status": "changed"}})
        assert gen._classify_change(entry) == "body"

    def test_response_only_change_is_classified_response_only(self):
        entry = _changed(changes={"responses": {"added": ["202"]}})
        assert gen._classify_change(entry) == "response-only"

    def test_response_only_changes_are_counted_not_enumerated(self):
        out = render(_diff(changed=[_changed(command="quiet-cmd", changes={"responses": {"added": ["202"]}})]))
        assert "1 operations changed only in their response schema" in out
        assert "quiet-cmd" not in out

    def test_rename_is_reported_as_a_change_not_an_addition(self):
        out = render(_diff(changed=[_changed(command="get-state", changes={"command": {"from": "get-state-get", "to": "get-state"}})]))
        assert "renamed from `get-state-get`" in out
        assert "### Added commands" in out
        added_section = out.split("### Added commands")[1]
        assert "get-state" not in added_section


# --------------------------------------------------------------------------
# Signature detail rendering
# --------------------------------------------------------------------------


class TestSignatureDetail:
    def test_added_parameter_reports_name_requiredness_and_type(self):
        entry = _changed(changes={"parameters": {"added": [{"name": "size", "required": True, "type": "integer"}]}})
        assert gen._signature_detail(entry) == "new required `--size` (integer)"

    def test_removed_parameter_is_reported(self):
        entry = _changed(changes={"parameters": {"removed": [{"name": "columnFilter"}]}})
        assert "dropped `--columnFilter`" in gen._signature_detail(entry)

    def test_retype_uses_the_from_to_shape_spec_diff_actually_emits(self):
        # Regression guard: an earlier version assumed {"name":..,"type":{"from","to"}}
        # and silently rendered every retype as a bare "parameters changed".
        entry = _changed(
            changes={
                "parameters": {
                    "changed": [
                        {
                            "parameter": "query:size",
                            "from": {"name": "size", "type": "unknown", "required": True},
                            "to": {"name": "size", "type": "integer", "required": True},
                        }
                    ]
                }
            }
        )
        detail = gen._signature_detail(entry)
        assert "`--size`" in detail
        assert "integer" in detail
        assert detail != "parameters changed"

    def test_requiredness_flip_is_reported(self):
        entry = _changed(
            changes={
                "parameters": {
                    "changed": [
                        {
                            "parameter": "query:filters",
                            "from": {"name": "filters", "type": "object", "required": False},
                            "to": {"name": "filters", "type": "object", "required": True},
                        }
                    ]
                }
            }
        )
        assert "became required" in gen._signature_detail(entry)

    def test_untyped_is_explained_rather_than_shown_as_unknown(self):
        # "unknown -> integer" reads like a tooling gap. It is really the spec
        # gaining a type it never had, and the CLI sent a string meanwhile.
        assert gen._type_label("unknown") == "untyped (sent as string)"
        assert gen._type_label(None) == "untyped (sent as string)"
        assert gen._type_label("integer") == "integer"


# --------------------------------------------------------------------------
# Descriptions must come from the spec, never be invented
# --------------------------------------------------------------------------


class TestDescriptions:
    def test_summary_is_used_when_present(self):
        assert gen._describe(_op(summary="List all Vendors")) == "List all Vendors"

    def test_missing_summary_falls_back_to_method_and_path(self):
        # Inventing a description would put words in the API's mouth.
        assert gen._describe(_op(summary="", method="PUT", path="/api/y")) == "`PUT /api/y`"

    def test_multiline_summary_is_flattened_to_one_line(self):
        assert "\n" not in gen._describe(_op(summary="Line one\nline two"))


# --------------------------------------------------------------------------
# Totals
# --------------------------------------------------------------------------


class TestTotals:
    def test_headline_counts_match_the_diff_contents(self):
        out = render(
            _diff(
                added=[_op(command="a"), _op(command="b")],
                removed=[_op(command="c")],
                changed=[_changed(command="d", changes={"responses": {}})],
            )
        )
        assert "**2 commands added, 1 removed, 1 operations changed.**" in out

    def test_spec_path_and_operation_totals_are_rendered(self):
        out = render(_diff(oldOperationCount=436, newOperationCount=583, oldPathCount=329, newPathCount=441))
        assert "| Spec operations | 436 | 583 |" in out
        assert "| Spec paths | 329 | 441 |" in out


# --------------------------------------------------------------------------
# End to end against the real 26.7 diff, when it is present
# --------------------------------------------------------------------------


REAL_DIFF = Path(__file__).resolve().parent.parent.parent / "output" / "SPEC-DIFF-26.7.json"


@pytest.mark.skipif(not REAL_DIFF.exists(), reason="26.7 diff artifact not present")
class TestAgainstRealDiff:
    def test_every_signature_change_renders_a_specific_reason(self):
        diff = json.loads(REAL_DIFF.read_text())
        vague = [
            c["command"]
            for c in diff["changed"]
            if gen._classify_change(c) == "signature"
            and gen._signature_detail(c) == "parameters changed"
        ]
        assert not vague, f"signature changes rendered without detail: {vague}"

    def test_renders_without_error_and_covers_every_removal(self):
        diff = json.loads(REAL_DIFF.read_text())
        out = render(diff)
        for op in diff["removed"]:
            assert f"`elisity {op['group']} {op['command']}`" in out
