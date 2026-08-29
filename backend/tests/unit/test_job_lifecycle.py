"""Deterministic generation lifecycle recovery tests."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.routers.jobs import _fail_stale_generation, _start_generation


def _job(*, started_at: datetime, status: str = "processing") -> SimpleNamespace:
    return SimpleNamespace(
        id=73,
        title="Generating…",
        status=status,
        created_at=started_at,
        generation_metadata={"started_at": started_at.isoformat()},
    )


def test_stale_processing_generation_becomes_retryable_failure() -> None:
    now = datetime.now(timezone.utc)
    job = _job(started_at=now - timedelta(minutes=16))

    assert _fail_stale_generation(job, now=now) is True
    assert job.status == "failed"
    assert job.title == "Generation interrupted"
    assert job.generation_metadata["failure_code"] == "generation_interrupted"


def test_recent_processing_generation_remains_active() -> None:
    now = datetime.now(timezone.utc)
    job = _job(started_at=now - timedelta(minutes=14))

    assert _fail_stale_generation(job, now=now) is False
    assert job.status == "processing"


def test_new_attempt_replaces_failure_with_fresh_start_time() -> None:
    old_start = datetime.now(timezone.utc) - timedelta(days=1)
    job = _job(started_at=old_start, status="failed")
    job.generation_metadata["failure_code"] = "generation_interrupted"

    _start_generation(job)

    new_start = datetime.fromisoformat(job.generation_metadata["started_at"])
    assert job.status == "processing"
    assert "failure_code" not in job.generation_metadata
    assert new_start > old_start
