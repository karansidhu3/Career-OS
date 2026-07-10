"""
Integration tests for Phase 7's per-user daily generation cap and generation
velocity anomaly detection (app/routers/jobs.py).

arq_pool_mock (conftest.py) is an AsyncMock — its methods return an AsyncMock
by default (which coerces to int(1) / truthy) rather than real Redis-backed
values, so these guardrails need get/incr explicitly configured per test
rather than relying on default mock behavior.
"""
import logging

import pytest

from app.config import settings
from app.models.ai_credential import AICredential
from app.models.profile import Experience
from app.services.crypto import encrypt

pytestmark = pytest.mark.integration

SAMPLE_JD = "Senior Software Engineer role at a fast-growing startup. " * 5


async def _add_api_key(db_session, user_id):
    encrypted_key, key_version = encrypt("sk-ant-test-fixture-key-1234")
    db_session.add(AICredential(
        user_id=user_id, provider="anthropic", encrypted_key=encrypted_key,
        key_version=key_version, key_hint="1234",
    ))
    await db_session.commit()


async def _add_experience(db_session, user_id):
    """Generation also requires at least one experience or project on file —
    otherwise there's nothing for the model to write from (see jobs.py's
    _has_generatable_content)."""
    db_session.add(Experience(user_id=user_id, company="Acme Corp", role="Engineer"))
    await db_session.commit()


# ── Daily generation cap ────────────────────────────────────────────────────

async def test_generate_allowed_when_under_daily_cap(client, db_session, current_test_user, arq_pool_mock):
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = str(settings.daily_generation_limit - 1)
    resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    assert resp.status_code == 201


async def test_generate_rejects_when_daily_cap_reached(client, db_session, current_test_user, arq_pool_mock):
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = str(settings.daily_generation_limit)
    resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    assert resp.status_code == 429
    assert "Daily generation limit" in resp.json()["detail"]


async def test_generate_rejects_when_daily_cap_exceeded(client, db_session, current_test_user, arq_pool_mock):
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = str(settings.daily_generation_limit + 5)
    resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    assert resp.status_code == 429


async def test_daily_cap_does_not_enqueue_or_create_job(client, db_session, current_test_user, arq_pool_mock):
    """A request rejected by the cap must not enqueue work or leave a stray job row."""
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = str(settings.daily_generation_limit)
    resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    assert resp.status_code == 429
    arq_pool_mock.enqueue_job.assert_not_awaited()

    list_resp = await client.get("/admin/jobs")
    assert list_resp.json() == []


async def test_regenerate_respects_daily_cap(client, db_session, current_test_user, arq_pool_mock):
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = "0"
    create = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    job_id = create.json()["id"]
    # Mark it no longer "processing" so the concurrency guard doesn't also trip.
    await client.patch(f"/admin/jobs/{job_id}/status", json={"status": "skipped"})

    arq_pool_mock.get.return_value = str(settings.daily_generation_limit)
    resp = await client.post(f"/admin/jobs/{job_id}/regenerate")
    assert resp.status_code == 429


async def test_successful_generate_increments_daily_counter(client, db_session, current_test_user, arq_pool_mock):
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = "0"
    resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})
    assert resp.status_code == 201
    arq_pool_mock.incr.assert_any_await(f"daily_gen_count:{current_test_user.id}")


# ── Generation velocity anomaly detection ───────────────────────────────────

async def test_velocity_anomaly_logs_warning_at_threshold(
    client, db_session, current_test_user, arq_pool_mock, caplog
):
    """Crossing the threshold logs a structured warning but does not block the request."""
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = "0"
    arq_pool_mock.incr.side_effect = [1, settings.velocity_anomaly_threshold]

    with caplog.at_level(logging.WARNING, logger="app.routers.jobs"):
        resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})

    assert resp.status_code == 201
    assert any("velocity anomaly" in record.message for record in caplog.records)


async def test_velocity_anomaly_does_not_log_below_threshold(
    client, db_session, current_test_user, arq_pool_mock, caplog
):
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = "0"
    arq_pool_mock.incr.side_effect = [1, settings.velocity_anomaly_threshold - 1]

    with caplog.at_level(logging.WARNING, logger="app.routers.jobs"):
        resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})

    assert resp.status_code == 201
    assert not any("velocity anomaly" in record.message for record in caplog.records)


async def test_velocity_anomaly_logs_only_once_per_window(
    client, db_session, current_test_user, arq_pool_mock, caplog
):
    """Only fires exactly when the counter first crosses the threshold, not on every
    subsequent request within the same window — avoids repeat-alert log spam."""
    await _add_api_key(db_session, current_test_user.id)
    await _add_experience(db_session, current_test_user.id)
    arq_pool_mock.get.return_value = "0"
    arq_pool_mock.incr.side_effect = [1, settings.velocity_anomaly_threshold + 1]

    with caplog.at_level(logging.WARNING, logger="app.routers.jobs"):
        resp = await client.post("/admin/jobs/generate", json={"description": SAMPLE_JD})

    assert resp.status_code == 201
    assert not any("velocity anomaly" in record.message for record in caplog.records)
