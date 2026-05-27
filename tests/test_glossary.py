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


def test_list_returns_19_terms(runner):
    """`elisity glossary list` returns 19 entries."""
    result = runner.invoke(cli, ["glossary", "list"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 19


def test_glossary_group_registered():
    """`glossary` is in COMMAND_GROUPS."""
    from elisity_cli.commands import COMMAND_GROUPS

    assert "glossary" in COMMAND_GROUPS


def test_data_path_resolves():
    """The data-path resolver finds both JSON files."""
    assert glossary_mod._data_path("product-glossary.json").exists()
    assert glossary_mod._data_path("ui-to-cli-mapping.json").exists()
