"""
Integration tests for the public, unauthenticated waitlist signup endpoint
(Phase 8) — no Authorization header, no current_test_user override needed.
"""
import pytest
from sqlalchemy import select

from app.models.waitlist import WaitlistEntry

pytestmark = pytest.mark.integration


async def test_join_waitlist_creates_entry(client, db_session):
    resp = await client.post("/waitlist", json={"email": "friend@example.com"})
    assert resp.status_code == 201
    assert resp.json() == {"status": "joined"}

    entry = (
        await db_session.execute(select(WaitlistEntry).where(WaitlistEntry.email == "friend@example.com"))
    ).scalar_one_or_none()
    assert entry is not None
    assert entry.invited_at is None


async def test_join_waitlist_rejects_invalid_email(client):
    resp = await client.post("/waitlist", json={"email": "not-an-email"})
    assert resp.status_code == 422


async def test_join_waitlist_is_idempotent_for_duplicate_email(client, db_session):
    first = await client.post("/waitlist", json={"email": "dup@example.com"})
    second = await client.post("/waitlist", json={"email": "dup@example.com"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == {"status": "joined"}

    count = (
        await db_session.execute(select(WaitlistEntry).where(WaitlistEntry.email == "dup@example.com"))
    ).scalars().all()
    assert len(count) == 1


async def test_join_waitlist_requires_no_authentication(client):
    """The whole point — this must work with zero Authorization header."""
    resp = await client.post(
        "/waitlist", json={"email": "no-auth@example.com"},
        headers={},  # explicit: no bearer token
    )
    assert resp.status_code == 201
