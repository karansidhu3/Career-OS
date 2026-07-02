"""
Integration tests for /admin/account/delete (Phase 6 — account deletion grace period).

The confirmation email is mocked (never hits the real Resend API in tests).
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

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
    """Only two email triggers exist in this app (export-ready, deletion-request)
    — cancellation is silent by design."""
    with _mock_email_client() as mock_get_client:
        await client.post("/admin/account/delete")
        mock_get_client.reset_mock()
        await client.delete("/admin/account/delete")
        mock_get_client.assert_not_called()
