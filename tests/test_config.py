"""Tests for configuration management."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from elisity_cli.config import (
    get_active_profile,
    set_profile,
    use_profile,
    list_profiles,
    load_config,
    save_config,
    DEFAULT_CONFIG_FILE,
)


class TestConfig:
    """Unit tests for config module."""

    def test_get_active_profile_from_env(self):
        """Environment variables take precedence over config."""
        with patch.dict(os.environ, {
            "CCC_BASE_URL": "https://test.elisity.io",
            "CCC_CLIENT_ID": "test-id",
            "CCC_CLIENT_SECRET": "test-secret",
        }):
            profile = get_active_profile(config={})
            assert profile["base_url"] == "https://test.elisity.io"
            assert profile["client_id"] == "test-id"
            assert profile["client_secret"] == "test-secret"

    def test_get_active_profile_from_config(self):
        """Config file values used when env vars absent."""
        config = {
            "active_profile": "lab",
            "profiles": {
                "lab": {
                    "base_url": "https://lab.elisity.io",
                    "client_id": "lab-id",
                    "client_secret": "lab-secret",
                }
            }
        }
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing CCC env vars
            for k in ("CCC_BASE_URL", "CCC_CLIENT_ID", "CCC_CLIENT_SECRET"):
                os.environ.pop(k, None)
            profile = get_active_profile(config=config)
            assert profile["base_url"] == "https://lab.elisity.io"
            assert profile["client_id"] == "lab-id"

    def test_set_and_list_profiles(self, tmp_path):
        """Create profiles and list them."""
        config_file = tmp_path / "config.yaml"
        with patch("elisity_cli.config.DEFAULT_CONFIG_FILE", config_file), \
             patch("elisity_cli.config.DEFAULT_CONFIG_DIR", tmp_path):
            set_profile("prod", "https://prod.elisity.io", "prod-id", "prod-secret")
            set_profile("lab", "https://lab.elisity.io", "lab-id", "lab-secret")

            profiles = list_profiles()
            assert "prod" in profiles
            assert "lab" in profiles
            assert profiles["prod"]["_active"] is True  # first created = active

    def test_use_profile(self, tmp_path):
        """Switch active profile."""
        config_file = tmp_path / "config.yaml"
        with patch("elisity_cli.config.DEFAULT_CONFIG_FILE", config_file), \
             patch("elisity_cli.config.DEFAULT_CONFIG_DIR", tmp_path):
            set_profile("a", "https://a.io", "a-id", "a-secret")
            set_profile("b", "https://b.io", "b-id", "b-secret")

            use_profile("b")
            config = load_config()
            assert config["active_profile"] == "b"

    def test_use_nonexistent_profile(self, tmp_path):
        """Switching to missing profile raises ValueError."""
        config_file = tmp_path / "config.yaml"
        with patch("elisity_cli.config.DEFAULT_CONFIG_FILE", config_file), \
             patch("elisity_cli.config.DEFAULT_CONFIG_DIR", tmp_path):
            set_profile("only", "https://a.io", "a-id", "a-secret")
            with pytest.raises(ValueError):
                use_profile("nope")
