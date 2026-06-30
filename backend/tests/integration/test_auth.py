"""
Integration tests for Clerk-based authentication.

/admin/* routes require a valid `Authorization: Bearer <clerk-session-jwt>` header,
verified against Clerk's JWKS in app.clerk_auth._decode_clerk_token. These tests
exercise the boundary (missing/invalid token) by temporarily removing the
get_current_user override that every other integration test relies on
(see conftest.py's current_test_user autouse fixture).

Happy-path identity resolution (JIT provisioning, legacy data claim) is covered
by tests/unit/test_clerk_auth.py, which mocks JWKS verification directly.
"""
import pytest
from unittest.mock import patch

import jwt as pyjwt

from app.clerk_auth import get_current_user
from tests.integration.conftest import _test_app

pytestmark = pytest.mark.integration


async def test_health_endpoint_is_unauthenticated(client):
    """Public /health should always be accessible."""
    resp = await client.get("/health")
    assert resp.status_code == 200


async def test_admin_route_requires_bearer_token(client):
    """Without the test override, a request with no Authorization header is rejected."""
    _test_app.dependency_overrides.pop(get_current_user, None)
    resp = await client.get("/admin/jobs")
    assert resp.status_code == 401


async def test_admin_route_rejects_invalid_token(client):
    """A syntactically present but invalid/expired token is rejected, not silently ignored."""
    _test_app.dependency_overrides.pop(get_current_user, None)
    with patch("app.clerk_auth._decode_clerk_token", side_effect=pyjwt.InvalidTokenError("bad token")):
        resp = await client.get("/admin/jobs", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


async def test_admin_route_accessible_with_valid_identity(client):
    """Sanity check: the autouse current_test_user override represents a verified identity."""
    resp = await client.get("/admin/jobs")
    assert resp.status_code == 200
