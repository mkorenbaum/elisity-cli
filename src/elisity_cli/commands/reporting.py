"""Reporting / GraphQL — Zero Trust scores, threat vectors, risk attribution.

The CCC reporting API at ``POST /api/reporting/v1/data`` is a GraphQL endpoint.
It is **not** in the OpenAPI spec — so unlike the other command groups, these
commands are hand-coded rather than generated. They wrap the GraphQL queries
the CCC dashboard UI uses for:

- Zero Trust page — per-policy-group device & policy coverage scores, restricted
  vs total flows, L4 port exposure, MITRE-style threat vectors.
- Malware lateral movement page — same threat vector data viewed by technique.
- Per-device risk attribution — Zero Trust metrics with the device MAC included.

Snapshots are taken at top-of-hour UTC; not every hour has data. Use
``elisity reporting list-snapshots`` to find available snapshot times.
"""

import json as _json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import click

from elisity_cli.context import pass_context
from elisity_cli.output import render

GRAPHQL_PATH = "/api/reporting/v1/data"

# Exact query the CCC dashboard sends. Preserved verbatim so the server-side
# variable-validation step accepts it (@include directives reference the
# `includeMac` and `includeL4Detail` variables — dropping them produces a
# `ValidationError: Unused variable` response).
_ZERO_TRUST_QUERY = """query GetRiskAttributionScores($snapshotDateTimes: [DateTime!]!, $site: [Site!], $includeMac: Boolean!, $includeL4Detail: Boolean = false, $macAddress: [String!], $filters: ZeroTrustFilters) {
  policyMetrics {
    zeroTrustMetrics(
      dateTime: $snapshotDateTimes
      site: $site
      macAddress: $macAddress
      filters: $filters
    ) {
      dateTime
      deviceId @include(if: $includeMac)
      macAddress @include(if: $includeMac)
      siteId
      siteName
      policyGroupId
      policyGroupName
      policySetId
      policySetName
      distributionZoneId
      distributionZoneName
      deviceCount
      totalFlows
      restrictedFlows
      avgDeviceCoverage
      avgPolicyCoverage
      l4Metrics {
        avgAllowedPorts
        avgAllowedTcp @include(if: $includeL4Detail)
        avgAllowedUdp @include(if: $includeL4Detail)
        avgIcmp @include(if: $includeL4Detail)
        __typename
      }
      threatVectorMetrics {
        ...ThreatVectorMetricsFields
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment PortExposureMetricFields on PortExposureMetricValue {
  port
  value
  __typename
}

fragment ThreatVectorMetricFields on ThreatVectorMetricValue {
  technique
  value
  __typename
}

fragment ThreatVectorMetricsFields on ThreatVectorMetrics {
  portExposure {
    ...PortExposureMetricFields
    __typename
  }
  threatVectors {
    ...ThreatVectorMetricFields
    __typename
  }
  __typename
}"""


@click.group("reporting")
def group():
    """CCC reporting (GraphQL) — Zero Trust scores, threat vectors, risk attribution.

    These commands query the /api/reporting/v1/data GraphQL endpoint that powers
    the CCC dashboard Zero Trust page, the malware lateral movement page, and
    per-device risk views. The endpoint is not in the OpenAPI spec, so these
    commands are hand-coded.
    """


def _post_graphql(ctx, operation_name: str, variables: dict, query: str):
    client = ctx.ensure_client()
    body = {
        "operationName": operation_name,
        "variables": variables,
        "query": query,
    }
    return client.post(GRAPHQL_PATH, data=body)


def _default_snapshot() -> str:
    """Top-of-hour timestamp for the previous full hour (UTC)."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _check_errors(result) -> None:
    """Raise on GraphQL-level errors."""
    if isinstance(result, dict) and result.get("errors"):
        click.echo("GraphQL errors:", err=True)
        for e in result["errors"]:
            click.echo(f"  - {e.get('message', e)}", err=True)
        raise SystemExit(1)


def _lookup_sites(ctx, site_names: List[str]) -> List[dict]:
    """Resolve site names to the Site input objects the GraphQL endpoint requires.

    The reporting endpoint's ``Site`` input type is a Map with three non-null
    fields: ``id`` (UUID), ``numericId`` (Long), ``label`` (String). Users
    pass site names on the CLI; we look them up against
    ``GET /api/topology/v2/sites`` and build the input objects.
    """
    client = ctx.ensure_client()
    sites = client.get("/api/topology/v2/sites") or []
    if isinstance(sites, dict):
        sites = sites.get("content") or sites.get("items") or []
    by_label = {s.get("label"): s for s in sites if isinstance(s, dict)}

    out: List[dict] = []
    missing: List[str] = []
    for name in site_names:
        s = by_label.get(name)
        if not s:
            missing.append(name)
            continue
        out.append(
            {
                "id": s.get("id"),
                "numericId": int(s.get("numericId")) if s.get("numericId") is not None else 0,
                "label": s.get("label"),
            }
        )
    if missing:
        available = sorted(by_label.keys())
        click.echo(
            f"Unknown site name(s): {missing}. Available: {available}", err=True
        )
        raise SystemExit(1)
    return out


@group.command("get-zero-trust-metrics")
@click.option(
    "--snapshot",
    "snapshots",
    multiple=True,
    default=None,
    help="ISO-8601 snapshot time (top-of-hour UTC, e.g. 2026-05-22T11:00:00.000Z). "
    "Repeatable. Default: previous full hour.",
)
@click.option(
    "--site",
    "sites",
    multiple=True,
    default=None,
    help="Filter to one or more site names (server-side filter). Repeatable. "
    "Use the site label as shown by `elisity topology get-all-sites`. "
    "Alternative: omit and post-filter with `-q \"[?siteName=='Boston']\"`.",
)
@click.option(
    "--include-mac",
    is_flag=True,
    default=False,
    help="Include per-device deviceId + macAddress in results.",
)
@click.option(
    "--include-l4-detail",
    is_flag=True,
    default=False,
    help="Include TCP/UDP/ICMP breakdown in l4Metrics.",
)
@pass_context
def cmd_zero_trust(
    ctx,
    snapshots,
    sites,
    include_mac,
    include_l4_detail,
):
    """Get Zero Trust scores (the metrics from CCC's Zero Trust page).

    Returns one row per (site, policy group, snapshot) with deviceCount,
    totalFlows, restrictedFlows, avgDeviceCoverage (Zero Trust device score),
    avgPolicyCoverage (Zero Trust policy score), plus L4 port exposure and
    threat-vector metrics (MITRE techniques + port exposure scores).

    Examples (note: -q / -f are top-level flags — place them BEFORE the
    group name):

      elisity reporting get-zero-trust-metrics
      elisity reporting get-zero-trust-metrics --snapshot 2026-05-22T11:00:00.000Z
      elisity reporting get-zero-trust-metrics --site Boston --site CORK
      elisity reporting get-zero-trust-metrics --include-l4-detail

      # Per-policy-group coverage scores
      elisity -q '[].{site: siteName, pg: policyGroupName, devices: deviceCount, devCov: avgDeviceCoverage, polCov: avgPolicyCoverage}' \\
        -f table reporting get-zero-trust-metrics

      # Tenant total device count covered by the snapshot
      elisity -q 'sum([].deviceCount)' reporting get-zero-trust-metrics

      # Device-weighted average coverage via jq (JMESPath lacks generic
      # arithmetic; null-safe with `// 0`)
      elisity reporting get-zero-trust-metrics | jq '
        (map((.avgDeviceCoverage // 0) * .deviceCount) | add) /
        (map(.deviceCount) | add)
      '
    """
    variables = {
        "snapshotDateTimes": list(snapshots) if snapshots else [_default_snapshot()],
        "includeMac": include_mac,
        "includeL4Detail": include_l4_detail,
    }
    if sites:
        variables["site"] = _lookup_sites(ctx, list(sites))

    result = _post_graphql(ctx, "GetRiskAttributionScores", variables, _ZERO_TRUST_QUERY)
    _check_errors(result)

    metrics = (
        result.get("data", {}).get("policyMetrics", {}).get("zeroTrustMetrics") or []
    )
    render(metrics, ctx.format, ctx.query)


@group.command("list-snapshots")
@click.option(
    "--hours",
    type=int,
    default=72,
    help="How many hours back to probe (default 72).",
)
@pass_context
def cmd_list_snapshots(ctx, hours):
    """Discover which top-of-hour snapshots have data on this tenant.

    /api/reporting/v1/data serves point-in-time snapshots. Not every hour has
    data — generation cadence varies by tenant. This walks back <hours> hours
    and returns the (snapshot, row count) pairs that have data.

    Example:
      elisity reporting list-snapshots
      elisity reporting list-snapshots --hours 168     # last week
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    available = []
    for h in range(hours):
        snap = (now - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        result = _post_graphql(
            ctx,
            "GetRiskAttributionScores",
            {
                "snapshotDateTimes": [snap],
                "includeMac": False,
                "includeL4Detail": False,
            },
            _ZERO_TRUST_QUERY,
        )
        # don't raise on per-snapshot errors — just skip the row
        if isinstance(result, dict) and result.get("errors"):
            continue
        rows = (
            result.get("data", {}).get("policyMetrics", {}).get("zeroTrustMetrics")
            or []
        )
        if rows:
            available.append({"snapshot": snap, "rows": len(rows)})
    render(available, ctx.format, ctx.query)


@group.command("query")
@click.option(
    "--body-file",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="JSON file containing {operationName, variables, query}.",
)
@pass_context
def cmd_raw_query(ctx, body_file):
    """Execute a raw GraphQL request from a JSON payload file.

    Escape hatch for ad-hoc GraphQL queries other than the predefined ones.
    The file must contain a complete GraphQL request body:

      {
        "operationName": "<name>",
        "variables": { ... },
        "query": "<gql string>"
      }

    Example:
      elisity reporting query --body-file ./my-query.json
    """
    with open(body_file) as f:
        payload = _json.load(f)

    client = ctx.ensure_client()
    result = client.post(GRAPHQL_PATH, data=payload)
    render(result, ctx.format, ctx.query)
