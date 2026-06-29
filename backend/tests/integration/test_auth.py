"""
Integration tests for API key authentication.

When API_KEY is set in the environment, /admin/* routes require a matching
X-API-Key header and return 401 otherwise. When not set, all routes are open.

These tests patch settings.api_key directly to avoid environment pollution.
"""
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.integration

# A predictable test key — not a real secret
TEST_KEY = "test-secret-key-abc123"


async def test_health_endpoint_is_unauthenticated(client):
    """Public /health should always be accessible."""
    resp = await client.get("/health")
    assert resp.status_code == 200


async def test_admin_route_accessible_when_api_key_not_configured(client):
    """/admin/* is open when API_KEY env var is empty (local dev default)."""
    # Client fixture has API_KEY="" so auth is disabled
    resp = await client.get("/admin/jobs")
    assert resp.status_code == 200


async def test_admin_route_requires_key_when_configured(client):
    with patch("app.auth.settings") as mock_settings:
        mock_settings.api_key = TEST_KEY
        # Request with no key
        resp = await client.get("/admin/jobs")
    assert resp.status_code == 401


async def test_admin_route_accepts_correct_key(client):
    with patch("app.auth.settings") as mock_settings:
        mock_settings.api_key = TEST_KEY
        resp = await client.get("/admin/jobs", headers={"X-API-Key": TEST_KEY})
    assert resp.status_code == 200


async def test_admin_route_rejects_wrong_key(client):
    with patch("app.auth.settings") as mock_settings:
        mock_settings.api_key = TEST_KEY
        resp = await client.get("/admin/jobs", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


async def test_admin_route_rejects_empty_key_when_auth_enabled(client):
    with patch("app.auth.settings") as mock_settings:
        mock_settings.api_key = TEST_KEY
        resp = await client.get("/admin/jobs", headers={"X-API-Key": ""})
    assert resp.status_code == 401
