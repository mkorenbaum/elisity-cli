"""Tests for CLI command structure and basic invocations."""

import json
import pytest
from click.testing import CliRunner

from elisity_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCLIStructure:
    """Verify CLI command groups are all registered."""

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "elisity" in result.output

    def test_root_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "topology" in result.output
        assert "policy" in result.output
        assert "devices" in result.output
        assert "connectors" in result.output
        assert "ad" in result.output
        assert "flows" in result.output
        assert "insights" in result.output
        assert "system" in result.output
        assert "auth" in result.output
        assert "config" in result.output

    def test_topology_group(self, runner):
        result = runner.invoke(cli, ["topology", "--help"])
        assert result.exit_code == 0
        assert "topology" in result.output.lower()

    def test_policy_group(self, runner):
        result = runner.invoke(cli, ["policy", "--help"])
        assert result.exit_code == 0

    def test_devices_group(self, runner):
        result = runner.invoke(cli, ["devices", "--help"])
        assert result.exit_code == 0

    def test_connectors_group(self, runner):
        result = runner.invoke(cli, ["connectors", "--help"])
        assert result.exit_code == 0

    def test_ad_group(self, runner):
        result = runner.invoke(cli, ["ad", "--help"])
        assert result.exit_code == 0

    def test_flows_group(self, runner):
        result = runner.invoke(cli, ["flows", "--help"])
        assert result.exit_code == 0

    def test_insights_group(self, runner):
        result = runner.invoke(cli, ["insights", "--help"])
        assert result.exit_code == 0

    def test_system_group(self, runner):
        result = runner.invoke(cli, ["system", "--help"])
        assert result.exit_code == 0

    def test_auth_group(self, runner):
        result = runner.invoke(cli, ["auth", "--help"])
        assert result.exit_code == 0
        assert "test" in result.output
        assert "token" in result.output
        assert "whoami" in result.output

    def test_config_group(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "set-profile" in result.output
        assert "use-profile" in result.output
        assert "list-profiles" in result.output


class TestCommandCounts:
    """Verify expected command counts per group."""

    def test_topology_commands(self):
        from elisity_cli.commands import topology
        assert len(topology.group.commands) >= 100

    def test_policy_commands(self):
        from elisity_cli.commands import policy
        assert len(policy.group.commands) >= 90

    def test_devices_commands(self):
        from elisity_cli.commands import devices
        assert len(devices.group.commands) >= 50

    def test_ad_commands(self):
        # 61 -> 49 in CCC 26.7: the spec removed 28 AD operations (the AD
        # Device / Group / User / Member surface) as part of consolidating onto
        # AD Agent V2, against 16 added. Every one of the 28 is in the diff's
        # `removed` list — see output/SPEC-DIFF-26.7.md. This is a deliberate
        # upstream removal, not command loss, so the floor moves down with it.
        from elisity_cli.commands import ad
        assert len(ad.group.commands) >= 45

    def test_connectors_commands(self):
        from elisity_cli.commands import connectors
        assert len(connectors.group.commands) >= 15

    def test_insights_commands(self):
        from elisity_cli.commands import insights
        assert len(insights.group.commands) >= 20

    def test_flows_commands(self):
        from elisity_cli.commands import flows
        assert len(flows.group.commands) >= 10

    def test_system_commands(self):
        from elisity_cli.commands import system
        assert len(system.group.commands) >= 10

    def test_total_commands(self):
        """Verify total command count across all groups."""
        from elisity_cli.commands import COMMAND_GROUPS
        total = 0
        for group_name in COMMAND_GROUPS:
            mod = __import__(f"elisity_cli.commands.{group_name}", fromlist=["group"])
            total += len(mod.group.commands)
        assert total >= 430, f"Expected 430+ commands, got {total}"


class TestConfigCommands:
    """Test config subcommands."""

    def test_set_profile(self, runner, tmp_path):
        from unittest.mock import patch
        config_file = tmp_path / "config.yaml"
        with patch("elisity_cli.config.DEFAULT_CONFIG_FILE", config_file), \
             patch("elisity_cli.config.DEFAULT_CONFIG_DIR", tmp_path):
            result = runner.invoke(cli, [
                "config", "set-profile", "test",
                "--base-url", "https://test.io",
                "--client-id", "cid",
                "--client-secret", "csecret",
            ])
            assert result.exit_code == 0
            assert "saved" in result.output

    def test_list_profiles_empty(self, runner, tmp_path):
        from unittest.mock import patch
        config_file = tmp_path / "config.yaml"
        with patch("elisity_cli.config.DEFAULT_CONFIG_FILE", config_file):
            result = runner.invoke(cli, ["config", "list-profiles"])
            assert result.exit_code == 0
