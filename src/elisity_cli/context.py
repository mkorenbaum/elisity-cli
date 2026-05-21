"""
CLI context — shared state passed through Click context.
"""

import logging
import sys
from typing import Optional

import click

from elisity_cli.client import CCCClient
from elisity_cli.config import get_active_profile


class CliContext:
    """Holds the authenticated client and output preferences."""

    def __init__(self):
        self.client: Optional[CCCClient] = None
        self.format: str = "json"
        self.query: Optional[str] = None
        self.debug: bool = False
        self.profile_data: dict = {}

    def ensure_client(self) -> CCCClient:
        """Lazily create and authenticate client."""
        if self.client is not None:
            return self.client

        p = self.profile_data or get_active_profile()
        if not p.get("base_url"):
            click.echo(
                "Error: No CCC_BASE_URL configured. Run 'elisity config set-profile' "
                "or export CCC_BASE_URL.",
                err=True,
            )
            sys.exit(1)
        if not p.get("client_id") or not p.get("client_secret"):
            click.echo(
                "Error: Missing CCC_CLIENT_ID or CCC_CLIENT_SECRET. "
                "Run 'elisity config set-profile' or export env vars.",
                err=True,
            )
            sys.exit(1)

        self.client = CCCClient(
            base_url=p["base_url"],
            client_id=p["client_id"],
            client_secret=p["client_secret"],
            timeout=p.get("timeout", 30),
            verify_ssl=p.get("verify_ssl", True),
        )

        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
            logging.getLogger("urllib3").setLevel(logging.DEBUG)

        return self.client


pass_context = click.make_pass_decorator(CliContext, ensure=True)
