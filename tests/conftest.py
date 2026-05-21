"""Shared test fixtures for elisity-cli tests."""

import os
import pytest
from click.testing import CliRunner

from elisity_cli.config import load_config, get_active_profile


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def ccc_profile():
    """Get CCC connection profile — from config file or env vars."""
    profile = get_active_profile()
    if not profile.get("base_url"):
        pytest.skip("No CCC_BASE_URL configured — skipping live tests")
    return profile


@pytest.fixture
def ccc_client(ccc_profile):
    """Authenticated CCC client for integration tests."""
    from elisity_cli.client import CCCClient
    client = CCCClient(
        base_url=ccc_profile["base_url"],
        client_id=ccc_profile["client_id"],
        client_secret=ccc_profile["client_secret"],
        timeout=ccc_profile.get("timeout", 30),
    )
    assert client.authenticate(), "Failed to authenticate with CCC"
    return client
