"""
Traffic analytics — device state, flow search, noise definitions

Auto-generated from the Elisity CCC OpenAPI specification.
"""

import click

from elisity_cli.context import CliContext, pass_context
from elisity_cli.output import render


@click.group("flows")
@pass_context
def group(ctx):
    """Traffic analytics — device state, flow search, noise definitions"""
    pass

@group.command("get-raw-traffic-summary")
@click.option("--body", "body_data", type=str, default=None, help="Request body as JSON string")
@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None, help="Read request body from JSON file")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_raw_traffic_summary(ctx, body_data, body_file, cmd_fmt, cmd_query):
    """Get traffic summary data"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/nflowsearch/api/v1/trafficsummary"
    params = None
    body = None
    if body_file:
        import json as _json
        with open(body_file) as f:
            body = _json.load(f)
    elif body_data:
        import json as _json
        body = _json.loads(body_data)
    client = ctx.ensure_client()
    try:
        result = client.post(endpoint, data=body, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-traffic-record")
@click.option("--offset", "offset", type=str, required=True, help="offset")
@click.option("--size", "size", type=str, required=True, help="size")
@click.option("--body", "body_data", type=str, default=None, help="Request body as JSON string")
@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None, help="Read request body from JSON file")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_traffic_record(ctx, offset, size, body_data, body_file, cmd_fmt, cmd_query):
    """POST /nflowsearch/api/v1/trafficRecord"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/nflowsearch/api/v1/trafficRecord"
    params = {}
    if offset is not None:
        params["offset"] = offset
    if size is not None:
        params["size"] = size
    body = None
    if body_file:
        import json as _json
        with open(body_file) as f:
            body = _json.load(f)
    elif body_data:
        import json as _json
        body = _json.loads(body_data)
    client = ctx.ensure_client()
    try:
        result = client.post(endpoint, data=body, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-pg-data")
@click.option("--format-param", "format", type=str, required=True, help="[sends format] format")
@click.option("--size", "size", type=str, required=True, help="size")
@click.option("--body", "body_data", type=str, default=None, help="Request body as JSON string")
@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None, help="Read request body from JSON file")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_pg_data(ctx, format, size, body_data, body_file, cmd_fmt, cmd_query):
    """POST /nflowsearch/api/v1/pgdata"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/nflowsearch/api/v1/pgdata"
    params = {}
    if format is not None:
        params["format"] = format
    if size is not None:
        params["size"] = size
    body = None
    if body_file:
        import json as _json
        with open(body_file) as f:
            body = _json.load(f)
    elif body_data:
        import json as _json
        body = _json.loads(body_data)
    client = ctx.ensure_client()
    try:
        result = client.post(endpoint, data=body, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("flows-export")
@click.option("--size", "size", type=str, default=20, help="Number of results to return")
@click.option("--offset", "offset", type=str, required=True, help="offset")
@click.option("--body", "body_data", type=str, default=None, help="Request body as JSON string")
@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None, help="Read request body from JSON file")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_flows_export(ctx, size, offset, body_data, body_file, cmd_fmt, cmd_query):
    """Generate flows export as CSV"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/nflowsearch/api/v1/flowdata"
    params = {}
    if size is not None:
        params["size"] = size
    if offset is not None:
        params["offset"] = offset
    body = None
    if body_file:
        import json as _json
        with open(body_file) as f:
            body = _json.load(f)
    elif body_data:
        import json as _json
        body = _json.loads(body_data)
    client = ctx.ensure_client()
    try:
        result = client.post(endpoint, data=body, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-dash-board-summary-data")
@click.option("--body", "body_data", type=str, default=None, help="Request body as JSON string")
@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None, help="Read request body from JSON file")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_dash_board_summary_data(ctx, body_data, body_file, cmd_fmt, cmd_query):
    """POST /nflowsearch/api/v1/dashboardSummary"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/nflowsearch/api/v1/dashboardSummary"
    params = None
    body = None
    if body_file:
        import json as _json
        with open(body_file) as f:
            body = _json.load(f)
    elif body_data:
        import json as _json
        body = _json.loads(body_data)
    client = ctx.ensure_client()
    try:
        result = client.post(endpoint, data=body, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-noise-definition")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_noise_definition(ctx, cmd_fmt, cmd_query):
    """GET /api/flows/v1/noisedefinition"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/noisedefinition"
    params = None
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("update-noise-definition")
@click.option("--body", "body_data", type=str, default=None, help="Request body as JSON string")
@click.option("--body-file", "body_file", type=click.Path(exists=True), default=None, help="Read request body from JSON file")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_update_noise_definition(ctx, body_data, body_file, cmd_fmt, cmd_query):
    """POST /api/flows/v1/noisedefinition"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/noisedefinition"
    params = None
    body = None
    if body_file:
        import json as _json
        with open(body_file) as f:
            body = _json.load(f)
    elif body_data:
        import json as _json
        body = _json.loads(body_data)
    client = ctx.ensure_client()
    try:
        result = client.post(endpoint, data=body, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-unique-values")
@click.option("--parameter", "parameter", type=str, required=True, help="parameter")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_unique_values(ctx, parameter, cmd_fmt, cmd_query):
    """Get unique values"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/nflowsearch/api/v1/unique-values"
    params = {}
    if parameter is not None:
        params["parameter"] = parameter
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-all")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_all(ctx, cmd_fmt, cmd_query):
    """GET /api/flows/v1/refresh-info"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/refresh-info"
    params = None
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-available-ports")
@click.option("--search", "search", type=str, default=None, help="Search text to filter by name, port, or protocol")
@click.option("--page", "page", type=str, default=0, help="Page number (0-based)")
@click.option("--size", "size", type=str, default=100, help="Page size")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_available_ports(ctx, search, page, size, cmd_fmt, cmd_query):
    """Get all available ports and their names"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/port-information/ports"
    params = {}
    if search is not None:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if size is not None:
        params["size"] = size
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("search-noise-definitions")
@click.option("--query-param", "query", type=str, default=None, help="[sends query] query")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_search_noise_definitions(ctx, query, cmd_fmt, cmd_query):
    """GET /api/flows/v1/noisedefinition/search"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/noisedefinition/search"
    params = {}
    if query is not None:
        params["query"] = query
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-latest-data-backward-compatible")
@click.argument("ip")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_latest_data_backward_compatible(ctx, ip, cmd_fmt, cmd_query):
    """Get latest device data - backward compatible"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/device-state-cache/latest/{ip}"
    params = None
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-latest-data")
@click.argument("ip")
@click.argument("distributionzoneid")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_latest_data(ctx, ip, distributionzoneid, cmd_fmt, cmd_query):
    """Get latest device data"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/device-state-cache/latest/{ip}/{distributionzoneid}"
    params = None
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-device-data-history")
@click.argument("ip")
@click.option("--distributionZoneId", "distributionZoneId", type=str, default=None, help="Distribution Zone ID")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_device_data_history(ctx, ip, distributionZoneId, cmd_fmt, cmd_query):
    """Get complete device data history"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/device-state-cache/history/{ip}"
    params = {}
    if distributionZoneId is not None:
        params["distributionZoneId"] = distributionZoneId
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-device-data-in-time-range")
@click.argument("ip")
@click.option("--distributionZoneId", "distributionZoneId", type=str, default=None, help="Distribution Zone ID")
@click.option("--from", "from_param", type=str, required=True, help="Start time (inclusive)")
@click.option("--to", "to", type=str, required=True, help="End time (inclusive)")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_device_data_in_time_range(ctx, ip, distributionZoneId, from_param, to, cmd_fmt, cmd_query):
    """Get device data history in time range"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/device-state-cache/history/{ip}/range"
    params = {}
    if distributionZoneId is not None:
        params["distributionZoneId"] = distributionZoneId
    if from_param is not None:
        params["from"] = from_param
    if to is not None:
        params["to"] = to
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("get-floor-data")
@click.argument("ip")
@click.option("--distributionZoneId", "distributionZoneId", type=str, default=None, help="Distribution Zone ID")
@click.option("--timestamp", "timestamp", type=str, required=True, help="Reference timestamp (inclusive)")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_get_floor_data(ctx, ip, distributionZoneId, timestamp, cmd_fmt, cmd_query):
    """Get device data at or before timestamp"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/device-state-cache/floor/{ip}"
    params = {}
    if distributionZoneId is not None:
        params["distributionZoneId"] = distributionZoneId
    if timestamp is not None:
        params["timestamp"] = timestamp
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("dump-latest")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_dump_latest(ctx, cmd_fmt, cmd_query):
    """Get latest data for all devices"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/device-state-cache/dump/latest"
    params = None
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)

@group.command("dump-all")
@click.option("--format", "-f", "cmd_fmt", type=click.Choice(["json", "table", "yaml", "csv"]), default=None, help="Output format override", hidden=True)
@click.option("--query", "-q", "cmd_query", type=str, default=None, help="JMESPath query override", hidden=True)
@pass_context
def cmd_dump_all(ctx, cmd_fmt, cmd_query):
    """Get complete history for all devices"""
    if cmd_fmt:
        ctx.format = cmd_fmt
    if cmd_query:
        ctx.query = cmd_query
    endpoint = f"/api/flows/v1/device-state-cache/dump/all"
    params = None
    client = ctx.ensure_client()
    try:
        result = client.get(endpoint, params=params)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    render(result, ctx.format, ctx.query)
