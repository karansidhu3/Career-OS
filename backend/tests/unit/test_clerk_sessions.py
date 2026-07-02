"""Unit tests for app.services.clerk_sessions — Clerk Backend API calls mocked,
never hits the real API in tests."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.clerk_sessions import get_session, list_sessions, revoke_session


def _mock_response(json_data):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data
    return resp


@pytest.fixture
def mock_get():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_post():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock:
        mock.return_value = _mock_response({})
        yield mock


async def test_list_sessions_unwraps_data_envelope(mock_get):
    mock_get.return_value = _mock_response({
        "data": [
            {"id": "sess_2", "last_active_at": 2000},
            {"id": "sess_1", "last_active_at": 1000},
        ],
    })
    sessions = await list_sessions("user_abc")
    assert [s["id"] for s in sessions] == ["sess_2", "sess_1"]  # newest first
    args, kwargs = mock_get.call_args
    assert kwargs["params"] == {"user_id": "user_abc", "status": "active"}


async def test_list_sessions_handles_bare_list_response(mock_get):
    mock_get.return_value = _mock_response([{"id": "sess_1", "last_active_at": 1000}])
    sessions = await list_sessions("user_abc")
    assert sessions == [{"id": "sess_1", "last_active_at": 1000}]


async def test_get_session_returns_raw_dict(mock_get):
    mock_get.return_value = _mock_response({"id": "sess_1", "user_id": "user_abc"})
    session = await get_session("sess_1")
    assert session["user_id"] == "user_abc"


async def test_revoke_session_posts_to_revoke_endpoint(mock_post):
    await revoke_session("sess_1")
    args, _ = mock_post.call_args
    assert args[0] == "https://api.clerk.com/v1/sessions/sess_1/revoke"
