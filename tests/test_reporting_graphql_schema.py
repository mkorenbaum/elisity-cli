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

The first round of this guard checked ARGUMENTS and stopped at the first return
type it had no staging for. CCC 26.7's second breakage went straight through it:
`zeroTrustMetrics`'s arguments were right, so the query passed here and the
server rejected the fields it SELECTED --

    Validation error (FieldUndefined@[policyMetrics/zeroTrustMetrics/avgDeviceCoverage])
    Validation error (FieldUndefined@[policyMetrics/zeroTrustMetrics/avgPolicyCoverage])

-- because `ZeroTrustMetrics` was never staged, so the whole selection set was
filed as "unverified" and read as a pass. The guard now validates every selected
field at every depth, resolves named and inline fragments against their type
condition, and counts FIELD PATHS rather than queries so the denominator is the
thing that matters.

Scope, stated honestly: this is a STATIC check. It proves the queries are
well-formed against the staged schema. It does not execute anything against a
live tenant, and it can only check types we have staged introspection for.
`TestCoverageIsHonest` asserts the unverified surface is exactly the known list
and pins the field-path denominator, so widening (or silently losing) coverage
is itself a test failure.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.gql_schema_check import (  # noqa: E402
    DEFAULT_SCHEMA,
    KNOWN_UNVERIFIED_ROOTS,
    REQUIRED_STAGED_TYPES,
    ROOT_FIELD_TYPES,
    check_module,
    extract_queries,
    load_schema,
    missing_required_types,
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

# The SELECTION SET that 26.7 rejected — arguments correct, fields deleted.
# This is the shape the first round of this guard passed.
_QUERY_263_FLAT_COVERAGE = """query GetRiskAttributionScores($dt: [DateTime!]!) {
  policyMetrics {
    zeroTrustMetrics(dateTime: $dt) {
      deviceCount
      avgDeviceCoverage
      avgPolicyCoverage
    }
  }
}"""

# Drift one level deeper still: inside a nested metric object, and inside a
# named fragment. Both are places the old checker could not see at all.
_QUERY_NESTED_DRIFT = """query Q($dt: [DateTime!]!) {
  policyMetrics {
    zeroTrustMetrics(dateTime: $dt) {
      l4Metrics { avgAllowedPorts avgNonsense }
      threatVectorMetrics { ...TV }
    }
  }
}

fragment TV on ThreatVectorMetrics {
  portExposure { port }
  notAFieldOnThreatVectorMetrics
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
        """Fields CCC 26.7 deleted must not be selected by any query.

        Asserted over the query literals rather than the whole file: the module
        names these fields in comments explaining why they went, and a source
        scan would forbid documenting the change.
        """
        selected = "\n".join(extract_queries().values())
        for field in (
            "countNeeded(",
            "policySetEnforcementScore(",
            "avgDeviceCoverage",
            "avgPolicyCoverage",
        ):
            assert field not in selected, (
                f"{field} does not exist in the CCC 26.7 schema — "
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

    def test_flat_coverage_fields_are_rejected(self, schema):
        """The exact second 26.7 breakage: right arguments, deleted fields.

        The first round of this guard reported this query as UNVERIFIED and the
        suite read that as a pass, so it shipped and failed on the live tenant.
        """
        result = validate_document(_QUERY_263_FLAT_COVERAGE, schema)
        assert [e["kind"] for e in result["errors"]] == [
            "FieldUndefined", "FieldUndefined",
        ]
        assert [e["path"] for e in result["errors"]] == [
            "policyMetrics/zeroTrustMetrics/avgDeviceCoverage",
            "policyMetrics/zeroTrustMetrics/avgPolicyCoverage",
        ]
        # Same wording the live endpoint used, naming the same type.
        assert "does not exist on ZeroTrustMetrics" in result["errors"][0]["message"]

    def test_drift_inside_a_nested_object_and_a_fragment_is_rejected(self, schema):
        """Depth is not a hiding place: nested metric objects and named
        fragments are validated against their own types."""
        result = validate_document(_QUERY_NESTED_DRIFT, schema)
        assert {e["path"] for e in result["errors"]} == {
            "policyMetrics/zeroTrustMetrics/l4Metrics/avgNonsense",
            "policyMetrics/zeroTrustMetrics/threatVectorMetrics/"
            "notAFieldOnThreatVectorMetrics",
        }

    def test_undefined_fragment_spread_is_rejected(self, schema):
        result = validate_document(
            "query Q { policyMetrics { zeroTrustMetrics { ...Missing } } }", schema
        )
        assert [e["kind"] for e in result["errors"]] == ["UnknownFragment"]

    def test_unused_fragment_definition_is_rejected(self, schema):
        """The server rejects a fragment that is defined and never spread."""
        result = validate_document(
            "query Q { policyMetrics { __typename } }\n"
            "fragment Dead on ThreatVectorMetrics { portExposure { port } }",
            schema,
        )
        assert [e["kind"] for e in result["errors"]] == ["UnusedFragment"]

    def test_deleting_required_staging_is_an_error(self, schema):
        """Coverage cannot shrink quietly.

        Dropping a staged type used to turn real checks into 'unverified' lines
        while the report kept printing a percentage over a smaller denominator.
        That is how the reshape shipped, so it is now an error.
        """
        assert missing_required_types(schema) == []
        shrunk = {k: v for k, v in schema.items() if k != "ZeroTrustMetrics"}
        assert missing_required_types(shrunk) == ["ZeroTrustMetrics"]

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

    def test_staged_schema_is_the_267_reporting_type_graph(self, schema):
        """Pin the staged introspection to what was captured from live 26.7."""
        assert set(schema) == {
            "PolicyMetrics",
            "ZeroTrustMetrics",
            "PolicyDeploymentMetrics",
            "MissingPolicyMetrics",
            "MissingPolicySetMetrics",
            "SecurityProfileMetrics",
            "IcMetrics",
            "GtvMetrics",
            "L4Metrics",
            "ThreatVectorMetrics",
            "PolicyCoverage",
        }
        assert REQUIRED_STAGED_TYPES <= set(schema)
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
        # The reshape, pinned: the flat fields are absent and the nested object
        # that replaced them carries the two the CLI selects.
        ztm = schema["ZeroTrustMetrics"]
        assert "avgDeviceCoverage" not in ztm
        assert "avgPolicyCoverage" not in ztm
        assert ztm["policyDeploymentMetrics"]["type"] == "PolicyDeploymentMetrics"
        assert {"deviceCoverage", "policyDeviceCoverage"} <= set(
            schema["PolicyDeploymentMetrics"]
        )

    def test_staged_policymetrics_matches_the_verbatim_capture(self):
        """The derived staging may add return-type names, never fields or args.

        `ccc-26.7-policymetrics-introspection.json` is the verbatim live capture.
        The widened file is derived from it plus the introspection handoff; if
        the two ever disagree about which fields or arguments exist, the derived
        one is the thing that drifted.
        """
        verbatim = load_schema(
            REPO_ROOT / "tests" / "data"
            / "ccc-26.7-policymetrics-introspection.json"
        )["PolicyMetrics"]
        derived = load_schema(DEFAULT_SCHEMA)["PolicyMetrics"]
        assert set(derived) == set(verbatim)
        for name, definition in verbatim.items():
            assert derived[name]["args"] == definition["args"], name

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

    def test_field_path_denominator_is_stated(self, report):
        """Coverage is reported over FIELD PATHS, not queries.

        "11 of 15 queries unverified" was the number the first round printed,
        and it hid the thing that broke: the one query it called verified had
        its entire selection set unchecked. The denominator that matters is how
        many of the fields we actually send were checked against a staged type.
        """
        totals = report["totals"]
        assert totals["fieldPaths"] == (
            totals["fieldPathsVerified"] + totals["fieldPathsUnverified"]
        )
        # The Zero Trust query is the one that broke; it is now checked in full
        # apart from the two threat-vector value types nobody has introspected.
        zt = report["queries"]["_ZERO_TRUST_QUERY"]["fieldPaths"]
        assert zt["verified"] >= 33, zt
        assert zt["unverified"] == 8, zt
        # Every remaining gap is named, not implied.
        for name, result in report["queries"].items():
            for gap in result["unverified"]:
                assert gap["reason"], name
                assert gap["fields"] >= 1, name

    def test_required_staging_is_present(self, report):
        assert report["missingRequiredTypes"] == []

    def test_reporting_group_size(self):
        """CCC 26.7 removed three commands; the count is asserted, not implied."""
        assert len(reporting.group.commands) == 17
        assert "get-policy-count-needed" not in reporting.group.commands
        assert "get-policy-set-enforcement-score" not in reporting.group.commands
        assert "diagnose-low-score" not in reporting.group.commands


# --------------------------------------------------------------------------
# 4. The parser the check depends on
# --------------------------------------------------------------------------


class TestParser:
    def test_parses_fragments_directives_and_inline_fragments(self, schema):
        """The real query uses all three; a parser failure must not read as a pass."""
        result = validate_document(reporting._ZERO_TRUST_QUERY, schema)
        assert result["verifiedRoots"] == ["policyMetrics"]
        assert result["errors"] == []
        # Proof the fragment body was actually walked rather than skipped: the
        # threat-vector leaves show up as named gaps under their own type.
        gaps = {gap["path"] for gap in result["unverified"]}
        assert any(
            path.startswith(
                "policyMetrics/zeroTrustMetrics/threatVectorMetrics/threatVectors"
            )
            for path in gaps
        ), gaps

    def test_fragment_cycle_is_reported_not_hung(self, schema):
        result = validate_document(
            "query Q { policyMetrics { zeroTrustMetrics { ...A } } }\n"
            "fragment A on ZeroTrustMetrics { deviceCount ...A }",
            schema,
        )
        assert "CyclicFragment" in {e["kind"] for e in result["errors"]}

    def test_malformed_query_raises(self, schema):
        from tools.gql_schema_check import GraphQLParseError

        with pytest.raises(GraphQLParseError):
            validate_document("query Q { policyMetrics { count ", schema)
