"""
Configuration management — multi-tenant profiles stored in ~/.elisity/config.yaml
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_CONFIG_DIR = Path.home() / ".elisity"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"

SECRET_MASK = "***"
SECRET_FIELDS = ("client_secret",)


def _ensure_config_dir():
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def redact_secrets(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``profile`` with sensitive fields masked.

    Used by any code path that may render a profile to the user — both
    ``config show`` and ``config list-profiles`` route through here so
    plaintext secrets never reach stdout.
    """
    redacted = dict(profile)
    for field in SECRET_FIELDS:
        if field in redacted and redacted[field]:
            redacted[field] = SECRET_MASK
    return redacted


def load_config() -> Dict[str, Any]:
    """Load config from ~/.elisity/config.yaml or return defaults."""
    if DEFAULT_CONFIG_FILE.exists():
        with open(DEFAULT_CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: Dict[str, Any]):
    """Persist config to disk."""
    _ensure_config_dir()
    with open(DEFAULT_CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_active_profile(config: Optional[Dict] = None) -> Dict[str, str]:
    """Return the active profile's connection details.

    Resolution order per field:
    1. Environment variables (CCC_BASE_URL, CCC_CLIENT_ID, CCC_CLIENT_SECRET)
    2. Active profile in config.yaml
    """
    config = config if config is not None else load_config()
    active = config.get("active_profile", "default")
    profiles = config.get("profiles", {})
    profile = profiles.get(active, {})

    return {
        "base_url": os.environ.get("CCC_BASE_URL", profile.get("base_url", "")),
        "client_id": os.environ.get("CCC_CLIENT_ID", profile.get("client_id", "")),
        "client_secret": os.environ.get("CCC_CLIENT_SECRET", profile.get("client_secret", "")),
        "verify_ssl": profile.get("verify_ssl", True),
        "timeout": int(os.environ.get("CCC_TIMEOUT", profile.get("timeout", 30))),
        "default_format": profile.get("default_format", "json"),
    }


def set_profile(name: str, base_url: str, client_id: str, client_secret: str, **kwargs):
    """Create or update a named profile."""
    config = load_config()
    profiles = config.setdefault("profiles", {})
    profiles[name] = {
        "base_url": base_url,
        "client_id": client_id,
        "client_secret": client_secret,
        **kwargs,
    }
    if "active_profile" not in config:
        config["active_profile"] = name
    save_config(config)


def use_profile(name: str):
    """Switch active profile."""
    config = load_config()
    profiles = config.get("profiles", {})
    if name not in profiles:
        raise ValueError(f"Profile '{name}' does not exist. Available: {list(profiles.keys())}")
    config["active_profile"] = name
    save_config(config)


def list_profiles() -> Dict[str, Dict]:
    """Return all profiles with active marker; secrets are masked."""
    config = load_config()
    active = config.get("active_profile", "default")
    profiles = config.get("profiles", {})
    result = {}
    for name, p in profiles.items():
        result[name] = {**redact_secrets(p), "_active": name == active}
    return result
