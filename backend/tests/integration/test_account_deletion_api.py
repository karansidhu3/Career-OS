"""
Integration tests for /admin/account/delete (Phase 6 — account deletion grace period).

The confirmation email is mocked (never hits the real Resend API in tests).
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.user import User

pytestmark = pytest.mark.integration


def _mock_email_client():
    return patch("app.routers.account.get_email_client", return_value=AsyncMock())


async def test_get_deletion_status_defaults_to_not_scheduled(client):
    resp = await client.get("/admin/account/delete")
    assert resp.status_code == 200
    assert resp.json()["scheduled_deletion_at"] is None


async def test_request_deletion_schedules_and_sends_email(client):
    with _mock_email_client() as mock_get_client:
        resp = await client.post("/admin/account/delete")
    assert resp.status_code == 200
    scheduled = resp.json()["scheduled_deletion_at"]
    assert scheduled is not None

    scheduled_dt = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
    days_out = (scheduled_dt - datetime.now(timezone.utc)).days
    assert 6 <= days_out <= 7  # ~7 days, allowing for test execution time

    mock_get_client.return_value.send.assert_awaited_once()
    kwargs = mock_get_client.return_value.send.await_args.kwargs
    assert "scheduled for deletion" in kwargs["subject"].lower()


async def test_get_deletion_status_reflects_pending_request(client):
    with _mock_email_client():
        await client.post("/admin/account/delete")
    resp = await client.get("/admin/account/delete")
    assert resp.json()["scheduled_deletion_at"] is not None


async def test_cancel_deletion_clears_schedule(client):
    with _mock_email_client():
        await client.post("/admin/account/delete")
    resp = await client.delete("/admin/account/delete")
    assert resp.status_code == 200
    assert resp.json()["scheduled_deletion_at"] is None

    status_resp = await client.get("/admin/account/delete")
    assert status_resp.json()["scheduled_deletion_at"] is None


async def test_cancel_deletion_sends_no_email(client):
    """Only one email trigger exists in this app (deletion-request) —
    cancellation is silent by design."""
    with _mock_email_client() as mock_get_client:
        await client.post("/admin/account/delete")
        mock_get_client.reset_mock()
        await client.delete("/admin/account/delete")
        mock_get_client.assert_not_called()


# ── POST /admin/account/delete/now ───────────────────────────────────────────

async def test_delete_now_rejects_when_nothing_scheduled(client):
    """Delete-now is an acceleration of an already-scheduled deletion, not an
    alternate path around the confirmation step that starts one."""
    resp = await client.post("/admin/account/delete/now")
    assert resp.status_code == 400
    assert "no deletion is scheduled" in resp.json()["detail"].lower()


async def test_delete_now_removes_the_user_immediately(client, db_session, current_test_user):
    with _mock_email_client():
        await client.post("/admin/account/delete")

    resp = await client.post("/admin/account/delete/now")
    assert resp.status_code == 204

    db_session.expire_all()
    user_row = (await db_session.execute(select(User).where(User.id == current_test_user.id))).scalar_one_or_none()
    assert user_row is None


async def test_delete_now_sends_no_additional_email(client):
    """The confirmation email already went out when deletion was first
    requested — delete-now is silent, same as cancel."""
    with _mock_email_client() as mock_get_client:
        await client.post("/admin/account/delete")
        mock_get_client.reset_mock()
        await client.post("/admin/account/delete/now")
        mock_get_client.assert_not_called()
