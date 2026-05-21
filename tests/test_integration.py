"""
Integration tests — run against a real CCC instance.

These tests require a configured profile or env vars:
  CCC_BASE_URL, CCC_CLIENT_ID, CCC_CLIENT_SECRET

Skip with: pytest -m "not integration"
"""

import json
import pytest
from click.testing import CliRunner

from elisity_cli.main import cli


pytestmark = pytest.mark.integration


@pytest.fixture
def runner():
    return CliRunner()


class TestAuthIntegration:
    """Test authentication against live CCC."""

    def test_auth_test(self, runner, ccc_profile):
        result = runner.invoke(cli, ["auth", "test"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "healthy"
        assert data["authenticated"] is True

    def test_auth_whoami(self, runner, ccc_profile):
        result = runner.invoke(cli, ["auth", "whoami"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "iss" in data
        assert "elisity" in data["iss"]

    def test_auth_token(self, runner, ccc_profile):
        result = runner.invoke(cli, ["auth", "token"])
        assert result.exit_code == 0
        assert len(result.output.strip()) > 50  # JWT tokens are long


class TestTopologyIntegration:
    """Test topology operations against live CCC."""

    def test_list_sites(self, runner, ccc_profile):
        result = runner.invoke(cli, ["topology", "get-all-sites"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "label" in data[0]

    def test_list_sites_table(self, runner, ccc_profile):
        result = runner.invoke(cli, ["-f", "table", "topology", "get-all-sites"])
        assert result.exit_code == 0
        assert "id" in result.output

    def test_list_sites_jmespath(self, runner, ccc_profile):
        result = runner.invoke(cli, ["-q", "[].label", "topology", "get-all-sites"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert all(isinstance(s, str) for s in data)

    def test_list_ves(self, runner, ccc_profile):
        result = runner.invoke(cli, ["topology", "get-virtual-edge"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "content" in data

    def test_list_vens(self, runner, ccc_profile):
        result = runner.invoke(cli, ["topology", "get-virtual-edge-nodes"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "content" in data


class TestPolicyIntegration:
    """Test policy operations against live CCC."""

    def test_list_policy_sets(self, runner, ccc_profile):
        result = runner.invoke(cli, ["policy", "get-all-as-nd-json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]

    def test_list_security_profiles(self, runner, ccc_profile):
        result = runner.invoke(cli, ["policy", "get-all-security-profiles-as-nd-json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_policy_groups(self, runner, ccc_profile):
        result = runner.invoke(cli, ["policy", "get-policy-groups-json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "content" in data


class TestDevicesIntegration:
    """Test device operations against live CCC."""

    def test_device_count(self, runner, ccc_profile):
        result = runner.invoke(cli, ["devices", "get-device-count"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "devicesCount" in data
        assert data["devicesCount"] >= 0

    def test_devices_view(self, runner, ccc_profile):
        result = runner.invoke(cli, [
            "devices", "get-devices-view",
            "--body", '{"page":0,"size":5}'
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "totalElements" in data
        assert "content" in data


class TestConnectorsIntegration:
    """Test connector operations against live CCC."""

    def test_connector_status(self, runner, ccc_profile):
        result = runner.invoke(cli, ["connectors", "read"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)


class TestFlowsIntegration:
    """Test flow operations against live CCC."""

    def test_noise_definitions(self, runner, ccc_profile):
        result = runner.invoke(cli, ["flows", "get-noise-definition"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "id" in data


class TestOutputFormats:
    """Test output format options with live data."""

    def test_json_output(self, runner, ccc_profile):
        result = runner.invoke(cli, ["-f", "json", "topology", "get-all-sites"])
        assert result.exit_code == 0
        json.loads(result.output)  # Should parse as valid JSON

    def test_table_output(self, runner, ccc_profile):
        result = runner.invoke(cli, ["-f", "table", "topology", "get-all-sites"])
        assert result.exit_code == 0
        assert "─" in result.output or "━" in result.output  # Table borders

    def test_yaml_output(self, runner, ccc_profile):
        result = runner.invoke(cli, ["-f", "yaml", "topology", "get-all-sites"])
        assert result.exit_code == 0
        assert "label:" in result.output or "- id:" in result.output

    def test_csv_output(self, runner, ccc_profile):
        result = runner.invoke(cli, ["-f", "csv", "topology", "get-all-sites"])
        assert result.exit_code == 0
        assert "id" in result.output
