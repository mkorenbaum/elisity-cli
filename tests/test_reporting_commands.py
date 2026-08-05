"""
Behavioural tests for the hand-coded `reporting` commands.

`tests/test_reporting_graphql_schema.py` proves the queries agree with the CCC
26.7 schema. These tests prove the commands still *behave* correctly around
them: what goes on the wire, and what comes back out.

Two things are load-bearing here:

1. **The 26.7 filter move.** The per-device selectors now travel inside the
   `ZeroTrustFilters` input object. A test that only checks the query string
   would not notice the CLI silently dropping the selector it was asked for, so
   the request body itself is asserted.

2. **`diagnose-low-score` must not conflate no-policy with simulation.** That
   command exists specifically to stop an agent recommending "activate the
   simulation policies" for a group that has no policy at all. Fixing the query
   underneath it must not quietly break that distinction, so every diagnosis
   label is pinned against a 26.7-shaped response.

The GraphQL responses below are shaped as the live 26.7 endpoint returns them
(`data.policyMetrics.zeroTrustMetrics[]`). No live tenant is contacted.
"""

import json

import pytest
from click.testing import CliRunner

from elisity_cli.commands import reporting
from elisity_cli.context import CliContext
from elisity_cli.main import cli

GRAPHQL_PATH = "/api/reporting/v1/data"
POLICIES_PATH = "/api/policy/v1/policy-sets/policies"


class FakeClient:
    """Records every call and replays canned CCC responses."""

    def __init__(self, graphql_response=None, policies=None, sites=None):
        self.graphql_response = graphql_response or {"data": {"policyMetrics": {"zeroTrustMetrics": []}}}
        self.policies = policies or []
        self.sites = sites or []
        self.posts = []
        self.gets = []

    def post(self, endpoint, data=None, params=None):
        self.posts.append({"endpoint": endpoint, "body": data})
        return self.graphql_response

    def get(self, endpoint, params=None):
        self.gets.append(endpoint)
        return self.sites

    def get_ndjson(self, endpoint, params=None):
        self.gets.append(endpoint)
        return self.policies


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake(monkeypatch):
    """Install a FakeClient and hand it back for assertions."""
    holder = {}

    def install(**kwargs):
        client = FakeClient(**kwargs)
        monkeypatch.setattr(CliContext, "ensure_client", lambda self: client)
        holder["client"] = client
        return client

    install.get = lambda: holder["client"]  # noqa: E731
    return install


def _zt_row(**overrides):
    """One zeroTrustMetrics row in the 26.7 response shape."""
    row = {
        "dateTime": "2026-08-05T12:00:00.000Z",
        "siteId": "site-1",
        "siteName": "Boston",
        "policyGroupId": "pg-none",
        "policyGroupName": "Unassigned",
        "policySetId": "ps-1",
        "policySetName": "Default",
        "distributionZoneId": "dz-1",
        "distributionZoneName": "DZ1",
        "deviceCount": 10,
        "totalFlows": 100,
        "restrictedFlows": 0,
        "avgDeviceCoverage": 0.0,
        "avgPolicyCoverage": 0.0,
        "l4Metrics": {"avgAllowedPorts": 12.0},
        "threatVectorMetrics": {"portExposure": [], "threatVectors": []},
    }
    row.update(overrides)
    return row


def _zt_response(rows):
    return {"data": {"policyMetrics": {"zeroTrustMetrics": rows}}}


def _policy(pg_id, mode, disabled=False):
    return {"srcId": pg_id, "dstId": None, "monitorMode": mode, "disabled": disabled}


# --------------------------------------------------------------------------
# get-zero-trust-metrics — the 26.7 filter move, asserted on the wire
# --------------------------------------------------------------------------


class TestZeroTrustRequestShape:
    def test_mac_selector_is_sent_inside_filters(self, runner, fake):
        client = fake(graphql_response=_zt_response([_zt_row()]))
        result = runner.invoke(
            cli, ["reporting", "get-zero-trust-metrics", "--mac-address", "00:11:22:33:44:55"]
        )
        assert result.exit_code == 0, result.output

        body = client.posts[0]["body"]
        assert client.posts[0]["endpoint"] == GRAPHQL_PATH
        assert body["variables"]["filters"] == {"macAddress": ["00:11:22:33:44:55"]}
        # The 26.7 breakage was a top-level `macAddress`. It must be gone from
        # both the variables and the query text.
        assert "macAddress" not in body["variables"]
        assert "macAddress: $macAddress" not in body["query"]
        assert "filters: $filters" in body["query"]

    def test_mac_selector_implies_include_mac(self, runner, fake):
        client = fake(graphql_response=_zt_response([_zt_row()]))
        runner.invoke(
            cli, ["reporting", "get-zero-trust-metrics", "--mac-address", "aa:bb:cc:dd:ee:ff"]
        )
        assert client.posts[0]["body"]["variables"]["includeMac"] is True

    def test_repeatable_mac_selector(self, runner, fake):
        client = fake(graphql_response=_zt_response([]))
        runner.invoke(
            cli,
            ["reporting", "get-zero-trust-metrics", "--mac-address", "a", "--mac-address", "b"],
        )
        assert client.posts[0]["body"]["variables"]["filters"] == {"macAddress": ["a", "b"]}

    def test_filters_omitted_when_no_selector_given(self, runner, fake):
        """An empty filters object is not the same as no filter — omit it."""
        client = fake(graphql_response=_zt_response([_zt_row()]))
        result = runner.invoke(cli, ["reporting", "get-zero-trust-metrics"])
        assert result.exit_code == 0, result.output
        assert "filters" not in client.posts[0]["body"]["variables"]

    def test_default_snapshot_is_sent(self, runner, fake):
        client = fake(graphql_response=_zt_response([]))
        runner.invoke(cli, ["reporting", "get-zero-trust-metrics"])
        snapshots = client.posts[0]["body"]["variables"]["snapshotDateTimes"]
        assert len(snapshots) == 1 and snapshots[0].endswith("Z")

    def test_rows_are_rendered(self, runner, fake):
        fake(graphql_response=_zt_response([_zt_row(siteName="CORK")]))
        result = runner.invoke(cli, ["reporting", "get-zero-trust-metrics"])
        assert json.loads(result.output)[0]["siteName"] == "CORK"


class TestGraphQLErrorsSurface:
    """A validation error must fail loudly, not render as an empty result.

    This is how the 26.7 breakage looked to a user: the CLI was returning the
    server's `Validation error (UnknownArgument@…)`. If that ever regresses to a
    silent empty list, a broken command looks like an empty tenant.
    """

    def test_validation_error_exits_nonzero(self, runner, fake):
        fake(
            graphql_response={
                "errors": [
                    {
                        "message": "Validation error (UnknownArgument@[policyMetrics/zeroTrustMetrics]): "
                        "Unknown field argument 'macAddress'"
                    }
                ]
            }
        )
        result = runner.invoke(cli, ["reporting", "get-zero-trust-metrics"])
        assert result.exit_code == 1
        assert "UnknownArgument" in result.output


# --------------------------------------------------------------------------
# diagnose-low-score — the no-policy vs simulation distinction
# --------------------------------------------------------------------------


class TestDiagnoseLowScore:
    """Every diagnosis label pinned against a 26.7-shaped response."""

    @pytest.fixture
    def diagnosed(self, runner, fake):
        rows = [
            _zt_row(policyGroupId="pg-none", policyGroupName="NoPolicy"),
            _zt_row(policyGroupId="pg-sim", policyGroupName="SimOnly"),
            _zt_row(policyGroupId="pg-ext", policyGroupName="External"),
            _zt_row(policyGroupId="pg-mixed", policyGroupName="Mixed"),
            _zt_row(policyGroupId="pg-active", policyGroupName="ActiveLow"),
        ]
        policies = [
            _policy("pg-sim", "MONITOR_ONLY"),
            _policy("pg-ext", "MONITOR_EXTERNAL"),
            _policy("pg-mixed", "MONITOR_AND_ENFORCE"),
            _policy("pg-mixed", "MONITOR_ONLY"),
            _policy("pg-active", "MONITOR_AND_ENFORCE"),
            # A disabled policy must not count — otherwise a group with only
            # disabled policies reads as ACTIVE_LOW_COVERAGE instead of NO_POLICY.
            _policy("pg-none", "MONITOR_AND_ENFORCE", disabled=True),
        ]
        fake(graphql_response=_zt_response(rows), policies=policies)
        result = runner.invoke(cli, ["reporting", "diagnose-low-score"])
        assert result.exit_code == 0, result.output
        return {row["policyGroupName"]: row for row in json.loads(result.output)}

    @pytest.mark.parametrize(
        "group,diagnosis",
        [
            ("NoPolicy", "NO_POLICY"),
            ("SimOnly", "SIMULATION_ONLY"),
            ("External", "EXTERNAL_ONLY"),
            ("Mixed", "MIXED_LOW_COVERAGE"),
            ("ActiveLow", "ACTIVE_LOW_COVERAGE"),
        ],
    )
    def test_diagnosis_label(self, diagnosed, group, diagnosis):
        assert diagnosed[group]["diagnosis"] == diagnosis

    def test_no_policy_is_not_told_to_activate_simulations(self, diagnosed):
        """The whole point of the command: NO_POLICY != SIMULATION_ONLY."""
        remediation = diagnosed["NoPolicy"]["remediation"]
        assert "no policy" in remediation.lower()
        assert "Do NOT recommend `change-status`" in remediation

    def test_simulation_only_is_told_to_activate(self, diagnosed):
        assert "change-status" in diagnosed["SimOnly"]["remediation"]

    def test_policy_counts_are_reported(self, diagnosed):
        assert diagnosed["Mixed"]["policiesActive"] == 1
        assert diagnosed["Mixed"]["policiesSimulation"] == 1
        assert diagnosed["NoPolicy"]["policiesActive"] == 0

    def test_uses_the_filters_shaped_query(self, runner, fake):
        """diagnose-low-score composes the same query — it must carry the fix."""
        client = fake(graphql_response=_zt_response([]), policies=[])
        runner.invoke(cli, ["reporting", "diagnose-low-score"])
        body = client.posts[0]["body"]
        assert "filters: $filters" in body["query"]
        assert "$macAddress" not in body["query"]

    def test_threshold_filters_healthy_groups(self, runner, fake):
        rows = [
            _zt_row(policyGroupId="pg-good", policyGroupName="Healthy",
                    avgDeviceCoverage=99.0, avgPolicyCoverage=99.0),
            _zt_row(policyGroupId="pg-bad", policyGroupName="Low",
                    avgDeviceCoverage=10.0, avgPolicyCoverage=10.0),
        ]
        fake(graphql_response=_zt_response(rows), policies=[])
        result = runner.invoke(cli, ["reporting", "diagnose-low-score", "--threshold", "50"])
        names = {row["policyGroupName"] for row in json.loads(result.output)}
        assert names == {"Low"}


class TestListSnapshots:
    """list-snapshots shares the zero-trust query, so it broke with it.

    It also swallows per-snapshot errors by design (not every hour has data) —
    which is exactly why the 26.7 validation error was invisible here: every
    probe errored and the command returned an empty list rather than failing.
    """

    def test_returns_snapshots_that_have_rows(self, runner, fake):
        fake(graphql_response=_zt_response([_zt_row(), _zt_row()]))
        result = runner.invoke(cli, ["reporting", "list-snapshots", "--hours", "2"])
        assert result.exit_code == 0, result.output
        snapshots = json.loads(result.output)
        assert len(snapshots) == 2
        assert snapshots[0]["rows"] == 2

    def test_uses_the_filters_shaped_query(self, runner, fake):
        client = fake(graphql_response=_zt_response([]))
        runner.invoke(cli, ["reporting", "list-snapshots", "--hours", "1"])
        assert "filters: $filters" in client.posts[0]["body"]["query"]

    def test_errors_are_skipped_not_raised(self, runner, fake):
        fake(graphql_response={"errors": [{"message": "no data for snapshot"}]})
        result = runner.invoke(cli, ["reporting", "list-snapshots", "--hours", "2"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []


class TestRemovedCommands:
    """CCC 26.7 removed the fields these commands queried."""

    @pytest.mark.parametrize(
        "command", ["get-policy-count-needed", "get-policy-set-enforcement-score"]
    )
    def test_command_is_gone(self, runner, command):
        result = runner.invoke(cli, ["reporting", command])
        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_surviving_policy_metric_commands_still_work(self, runner, fake):
        """The neighbouring policyMetrics commands were not collateral damage."""
        fake(graphql_response={"data": {"policyMetrics": {"count": [{"value": 42}]}}})
        result = runner.invoke(cli, ["reporting", "get-policy-count"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)[0]["value"] == 42
