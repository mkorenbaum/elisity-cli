"""
Output formatting — JSON, table, YAML, CSV with optional JMESPath filtering.
"""

import csv
import io
import json
import sys
from typing import Any, Optional

import click
import jmespath
from rich.console import Console
from rich.table import Table

console = Console(stderr=True)
output_console = Console()


def apply_query(data: Any, query: Optional[str]) -> Any:
    """Apply JMESPath query to data."""
    if not query:
        return data
    try:
        return jmespath.search(query, data)
    except jmespath.exceptions.JMESPathError as e:
        click.echo(f"JMESPath error: {e}", err=True)
        sys.exit(1)


def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def format_table(data: Any) -> str:
    """Render data as a rich table. Handles list of dicts or single dict."""
    if isinstance(data, dict):
        # Check for paginated response
        if "content" in data and isinstance(data["content"], list):
            data = data["content"]
        else:
            data = [data]
    if not isinstance(data, list) or len(data) == 0:
        return json.dumps(data, indent=2, default=str)

    # Flatten nested dicts one level for display
    flat = []
    for item in data:
        if isinstance(item, dict):
            row = {}
            for k, v in item.items():
                if isinstance(v, (dict, list)):
                    row[k] = json.dumps(v, default=str)[:80]
                else:
                    row[k] = str(v) if v is not None else ""
            flat.append(row)
        else:
            flat.append({"value": str(item)})

    if not flat:
        return "(empty)"

    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    cols = list(flat[0].keys())
    for col in cols:
        table.add_column(col, overflow="fold", max_width=60)
    for row in flat:
        table.add_row(*[row.get(c, "") for c in cols])

    buf = io.StringIO()
    temp_console = Console(file=buf, force_terminal=False, width=200)
    temp_console.print(table)
    return buf.getvalue()


def format_yaml(data: Any) -> str:
    import yaml
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def format_csv(data: Any) -> str:
    if isinstance(data, dict):
        if "content" in data:
            data = data["content"]
        else:
            data = [data]
    if not isinstance(data, list) or not data:
        return ""
    buf = io.StringIO()
    if isinstance(data[0], dict):
        writer = csv.DictWriter(buf, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    else:
        writer = csv.writer(buf)
        for item in data:
            writer.writerow([item])
    return buf.getvalue()


FORMATTERS = {
    "json": format_json,
    "table": format_table,
    "yaml": format_yaml,
    "csv": format_csv,
}


def render(data: Any, fmt: str = "json", query: Optional[str] = None):
    """Apply optional query and render in requested format to stdout."""
    data = apply_query(data, query)
    formatter = FORMATTERS.get(fmt, format_json)
    output = formatter(data)
    click.echo(output)
