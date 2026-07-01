"""
Integration tests for the jobs API (/admin/jobs/*).

These tests exercise the full HTTP layer: request parsing, route handlers,
database reads/writes, and response serialization. Claude API and PDF
compilation are mocked so tests are fast and hermetic.

Every request runs as `current_test_user` (see conftest.py). Job fixtures
inserted directly via db_session must carry that user's id, otherwise the
user-scoped routes correctly won't see them — that's the behavior under test.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.models.ai_credential import AICredential
from app.models.job import Job
from app.services.crypto import encrypt

pytestmark = pytest.mark.integration

SAMPLE_JD = "Senior Software Engineer role at a fast-growing startup. " * 5  # > 10 chars


async def _add_api_key(db_session, user_id):
    """Generation requires the requesting user to have a stored, decryptable key (Phase 3)."""
    encrypted_key, key_version = encrypt("sk-ant-test-fixture-key-1234")
    db_session.add(AICredential(
        user_id=user_id, provider="anthropic", encrypted_key=encrypted_key,
        key_version=key_version, key_hint="1234",
    ))
    await db_session.commit()


# ── POST /admin/jobs/generate ─────────────────────────────────────────────────

async def test_generate_returns_201_with_processing_status(client, db_session, current_test_user):
    await _add_api_key(db_session, current_test_user.id)
    with patch("app.routers.jobs._run_generation", new=AsyncMock()):
        resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "processing"
    assert data["title"] == "Generating…"
    assert "id" in data


async def test_generate_rejects_short_description(client):
    resp = await client.post("/admin/jobs/generate", json={"description": "short"})
    assert resp.status_code == 422


async def test_generate_rejects_missing_description(client):
    resp = await client.post("/admin/jobs/generate", json={})
    assert resp.status_code == 422


async def test_generate_requires_api_key(client):
    """Without a stored key, generation must fail fast with a clear 400 — never
    silently fall back to a shared/global key."""
    resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    assert resp.status_code == 400
    assert "API key" in resp.json()["detail"]


# ── GET /admin/jobs ───────────────────────────────────────────────────────────

async def test_list_jobs_empty(client):
    resp = await client.get("/admin/jobs")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_jobs_returns_all_jobs(client, db_session, current_test_user):
    db_session.add(Job(title="SWE at Acme", status="generated", user_id=current_test_user.id))
    db_session.add(Job(title="Backend at Stripe", status="applied", user_id=current_test_user.id))
    await db_session.commit()

    resp = await client.get("/admin/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_jobs_only_returns_current_users_jobs(client, db_session, current_test_user):
    """A job owned by a different user must never appear in this user's list."""
    from app.models.user import User
    other_user = User(clerk_user_id="other-clerk-user", email="other@example.com")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    db_session.add(Job(title="Mine", status="generated", user_id=current_test_user.id))
    db_session.add(Job(title="Not mine", status="generated", user_id=other_user.id))
    await db_session.commit()

    resp = await client.get("/admin/jobs")
    assert resp.status_code == 200
    titles = [j["title"] for j in resp.json()]
    assert titles == ["Mine"]


async def test_list_jobs_filters_by_status(client, db_session, current_test_user):
    db_session.add(Job(title="Job A", status="generated", user_id=current_test_user.id))
    db_session.add(Job(title="Job B", status="applied", user_id=current_test_user.id))
    db_session.add(Job(title="Job C", status="applied", user_id=current_test_user.id))
    await db_session.commit()

    resp = await client.get("/admin/jobs?status=applied")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 2
    assert all(j["status"] == "applied" for j in jobs)


# ── GET /admin/jobs/{id} ──────────────────────────────────────────────────────

async def test_get_job_returns_correct_job(client, db_session, current_test_user):
    job = Job(title="Target Job", company="Acme", status="generated", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.get(f"/admin/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Target Job"
    assert resp.json()["company"] == "Acme"


async def test_get_nonexistent_job_returns_404(client):
    resp = await client.get("/admin/jobs/99999")
    assert resp.status_code == 404


async def test_get_other_users_job_returns_404(client, db_session, current_test_user):
    """Guessing another user's job id must 404, not leak the row."""
    from app.models.user import User
    other_user = User(clerk_user_id="other-clerk-user-2", email="other2@example.com")
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    job = Job(title="Not yours", status="generated", user_id=other_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.get(f"/admin/jobs/{job.id}")
    assert resp.status_code == 404


# ── PATCH /admin/jobs/{id}/status ─────────────────────────────────────────────

async def test_update_status_to_applied(client, db_session, current_test_user):
    job = Job(title="Test Job", status="generated", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.patch(f"/admin/jobs/{job.id}/status", json={"status": "applied"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


async def test_update_status_to_interview(client, db_session, current_test_user):
    job = Job(title="Test Job", status="applied", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.patch(f"/admin/jobs/{job.id}/status", json={"status": "interview"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "interview"


async def test_update_status_invalid_value_returns_422(client, db_session, current_test_user):
    job = Job(title="Test Job", status="generated", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.patch(f"/admin/jobs/{job.id}/status", json={"status": "pending"})
    assert resp.status_code == 422


async def test_update_status_nonexistent_job_returns_404(client):
    resp = await client.patch("/admin/jobs/99999/status", json={"status": "applied"})
    assert resp.status_code == 404


# ── DELETE /admin/jobs/{id} ───────────────────────────────────────────────────

async def test_delete_job_returns_204(client, db_session, current_test_user):
    job = Job(title="Delete Me", status="generated", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.delete(f"/admin/jobs/{job.id}")
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"/admin/jobs/{job.id}")
    assert resp.status_code == 404


async def test_delete_nonexistent_job_returns_404(client):
    resp = await client.delete("/admin/jobs/99999")
    assert resp.status_code == 404


# ── PATCH /admin/jobs/{id}/cover-letter ───────────────────────────────────────

async def test_update_cover_letter_persists(client, db_session, current_test_user):
    job = Job(title="Test Job", status="generated", cover_letter="Original text.", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    updated = "Updated cover letter content."
    resp = await client.patch(
        f"/admin/jobs/{job.id}/cover-letter",
        json={"cover_letter": updated},
    )
    assert resp.status_code == 200
    assert resp.json()["cover_letter"] == updated


async def test_update_cover_letter_empty_returns_422(client, db_session, current_test_user):
    job = Job(title="Test Job", status="generated", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.patch(f"/admin/jobs/{job.id}/cover-letter", json={"cover_letter": ""})
    assert resp.status_code == 422


# ── GET /admin/jobs/insights ──────────────────────────────────────────────────

async def test_insights_returns_low_count_with_no_jobs(client):
    resp = await client.get("/admin/jobs/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["headline"] is None


async def test_insights_returns_low_count_with_fewer_than_3_jobs(client, db_session, current_test_user):
    db_session.add(Job(title="Job 1", status="generated", strategic_note="GOOD FIT\n- Strong match", user_id=current_test_user.id))
    db_session.add(Job(title="Job 2", status="applied",   strategic_note="GOOD FIT\n- Good match", user_id=current_test_user.id))
    await db_session.commit()

    resp = await client.get("/admin/jobs/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["headline"] is None


# ── JobRead response shape ────────────────────────────────────────────────────

async def test_job_read_includes_cost_usd_field(client, db_session, current_test_user):
    job = Job(
        title="Tokenized Job",
        status="generated",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
        cache_write_tokens=100,
        user_id=current_test_user.id,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.get(f"/admin/jobs/{job.id}")
    assert resp.status_code == 200
    assert "cost_usd" in resp.json()
    assert resp.json()["cost_usd"] > 0


async def test_job_read_cost_usd_none_without_tokens(client, db_session, current_test_user):
    job = Job(title="No Token Job", status="generated", user_id=current_test_user.id)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await client.get(f"/admin/jobs/{job.id}")
    assert resp.status_code == 200
    assert resp.json()["cost_usd"] is None
