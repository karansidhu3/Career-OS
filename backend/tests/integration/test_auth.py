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
import asyncio
import uuid
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.clerk_auth import get_current_user
from app.models.user import User
from tests.integration.conftest import _test_app

pytestmark = pytest.mark.integration


async def test_health_endpoint_is_unauthenticated(client):
    """Public /health should always be accessible."""
    resp = await client.get("/health")
    assert resp.status_code == 200


async def test_health_endpoint_supports_head(client):
    """Uptime monitors (Phase 7) commonly probe with HEAD, not GET, to save
    bandwidth — a route registered with only @app.get does not automatically
    support HEAD in FastAPI/Starlette, so this needs its own coverage."""
    resp = await client.head("/health")
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


async def test_concurrent_first_sign_in_does_not_500_on_jit_race(test_engine):
    """Regression test for a real bug: get_current_user's JIT provisioning was a
    plain check-then-insert with no locking. The frontend's onboarding gate fires
    two concurrent authenticated requests on a user's very first sign-in
    (Promise.all([getProfile, getApiKeyStatus])) — both would see no existing row
    for the brand-new clerk_user_id, both would try to INSERT, and the loser hit
    the unique constraint and raised IntegrityError, bubbling a 500. The frontend
    treated that 500 as "transient error, fail open" and dropped the new user
    straight onto the generation screen with no profile and no API key.

    Uses a real asyncio.Barrier so both concurrent calls are guaranteed to pass
    their "does this user exist yet" check before either commits — deterministically
    reproducing the race instead of hoping the scheduler interleaves them.
    """
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    clerk_id = f"race_test_{uuid.uuid4()}"
    claims = {"sub": clerk_id}
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake.jwt.token")
    barrier = asyncio.Barrier(2)

    async def _fake_fetch_email(_clerk_user_id):
        # Both calls reach here only after their own initial existence check
        # has already run — waiting here forces both to have observed "no
        # user yet" before either proceeds to INSERT.
        await barrier.wait()
        return f"{clerk_id}@example.com"

    async def _call():
        async with session_factory() as session:
            return await get_current_user(request=MagicMock(), creds=creds, db=session)

    with patch("app.clerk_auth._decode_clerk_token", return_value=claims), \
         patch("app.clerk_auth._fetch_clerk_email", new=_fake_fetch_email):
        user_a, user_b = await asyncio.gather(_call(), _call())

    # Neither call raised (no 500 to trigger the frontend's fail-open path),
    # and both concurrent requests resolved to the same single user row.
    assert user_a.id == user_b.id

    async with session_factory() as session:
        rows = (
            await session.execute(select(User).where(User.clerk_user_id == clerk_id))
        ).scalars().all()
    assert len(rows) == 1
