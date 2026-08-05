"""Tests for the `elisity glossary` command group."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from elisity_cli.commands import glossary as glossary_mod
from elisity_cli.main import cli


REPO_ROOT = Path(__file__).resolve().parents[1]
GLOSSARY_PATH = REPO_ROOT / "data" / "product-glossary.json"
MAPPING_PATH = REPO_ROOT / "data" / "ui-to-cli-mapping.json"


@pytest.fixture
def runner():
    return CliRunner()


def test_mapping_file_loads():
    """ui-to-cli-mapping.json is a non-empty list whose entries have the
    expected shape."""
    data = json.loads(MAPPING_PATH.read_text())
    assert isinstance(data, list)
    assert len(data) > 0
    required = {"term", "synonyms", "context", "domain"}
    for entry in data:
        missing = required - set(entry.keys())
        assert not missing, f"entry {entry.get('term')!r} missing fields: {missing}"


def test_every_glossary_term_has_mapping():
    """Every `correct` term in product-glossary.json has a matching `term`
    in ui-to-cli-mapping.json."""
    glossary = json.loads(GLOSSARY_PATH.read_text())
    mapping = json.loads(MAPPING_PATH.read_text())
    mapping_terms = {e["term"] for e in mapping}
    for term in glossary["terms"]:
        assert (
            term["correct"] in mapping_terms
        ), f"glossary term {term['correct']!r} has no entry in ui-to-cli-mapping.json"


def test_search_finds_synonym(runner):
    """`elisity glossary search "monitor mode"` returns the Simulation entry."""
    result = runner.invoke(cli, ["glossary", "search", "monitor mode"])
    assert result.exit_code == 0, result.output
    assert "Simulation" in result.output


def test_explain_returns_recipes(runner):
    """`elisity glossary explain "VEN"` returns Virtual Edge Node + recipes."""
    result = runner.invoke(cli, ["glossary", "explain", "VEN"])
    assert result.exit_code == 0, result.output
    assert "Virtual Edge Node" in result.output
    assert "CLI recipes" in result.output


def test_explain_zero_trust_score_returns_enforcement_score(runner):
    """`elisity glossary explain "Zero Trust score"` resolves to Policy
    Enforcement Score with at least one recipe."""
    result = runner.invoke(cli, ["glossary", "explain", "Zero Trust score"])
    assert result.exit_code == 0, result.output
    assert "Policy Enforcement Score" in result.output
    assert "get-aggregate-enforcement-score" in result.output


def test_unknown_term_exits_nonzero(runner):
    """A gibberish search term exits with status 1 and writes to stderr."""
    result = runner.invoke(cli, ["glossary", "search", "qzqzqzqzqz-not-a-term"])
    assert result.exit_code == 1


def test_list_returns_every_mapped_term(runner):
    """`elisity glossary list` surfaces every entry in the mapping file.

    Asserted against the mapping rather than a literal count: a hardcoded number
    here has to be edited by hand every time a term is added, and the edit is
    easy to forget. What actually matters is that `list` hides nothing.
    """
    expected = len(json.loads(MAPPING_PATH.read_text()))
    result = runner.invoke(cli, ["glossary", "list"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == expected


def test_glossary_group_registered():
    """`glossary` is in COMMAND_GROUPS."""
    from elisity_cli.commands import COMMAND_GROUPS

    assert "glossary" in COMMAND_GROUPS


def test_data_path_resolves():
    """The data-path resolver finds both JSON files."""
    assert glossary_mod._data_path("product-glossary.json").exists()
    assert glossary_mod._data_path("ui-to-cli-mapping.json").exists()


def test_every_referenced_command_exists():
    """No glossary entry may cite a command that does not exist.

    The glossary is the agent-facing lookup surface — docs/AGENTS.md tells an
    agent to run `glossary explain` and then run the recipe it returns. A dead
    recipe therefore hands an agent a fabricated command, which is precisely the
    failure mode AGENTS.md calls non-negotiable.

    CCC 26.7 made this concrete: it removed `policy get-enforcement-score`,
    `policy get-enforcement-score-weight-settings`, `flows get-latest-data` and
    `flows get-all`, all four of which were still cited here. Nothing caught it,
    because the counts all still agreed.
    """
    import re

    mapping = json.loads(MAPPING_PATH.read_text())

    # Build the real command surface straight from the registered Click groups,
    # so this can never drift from what the CLI actually exposes.
    from elisity_cli.commands import COMMAND_GROUPS

    real = {}
    for name in COMMAND_GROUPS:
        mod = __import__(f"elisity_cli.commands.{name}", fromlist=["group"])
        real[name] = set(mod.group.commands)
    real["auth"] = {"test", "token", "whoami"}
    real["config"] = {"set-profile", "use-profile", "list-profiles", "show"}

    reference_re = re.compile(r"elisity ([a-z][a-z0-9-]*) ([a-z][a-z0-9-]*)")
    bad = []
    for entry in mapping:
        for group, command in reference_re.findall(json.dumps(entry)):
            if group not in real:
                bad.append(f"{entry['term']}: unknown group 'elisity {group}'")
            elif command not in real[group]:
                bad.append(f"{entry['term']}: no such command 'elisity {group} {command}'")

    assert not bad, "glossary cites commands that do not exist:\n  " + "\n  ".join(sorted(set(bad)))
