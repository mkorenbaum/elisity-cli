"""
Schema drift guard for the hand-coded `reporting` GraphQL queries.

Why this file exists
--------------------
Every other command group is generated from the CCC OpenAPI spec, so a spec bump
regenerates it and the spec diff makes the change reviewable. The `reporting`
group is not: the CCC reporting API is GraphQL and is deliberately absent from
the OpenAPI spec, so these queries are hand-written and **do not move when the
generator runs**.

That is a blind spot no other check in this repo can see. When CCC 26.7 changed
the GraphQL schema underneath `reporting`, the suite stayed green, the spec diff
stayed clean, the generated code stayed correct — and three commands were dead on
arrival against a live 26.7 tenant:

    Validation error (UnknownArgument@[policyMetrics/zeroTrustMetrics]):
        Unknown field argument 'macAddress'
    Validation error (FieldUndefined@[policyMetrics/countNeeded])
    Validation error (FieldUndefined@[policyMetrics/policySetEnforcementScore])

These tests validate every query literal in `commands/reporting.py` against a
staged introspection of the live 26.7 schema, so the next schema drift fails here
instead of shipping.

Scope, stated honestly: this is a STATIC check. It proves the queries are
well-formed against the staged schema. It does not execute anything against a
live tenant, and it can only check types we have staged introspection for —
`PolicyMetrics` today. `TestCoverageIsHonest` asserts the unverified surface is
exactly the known list, so widening (or silently losing) coverage is itself a
test failure.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.gql_schema_check import (  # noqa: E402
    DEFAULT_SCHEMA,
    KNOWN_UNVERIFIED_ROOTS,
    ROOT_FIELD_TYPES,
    check_module,
    extract_queries,
    load_schema,
    validate_document,
)

from elisity_cli.commands import reporting  # noqa: E402

# The three query shapes CCC 26.3 accepted and 26.7 rejects. Used to prove this
# suite actually fails on drift — a schema check that passes on a known-bad
# query is worth nothing.
_QUERY_263_TOP_LEVEL_MAC = """query GetRiskAttributionScores($snapshotDateTimes: [DateTime!]!, $macAddress: [String!]) {
  policyMetrics {
    zeroTrustMetrics(dateTime: $snapshotDateTimes, macAddress: $macAddress) {
      deviceCount
    }
  }
}"""

_QUERY_263_COUNT_NEEDED = """query PolicyCountNeeded($dt: [DateTime!]!) {
  policyMetrics {
    countNeeded(dateTime: $dt) {
      value
    }
  }
}"""

_QUERY_263_POLICY_SET_SCORE = """query PolicySetEnforcementScore($id: UUID!, $dt: [DateTime!]!) {
  policyMetrics {
    policySetEnforcementScore(policySetId: $id, dateTime: $dt) {
      ... on FloatMetricValue {
        value
      }
    }
  }
}"""


@pytest.fixture(scope="module")
def schema():
    return load_schema(DEFAULT_SCHEMA)


@pytest.fixture(scope="module")
def report():
    return check_module()


# --------------------------------------------------------------------------
# 1. The guard itself — every shipped query validates against 26.7
# --------------------------------------------------------------------------


class TestQueriesMatchStagedSchema:
    def test_no_schema_errors(self, report):
        """No unknown argument, no undefined field, in any reporting query."""
        failures = [
            f"{name}: {error['kind']}@[{error['path']}] {error['message']}"
            for name, result in report["queries"].items()
            for error in result["errors"]
        ]
        assert not failures, (
            "reporting GraphQL queries disagree with the staged CCC schema "
            f"({report['schema']}):\n  " + "\n  ".join(failures)
        )

    def test_zero_trust_selectors_live_in_filters(self):
        """26.7 moved the per-device selectors into the `filters` input object.

        Asserted on the query text as well as via the schema check: this is the
        exact regression that shipped, and it must fail loudly if reintroduced.
        """
        query = reporting._ZERO_TRUST_QUERY
        assert "filters: $filters" in query
        assert "macAddress: $macAddress" not in query
        assert "$macAddress" not in query, (
            "an orphaned variable declaration is itself a server-side "
            "'Unused variable' ValidationError"
        )

    def test_filters_builder_rejects_unknown_keys(self):
        """A selector that is not a ZeroTrustFilters key fails here, not on the wire."""
        with pytest.raises(ValueError, match="not ZeroTrustFilters keys"):
            reporting._zero_trust_filters(notAFilterKey=["x"])

    def test_filters_builder_omits_empty_selectors(self):
        assert reporting._zero_trust_filters(macAddress=()) is None
        assert reporting._zero_trust_filters(macAddress=("00:11:22:33:44:55",)) == {
            "macAddress": ["00:11:22:33:44:55"]
        }

    def test_filter_keys_match_the_267_input_object(self):
        assert set(reporting._ZERO_TRUST_FILTER_KEYS) == {
            "ipAddress",
            "macAddress",
            "deviceId",
            "siteId",
            "policySetId",
            "policyGroupId",
            "distributionZoneId",
        }

    def test_removed_267_fields_are_gone_from_the_module(self):
        """Fields CCC 26.7 deleted must not be referenced by any query."""
        source = Path(reporting.__file__).read_text()
        for field in ("countNeeded(", "policySetEnforcementScore("):
            assert field not in source, (
                f"{field} does not exist on PolicyMetrics in CCC 26.7 — "
                "any query selecting it fails with FieldUndefined"
            )


# --------------------------------------------------------------------------
# 2. Non-vacuity — the guard must FAIL on the queries 26.7 actually rejected
# --------------------------------------------------------------------------


class TestGuardIsNonVacuous:
    """A check that cannot fail is not a check.

    Each case feeds the validator the 26.3-shaped query that CCC 26.7 rejected
    live, and asserts it produces the same class of error the live endpoint did.
    """

    def test_top_level_mac_address_is_rejected(self, schema):
        result = validate_document(_QUERY_263_TOP_LEVEL_MAC, schema)
        kinds = {error["kind"] for error in result["errors"]}
        assert kinds == {"UnknownArgument"}
        assert "macAddress" in result["errors"][0]["message"]
        assert result["errors"][0]["path"] == "policyMetrics/zeroTrustMetrics"

    def test_count_needed_is_rejected(self, schema):
        result = validate_document(_QUERY_263_COUNT_NEEDED, schema)
        assert [error["kind"] for error in result["errors"]] == ["FieldUndefined"]
        assert result["errors"][0]["path"] == "policyMetrics/countNeeded"

    def test_policy_set_enforcement_score_is_rejected(self, schema):
        result = validate_document(_QUERY_263_POLICY_SET_SCORE, schema)
        assert [error["kind"] for error in result["errors"]] == ["FieldUndefined"]
        assert result["errors"][0]["path"] == "policyMetrics/policySetEnforcementScore"

    def test_typo_in_a_root_is_rejected(self, schema):
        """An unrecognised root must be an error, not waved through as unverified."""
        result = validate_document("query Q { polcyMetrics { count } }", schema)
        assert [error["kind"] for error in result["errors"]] == ["UnknownRoot"]

    def test_meta_fields_are_not_errors(self, schema):
        """`__typename` is valid on every object type."""
        result = validate_document("query Q { policyMetrics { __typename } }", schema)
        assert result["errors"] == []


# --------------------------------------------------------------------------
# 3. Coverage is stated, not assumed
# --------------------------------------------------------------------------


class TestCoverageIsHonest:
    def test_every_query_literal_is_checked(self, report):
        """No query may escape the check by not being registered anywhere."""
        assert set(report["queries"]) == set(extract_queries())
        assert report["totals"]["queries"] >= 15

    def test_staged_schema_is_the_267_policymetrics_field_set(self, schema):
        """Pin the staged introspection to what Obiwan captured from live 26.7."""
        assert set(schema) == {"PolicyMetrics"}
        assert set(schema["PolicyMetrics"]) == {
            "count",
            "coverage",
            "aggregatePolicyEnforcementScore",
            "policyGroups",
            "zeroTrustMetrics",
        }
        assert schema["PolicyMetrics"]["zeroTrustMetrics"]["args"] == {
            "dateTime",
            "site",
            "filters",
        }

    def test_unverified_surface_is_the_known_list(self, report):
        """Queries we CANNOT check are named explicitly.

        `identityGraphMetrics`, `topologyMetrics` and `trafficVectorsMetrics`
        have not been introspected, so 11 of the queries are unverified. That is
        a stated limit, not a pass — when someone stages those types, this test
        fails and the number comes down deliberately.
        """
        unverified = {
            name
            for name, result in report["queries"].items()
            if not result["verifiedRoots"]
        }
        assert unverified == {
            "_ACTIVE_SITES_COUNT_QUERY",
            "_ACTIVE_SITES_WAP_COUNT_QUERY",
            "_DEVICES_BY_CONNECTOR_QUERY",
            "_DEVICE_COUNT_QUERY",
            "_SITE_KPIS_QUERY",
            "_TARGET_SITES_QUERY",
            "_TRAFFIC_VECTORS_BY_IP_QUERY",
            "_TRAFFIC_VECTORS_BY_PG_QUERY",
            "_TRAFFIC_VECTORS_COUNT_QUERY",
            "_VIRTUAL_EDGES_COUNT_QUERY",
            "_VIRTUAL_EDGE_NODES_COUNT_QUERY",
        }
        assert ROOT_FIELD_TYPES == {"policyMetrics": "PolicyMetrics"}
        assert KNOWN_UNVERIFIED_ROOTS == {
            "identityGraphMetrics",
            "topologyMetrics",
            "trafficVectorsMetrics",
        }

    def test_reporting_group_size(self):
        """CCC 26.7 removed two commands; the count is asserted, not implied."""
        assert len(reporting.group.commands) == 18
        assert "get-policy-count-needed" not in reporting.group.commands
        assert "get-policy-set-enforcement-score" not in reporting.group.commands


# --------------------------------------------------------------------------
# 4. The parser the check depends on
# --------------------------------------------------------------------------


class TestParser:
    def test_parses_fragments_directives_and_inline_fragments(self, schema):
        """The real query uses all three; a parser failure must not read as a pass."""
        result = validate_document(reporting._ZERO_TRUST_QUERY, schema)
        assert result["verifiedRoots"] == ["policyMetrics"]
        assert result["errors"] == []

    def test_malformed_query_raises(self, schema):
        from tools.gql_schema_check import GraphQLParseError

        with pytest.raises(GraphQLParseError):
            validate_document("query Q { policyMetrics { count ", schema)
