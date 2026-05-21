"""
Regression test for REM-13: `config list-profiles` must mask `client_secret`.

The bug: `list_profiles()` returned raw profile dicts including plaintext
secrets, which would then leak to stdout (JSON/YAML/table/CSV) in any
formatter the caller chose. The fix routes every profile through
`redact_secrets()` before returning.
"""

import json
from unittest import mock

import pytest
import yaml

from elisity_cli import config as config_module


PLAINTEXT_SECRET = "super-sensitive-shhh-1234567890"


@pytest.fixture
def fake_config():
    return {
        "active_profile": "prod",
        "profiles": {
            "prod": {
                "base_url": "https://prod.idp01.elisity.io",
                "client_id": "prod-client",
                "client_secret": PLAINTEXT_SECRET,
            },
            "lab": {
                "base_url": "https://lab.idp01.elisity.io",
                "client_id": "lab-client",
                "client_secret": PLAINTEXT_SECRET + "-lab",
            },
        },
    }


def test_list_profiles_masks_client_secret(fake_config):
    with mock.patch.object(config_module, "load_config", return_value=fake_config):
        result = config_module.list_profiles()

    assert set(result.keys()) == {"prod", "lab"}
    for name, profile in result.items():
        assert profile["client_secret"] == config_module.SECRET_MASK, (
            f"profile {name!r} leaked client_secret: {profile['client_secret']!r}"
        )
        # Non-secret fields preserved
        assert profile["client_id"]
        assert profile["base_url"]
    # active marker preserved
    assert result["prod"]["_active"] is True
    assert result["lab"]["_active"] is False


def test_list_profiles_no_plaintext_leak_in_any_serialization(fake_config):
    with mock.patch.object(config_module, "load_config", return_value=fake_config):
        result = config_module.list_profiles()

    rendered_json = json.dumps(result)
    rendered_yaml = yaml.safe_dump(result)
    rendered_repr = repr(result)

    for blob in (rendered_json, rendered_yaml, rendered_repr):
        assert PLAINTEXT_SECRET not in blob, "plaintext client_secret leaked into output"
        assert PLAINTEXT_SECRET + "-lab" not in blob


def test_redact_secrets_helper_is_pure(fake_config):
    original = fake_config["profiles"]["prod"]
    masked = config_module.redact_secrets(original)
    assert masked["client_secret"] == config_module.SECRET_MASK
    # Source dict must not be mutated
    assert original["client_secret"] == PLAINTEXT_SECRET


def test_redact_secrets_skips_empty_secret():
    masked = config_module.redact_secrets({"client_secret": ""})
    assert masked["client_secret"] == ""
