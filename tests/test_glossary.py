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


# --------------------------------------------------------------------------
# Runnable-reference sweep
# --------------------------------------------------------------------------

# Every file that tells a human or an agent to run something. The old version of
# this check read ui-to-cli-mapping.json ONLY, so the prose copies of the same
# recipes were unguarded — and CCC 26.7 left six of them citing commands it had
# removed, in the very files docs/AGENTS.md points an agent at. Two of the four
# fabricated recipes found earlier were fixed in the JSON and left in the prose.
REFERENCE_FILES = (
    sorted((REPO_ROOT / "docs").glob("*.md"))
    + [
        REPO_ROOT / "README.md",
        REPO_ROOT / "BACKLOG.md",
        REPO_ROOT / "VALIDATION_PROCEDURE.md",
        REPO_ROOT / "data" / "ui-to-cli-mapping.json",
        REPO_ROOT / "data" / "product-glossary.json",
        # The packaged copies are what `pip install .` actually ships.
        REPO_ROOT / "src" / "elisity_cli" / "data" / "ui-to-cli-mapping.json",
        REPO_ROOT / "src" / "elisity_cli" / "data" / "product-glossary.json",
    ]
)

# Sections that are SUPPOSED to name commands that no longer exist. Excluded by
# heading rather than by listing the commands, so the changelog can grow without
# anyone maintaining an allowlist.
EXCLUDED_SECTION_HEADINGS = (
    "### Removed commands (breaking)",
    "### Command names now pointing at a different endpoint (breaking, silent)",
)

# Deliberate non-commands, each with the reason it is here.
ALLOWED_DEAD_REFERENCES = {
    "topology fake-command":
        "VALIDATION_PROCEDURE.md step 12 — the negative test that proves an "
        "unknown command exits non-zero. It must not exist.",
}


def _command_surface():
    """The real command surface, straight from the registered Click groups."""
    from elisity_cli.commands import COMMAND_GROUPS

    real = {}
    for name in COMMAND_GROUPS:
        mod = __import__(f"elisity_cli.commands.{name}", fromlist=["group"])
        real[name] = set(mod.group.commands)
    real["auth"] = {"test", "token", "whoami"}
    real["config"] = {"set-profile", "use-profile", "list-profiles", "show"}
    return real


def _strip_excluded_sections(text):
    """Drop sections whose whole purpose is to name removed commands."""
    for heading in EXCLUDED_SECTION_HEADINGS:
        while heading in text:
            start = text.index(heading)
            nxt = text.find("\n### ", start + len(heading))
            end = len(text) if nxt < 0 else nxt
            text = text[:start] + text[end:]
    return text


def _referenced_commands(text):
    """(group, command) for every `elisity ... <group> <command>` in the text.

    Tolerates the global flags the CLI requires BEFORE the group name
    (`elisity -f table -q '[]' reporting get-site-kpis`), and rejoins the
    hyphen-wrapped lines that appear in pasted `--help` transcripts, where Click
    breaks a command name mid-token.
    """
    import re

    text = re.sub(r"-\n\s+", "-", text)
    pattern = re.compile(
        r"elisity\s+(?:-\S+\s+(?:'[^']*'|\"[^\"]*\"|\S+)\s+)*"
        r"([a-z][a-z0-9-]*)\s+([a-z][a-z0-9-]*)"
    )
    return pattern.findall(text)


def test_every_referenced_command_exists():
    """No file may tell anyone to run a command that does not exist.

    The glossary is the agent-facing lookup surface — docs/AGENTS.md tells an
    agent to run `glossary explain` and then run the recipe it returns. A dead
    recipe therefore hands an agent a fabricated command, which is precisely the
    failure mode AGENTS.md calls non-negotiable. The same is true of a runnable
    ```bash``` block in the user guide.

    CCC 26.7 made this concrete: it removed `policy get-enforcement-score`,
    `policy get-enforcement-score-weight-settings`, `flows get-latest-data`,
    `flows get-all`, `devices get-device-count` and
    `ad get-user-by-sid-and-domain`, all of which were still cited somewhere.
    Nothing caught it, because the counts all still agreed and this check only
    read one JSON file.
    """
    real = _command_surface()
    bad = []
    checked = 0
    for path in REFERENCE_FILES:
        text = _strip_excluded_sections(path.read_text())
        for group, command in _referenced_commands(text):
            if group not in real:
                continue          # not a command group — ordinary prose
            checked += 1
            if command in real[group]:
                continue
            if f"{group} {command}" in ALLOWED_DEAD_REFERENCES:
                continue
            bad.append(
                f"{path.relative_to(REPO_ROOT)}: no such command "
                f"'elisity {group} {command}'"
            )

    assert checked > 500, (
        f"only {checked} references matched — the sweep stopped seeing the docs, "
        "which would make it pass vacuously"
    )
    assert not bad, (
        "documentation cites commands that do not exist:\n  "
        + "\n  ".join(sorted(set(bad)))
    )


def test_the_reference_sweep_can_fail(tmp_path):
    """Non-vacuity: the sweep must reject a command that does not exist."""
    real = _command_surface()
    refs = _referenced_commands("Run `elisity policy totally-fake-command` now.")
    assert refs == [("policy", "totally-fake-command")]
    assert "totally-fake-command" not in real["policy"]


def test_excluded_sections_are_scoped_to_their_own_section():
    """The exclusion must not swallow the rest of the document.

    It drops from the heading to the next `### `, so a stale reference in the
    section AFTER the changelog's removal list is still caught.
    """
    text = (
        "### Removed commands (breaking)\n"
        "- `elisity policy get-enforcement-score` — gone\n"
        "\n### Something else\n"
        "- `elisity policy still-checked-here`\n"
    )
    stripped = _strip_excluded_sections(text)
    assert "get-enforcement-score" not in stripped
    assert "still-checked-here" in stripped


def test_packaged_data_matches_the_repo_copy():
    """`pip install .` ships src/elisity_cli/data/, not data/.

    `commands/glossary.py` prefers the repo-root `data/` when running from a
    source checkout and falls back to the packaged copy in a wheel — so every
    test, and every developer, reads the repo copy while USERS read the packaged
    one. The packaged ui-to-cli-mapping.json was a full CCC release behind: it
    still recommended `policy get-enforcement-score-weight-settings` and
    `flows get-latest-data`, and was missing every 26.7 term. Nothing compared
    them.
    """
    for name in ("ui-to-cli-mapping.json", "product-glossary.json"):
        repo_copy = json.loads((REPO_ROOT / "data" / name).read_text())
        packaged = json.loads(
            (REPO_ROOT / "src" / "elisity_cli" / "data" / name).read_text()
        )
        assert repo_copy == packaged, (
            f"{name}: the packaged copy differs from data/{name}. Users install "
            "the packaged one; run `cp data/*.json src/elisity_cli/data/`."
        )
