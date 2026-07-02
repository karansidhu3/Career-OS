"""
Integration tests for /admin/account/sessions (Phase 6 — session list/revoke).

Clerk's Backend API is mocked throughout — these tests verify our routing,
response shaping, and (critically) the ownership check on revoke, not Clerk
itself. See tests/unit/test_clerk_sessions.py for the Clerk-API-call-shape tests.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.clerk_auth import get_current_session_id
from tests.integration.conftest import _test_app

pytestmark = pytest.mark.integration

_RAW_SESSIONS = [
    {
        "id": "sess_current",
        "status": "active",
        "last_active_at": 2_000_000,
        "created_at": 1_000_000,
        "user_id": "clerk_test_user",
        "latest_activity": {"browser_name": "Chrome", "device_type": "desktop", "ip_address": "1.2.3.4", "city": "Vancouver", "country": "CA"},
    },
    {
        "id": "sess_other",
        "status": "active",
        "last_active_at": 1_500_000,
        "created_at": 900_000,
        "user_id": "clerk_test_user",
        "latest_activity": {"browser_name": "Safari", "device_type": "mobile"},
    },
]


@pytest.fixture(autouse=True)
def _current_session_override():
    _test_app.dependency_overrides[get_current_session_id] = lambda: "sess_current"
    yield
    _test_app.dependency_overrides.pop(get_current_session_id, None)


async def test_list_sessions_marks_current_session(client):
    with patch("app.routers.account.clerk_list_sessions", AsyncMock(return_value=_RAW_SESSIONS)):
        resp = await client.get("/admin/account/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    current = next(s for s in data if s["id"] == "sess_current")
    other = next(s for s in data if s["id"] == "sess_other")
    assert current["is_current"] is True
    assert other["is_current"] is False
    assert current["browser"] == "Chrome"
    assert current["city"] == "Vancouver"


async def test_revoke_session_succeeds_for_owned_session(client, current_test_user):
    session_detail = {"id": "sess_other", "user_id": current_test_user.clerk_user_id}
    with patch("app.routers.account.clerk_get_session", AsyncMock(return_value=session_detail)), \
         patch("app.routers.account.clerk_revoke_session", AsyncMock()) as mock_revoke:
        resp = await client.post("/admin/account/sessions/sess_other/revoke")
    assert resp.status_code == 200
    mock_revoke.assert_awaited_once_with("sess_other")


async def test_revoke_session_rejects_session_owned_by_a_different_user(client):
    """The core IDOR guard: a session_id belonging to someone else must 404,
    not revoke. Clerk session ids aren't scoped to our app or per-request-user."""
    session_detail = {"id": "sess_someone_elses", "user_id": "clerk_a_totally_different_user"}
    with patch("app.routers.account.clerk_get_session", AsyncMock(return_value=session_detail)), \
         patch("app.routers.account.clerk_revoke_session", AsyncMock()) as mock_revoke:
        resp = await client.post("/admin/account/sessions/sess_someone_elses/revoke")
    assert resp.status_code == 404
    mock_revoke.assert_not_called()


async def test_revoke_others_skips_current_session(client):
    with patch("app.routers.account.clerk_list_sessions", AsyncMock(return_value=_RAW_SESSIONS)), \
         patch("app.routers.account.clerk_revoke_session", AsyncMock()) as mock_revoke:
        resp = await client.post("/admin/account/sessions/revoke-others")
    assert resp.status_code == 200
    assert resp.json()["revoked"] == ["sess_other"]
    mock_revoke.assert_awaited_once_with("sess_other")
