"""Tests for the CCC API client."""

import json
import pytest
import responses
from unittest.mock import patch

from elisity_cli.client import CCCClient


BASE_URL = "https://test-ccc.elisity.io"
TOKEN_URL = f"{BASE_URL}/auth/realms/elisity/protocol/openid-connect/token"


@pytest.fixture
def client():
    return CCCClient(
        base_url=BASE_URL,
        client_id="test-id",
        client_secret="test-secret",
    )


class TestAuthentication:
    """Unit tests for OAuth2 authentication."""

    @responses.activate
    def test_successful_auth(self, client):
        responses.add(
            responses.POST,
            TOKEN_URL,
            json={"access_token": "test-token", "expires_in": 300},
            status=200,
        )
        assert client.authenticate() is True
        assert client.access_token == "test-token"

    @responses.activate
    def test_auth_failure(self, client):
        responses.add(
            responses.POST,
            TOKEN_URL,
            json={"error": "invalid_client"},
            status=401,
        )
        assert client.authenticate() is False
        assert client.access_token is None

    @responses.activate
    def test_auto_refresh(self, client):
        """Token should auto-refresh when expired."""
        responses.add(
            responses.POST,
            TOKEN_URL,
            json={"access_token": "token-1", "expires_in": 0},  # Immediately expired
            status=200,
        )
        responses.add(
            responses.POST,
            TOKEN_URL,
            json={"access_token": "token-2", "expires_in": 300},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"ok": True},
            status=200,
        )
        # First auth gets expired token
        client.authenticate()
        client.token_expiry = 0  # Force expiry
        # Next request should trigger re-auth
        result = client.get("/api/test")
        assert result == {"ok": True}
        assert client.access_token == "token-2"


class TestHTTPMethods:
    """Unit tests for HTTP method wrappers."""

    @responses.activate
    def test_get(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        responses.add(responses.GET, f"{BASE_URL}/api/test",
                      json={"data": "value"}, status=200)
        result = client.get("/api/test")
        assert result == {"data": "value"}

    @responses.activate
    def test_post(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        responses.add(responses.POST, f"{BASE_URL}/api/test",
                      json={"id": "new-1"}, status=201)
        result = client.post("/api/test", data={"name": "item"})
        assert result["id"] == "new-1"

    @responses.activate
    def test_put(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        responses.add(responses.PUT, f"{BASE_URL}/api/test/1",
                      json={"updated": True}, status=200)
        result = client.put("/api/test/1", data={"name": "updated"})
        assert result["updated"] is True

    @responses.activate
    def test_delete(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        responses.add(responses.DELETE, f"{BASE_URL}/api/test/1",
                      body="", status=204)
        result = client.delete("/api/test/1")
        assert result == {}

    @responses.activate
    def test_get_ndjson(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        ndjson = '{"id":"1","name":"a"}\n{"id":"2","name":"b"}'
        responses.add(responses.GET, f"{BASE_URL}/api/test",
                      body=ndjson, status=200,
                      content_type="application/x-ndjson")
        result = client.get_ndjson("/api/test")
        assert len(result) == 2
        assert result[0]["name"] == "a"


class TestPagination:
    """Unit tests for auto-pagination."""

    @responses.activate
    def test_paginate_single_page(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        responses.add(responses.GET, f"{BASE_URL}/api/items",
                      json={"content": [{"id": "1"}], "last": True, "totalPages": 1},
                      status=200)
        items = list(client.paginate("/api/items"))
        assert len(items) == 1

    @responses.activate
    def test_paginate_multi_page(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        responses.add(responses.GET, f"{BASE_URL}/api/items",
                      json={"content": [{"id": "1"}], "last": False, "totalPages": 2},
                      status=200)
        responses.add(responses.GET, f"{BASE_URL}/api/items",
                      json={"content": [{"id": "2"}], "last": True, "totalPages": 2},
                      status=200)
        items = list(client.paginate("/api/items"))
        assert len(items) == 2


class TestHealthCheck:
    """Unit tests for health check."""

    @responses.activate
    def test_healthy(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"access_token": "t", "expires_in": 300}, status=200)
        responses.add(responses.GET, f"{BASE_URL}/api/topology/v2/sites",
                      json={"content": []}, status=200)
        result = client.health_check()
        assert result["status"] == "healthy"
        assert result["authenticated"] is True

    @responses.activate
    def test_unhealthy(self, client):
        responses.add(responses.POST, TOKEN_URL,
                      json={"error": "fail"}, status=401)
        result = client.health_check()
        assert result["status"] == "error"
