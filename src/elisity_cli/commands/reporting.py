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


# ---------------------------------------------------------------------------
# Additional metric queries discovered via GraphQL introspection of
# /api/reporting/v1/data. The reporting endpoint exposes 4 metric domains
# (policyMetrics, identityGraphMetrics, trafficVectorsMetrics, topologyMetrics)
# — these commands wrap the most operationally useful queries for tenant
# summary, posture scoring, and per-site dashboards.
# ---------------------------------------------------------------------------


_AGGREGATE_SCORE_QUERY = """query AggregateEnforcementScore($dt: [DateTime!]!, $site: [Site!]) {
  policyMetrics {
    aggregatePolicyEnforcementScore(dateTime: $dt, site: $site) {
      ... on FloatMetricValue {
        value
        dateTime
        __typename
      }
    }
  }
}"""

_POLICY_SET_SCORE_QUERY = """query PolicySetEnforcementScore($id: UUID!, $dt: [DateTime!]!, $site: [Site!]) {
  policyMetrics {
    policySetEnforcementScore(policySetId: $id, dateTime: $dt, site: $site) {
      ... on FloatMetricValue {
        value
        dateTime
        __typename
      }
    }
  }
}"""

_DEVICE_COUNT_QUERY = """query DeviceCount($dt: DateTimeSelectionInput!, $online: Boolean, $site: [Site!]) {
  identityGraphMetrics {
    devices {
      count(dateTime: $dt, online: $online, site: $site) {
        dateTime
        online
        value
      }
    }
  }
}"""

_SITE_KPIS_QUERY = """query SiteKPIs($dt: DateTime!, $site: [Site!]) {
  topologyMetrics {
    siteKPIs(dateTime: $dt, site: $site) {
      dateTime
      siteName
      onlineDevices
      virtualEdgeNodes
      localPolicyGroups
      simulatedPolicies
      activatedPolicies
      policyEnforcementScore
    }
  }
}"""


@group.command("get-aggregate-enforcement-score")
@click.option(
    "--snapshot",
    "snapshots",
    multiple=True,
    default=None,
    help="ISO-8601 snapshot time (top-of-hour UTC). Repeatable. Default: previous full hour.",
)
@click.option(
    "--site",
    "sites",
    multiple=True,
    default=None,
    help="Filter to one or more site names. Repeatable.",
)
@pass_context
def cmd_aggregate_score(ctx, snapshots, sites):
    """Tenant-wide Zero Trust enforcement score (single number per snapshot).

    This is the actual "Zero Trust score" headline number that the CCC UI
    shows. Returns a list of FloatMetricValue, one per requested snapshot
    (most users want a single recent snapshot — that's the default).

    Examples:
      elisity reporting get-aggregate-enforcement-score
      elisity reporting get-aggregate-enforcement-score --snapshot 2026-05-22T11:00:00.000Z
      elisity reporting get-aggregate-enforcement-score --site Boston --site CORK
    """
    snaps = list(snapshots) if snapshots else [_default_snapshot()]
    variables = {"dt": snaps}
    if sites:
        variables["site"] = _lookup_sites(ctx, list(sites))

    result = _post_graphql(ctx, "AggregateEnforcementScore", variables, _AGGREGATE_SCORE_QUERY)
    _check_errors(result)
    data = (
        result.get("data", {}).get("policyMetrics", {}).get("aggregatePolicyEnforcementScore")
        or []
    )
    render(data, ctx.format, ctx.query)


@group.command("get-policy-set-enforcement-score")
@click.argument("policy_set_id")
@click.option(
    "--snapshot",
    "snapshots",
    multiple=True,
    default=None,
    help="ISO-8601 snapshot time (top-of-hour UTC). Repeatable. Default: previous full hour.",
)
@click.option(
    "--site",
    "sites",
    multiple=True,
    default=None,
    help="Filter to one or more site names. Repeatable.",
)
@pass_context
def cmd_policy_set_score(ctx, policy_set_id, snapshots, sites):
    """Per-policy-set enforcement score (GraphQL — works where the REST
    `policy get-enforcement-score` returns 404).

    Examples:
      # Get every policy set ID
      elisity policy get-all-as-nd-json -q '[].{id: id, name: name}'

      # Pull score for one
      elisity reporting get-policy-set-enforcement-score <POLICY_SET_ID>

      # Fan out across all policy sets
      for id in $(elisity policy get-all-as-nd-json -q '[].id' -f csv | tail -n +2); do
        echo "=== $id ==="
        elisity reporting get-policy-set-enforcement-score "$id"
      done
    """
    snaps = list(snapshots) if snapshots else [_default_snapshot()]
    variables = {"id": policy_set_id, "dt": snaps}
    if sites:
        variables["site"] = _lookup_sites(ctx, list(sites))

    result = _post_graphql(ctx, "PolicySetEnforcementScore", variables, _POLICY_SET_SCORE_QUERY)
    _check_errors(result)
    data = (
        result.get("data", {}).get("policyMetrics", {}).get("policySetEnforcementScore")
        or []
    )
    render(data, ctx.format, ctx.query)


@group.command("get-device-count")
@click.option(
    "--snapshot",
    "snapshots",
    multiple=True,
    default=None,
    help="ISO-8601 snapshot time (top-of-hour UTC). Repeatable. Default: previous full hour.",
)
@click.option(
    "--online",
    type=click.Choice(["true", "false"]),
    default=None,
    help="Filter to online=true or online=false only. Omit to get both as separate rows.",
)
@click.option(
    "--site",
    "sites",
    multiple=True,
    default=None,
    help="Filter to one or more site names. Repeatable.",
)
@pass_context
def cmd_device_count(ctx, snapshots, online, sites):
    """Device count from CCC's metrics snapshot — broken out by online state.

    Returns one row per (snapshot, online-state). With no --online filter,
    you get two rows per snapshot (online=true, online=false) — useful for
    tenant-wide online/offline counts in a single call without paginating
    through devices/view.

    Examples:
      # Online + offline counts for the latest snapshot
      elisity reporting get-device-count

      # Just online devices
      elisity reporting get-device-count --online true

      # Per site
      elisity reporting get-device-count --site Boston
      elisity reporting get-device-count --site Boston --site CORK
    """
    snaps = list(snapshots) if snapshots else [_default_snapshot()]
    variables = {"dt": {"dateTimes": snaps}}
    if online is not None:
        variables["online"] = (online == "true")
    if sites:
        variables["site"] = _lookup_sites(ctx, list(sites))

    result = _post_graphql(ctx, "DeviceCount", variables, _DEVICE_COUNT_QUERY)
    _check_errors(result)
    data = (
        result.get("data", {}).get("identityGraphMetrics", {}).get("devices", {}).get("count")
        or []
    )
    render(data, ctx.format, ctx.query)


@group.command("get-site-kpis")
@click.option(
    "--snapshot",
    "snapshot",
    default=None,
    help="ISO-8601 snapshot time (top-of-hour UTC). Default: previous full hour.",
)
@click.option(
    "--site",
    "sites",
    multiple=True,
    default=None,
    help="Filter to one or more site names. Repeatable.",
)
@pass_context
def cmd_site_kpis(ctx, snapshot, sites):
    """Per-site KPI dashboard — devices, VENs, policy counts, enforcement score.

    Returns one row per site with: onlineDevices, virtualEdgeNodes,
    localPolicyGroups, simulatedPolicies, activatedPolicies,
    policyEnforcementScore. This is the data behind CCC's per-site
    dashboard cards — the single best query for a tenant summary.

    Examples:
      elisity -f table reporting get-site-kpis
      elisity reporting get-site-kpis --site Boston
    """
    snap = snapshot or _default_snapshot()
    variables = {"dt": snap}
    if sites:
        variables["site"] = _lookup_sites(ctx, list(sites))

    result = _post_graphql(ctx, "SiteKPIs", variables, _SITE_KPIS_QUERY)
    _check_errors(result)
    data = result.get("data", {}).get("topologyMetrics", {}).get("siteKPIs") or []
    render(data, ctx.format, ctx.query)


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
