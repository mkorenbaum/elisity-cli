"""Glossary — map Elisity UI terminology to CLI commands.

Backed by data/product-glossary.json (upstream truth) and
data/ui-to-cli-mapping.json (CLI recipes derived from the 462-command surface).

Three subcommands:
    elisity glossary list                       — terse summary of all 19 terms
    elisity glossary search "<phrase>"          — full mapping entry for any synonym
    elisity glossary explain "<phrase>"         — agent-friendly prose + recipes
"""

import json
import re
from pathlib import Path

import click

from elisity_cli.context import pass_context
from elisity_cli.output import render


def _candidate_data_dirs():
    """Yield possible locations for the data/ directory.

    Resolution order:
      1. ``<repo-root>/data`` when running editable from a source checkout
         (``src/elisity_cli/commands/glossary.py`` → parents[3] == repo root).
      2. ``<package>/data`` when ``data/`` was shipped inside the wheel
         (set up via ``[tool.setuptools.package-data]``).
    """
    here = Path(__file__).resolve()
    yield here.parents[3] / "data"
    yield here.parents[1] / "data"


def _data_path(filename):
    for d in _candidate_data_dirs():
        candidate = d / filename
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate {filename}. Looked in: "
        + ", ".join(str(d) for d in _candidate_data_dirs())
    )


def _load_mapping():
    return json.loads(_data_path("ui-to-cli-mapping.json").read_text())


def _load_glossary():
    return json.loads(_data_path("product-glossary.json").read_text())


def _normalize(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _matches(entry, q_norm):
    """Return True if any term/synonym in entry matches the normalized query."""
    haystack = [entry["term"]] + list(entry.get("synonyms", []))
    for h in haystack:
        h_norm = _normalize(h)
        if not h_norm or not q_norm:
            continue
        if q_norm in h_norm or h_norm in q_norm:
            return True
    return False


@click.group("glossary")
def group():
    """Map Elisity UI terms (e.g. 'monitor mode') to CLI commands.

    Backed by data/ui-to-cli-mapping.json. For agents operating the CLI on
    behalf of humans, see docs/AGENTS.md.
    """


@group.command("list")
@pass_context
def list_terms(ctx):
    """List all glossary terms (canonical name + domain + enum value)."""
    entries = _load_mapping()
    summary = [
        {
            "term": e["term"],
            "domain": e.get("domain", ""),
            "enum_value": e.get("enum_value"),
        }
        for e in entries
    ]
    render(summary, ctx.format, ctx.query)


@group.command("search")
@click.argument("query", nargs=-1, required=True)
@pass_context
def search(ctx, query):
    """Search by canonical term or synonym. Returns full mapping entries.

    Examples:
      elisity glossary search "monitor mode"
      elisity glossary search VEN
      elisity glossary search posture score
    """
    q = _normalize(" ".join(query))
    entries = _load_mapping()
    matches = [e for e in entries if _matches(e, q)]
    if not matches:
        click.echo(f"No glossary term matched: {' '.join(query)}", err=True)
        raise SystemExit(1)
    render(matches, ctx.format, ctx.query)


@group.command("explain")
@click.argument("query", nargs=-1, required=True)
@pass_context
def explain(ctx, query):
    """Human-readable explanation of a term + its CLI recipes.

    Designed for agents: returns prose rather than JSON, so an LLM reading
    the output gets ready-to-paste commands.
    """
    q = _normalize(" ".join(query))
    entries = _load_mapping()
    match = next((e for e in entries if _matches(e, q)), None)
    if not match:
        click.echo(f"No glossary term matched: {' '.join(query)}", err=True)
        raise SystemExit(1)

    click.echo(f"Term: {match['term']}")
    if match.get("enum_value"):
        click.echo(f"Enum value: {match['enum_value']}")
    click.echo(f"Domain: {match.get('domain', 'unknown')}")
    if match.get("synonyms"):
        click.echo(f"Also called: {', '.join(match['synonyms'])}")
    click.echo("")
    click.echo("Context:")
    click.echo(f"  {match['context']}")

    recipes = match.get("cli_recipes", [])
    if recipes:
        click.echo("")
        click.echo("CLI recipes:")
        for r in recipes:
            click.echo("")
            click.echo(f"  # {r['intent']}")
            click.echo(f"  {r['command']}")
            if r.get("notes"):
                click.echo(f"  # {r['notes']}")
    else:
        click.echo("")
        click.echo("(no direct CLI surface for this term — terminology only)")
        if match.get("note"):
            click.echo(f"  {match['note']}")

    related = match.get("related_commands", [])
    if related:
        click.echo("")
        click.echo("Related commands:")
        for c in related:
            click.echo(f"  - {c}")
