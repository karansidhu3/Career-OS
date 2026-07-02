"""
Integration tests for app.worker.run_account_deletion_sweep (Phase 6).

Same AsyncSessionLocal-rebinding concern as test_worker_export_job.py — the
worker's module-level session factory is bound to DATABASE_URL at import time,
not TEST_DATABASE_URL, so it must be rebound to the test engine for these tests.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.job import Job
from app.models.user import User
from app.worker import run_account_deletion_sweep

pytestmark = pytest.mark.integration


async def _schedule_deletion(db_session, user_id, when) -> None:
    """current_test_user is loaded on its own short-lived session (see conftest.py) —
    mutating the detached instance directly and committing via db_session wouldn't
    persist, since db_session never tracked that mutation."""
    await db_session.execute(update(User).where(User.id == user_id).values(scheduled_deletion_at=when))
    await db_session.commit()


@pytest.fixture(autouse=True)
def _pdf_storage_tmp_dir(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "pdf_storage_dir", str(tmp_path))


@pytest.fixture(autouse=True)
def _worker_session_factory(test_engine, monkeypatch):
    import app.worker as worker_module
    monkeypatch.setattr(worker_module, "AsyncSessionLocal", async_sessionmaker(test_engine, expire_on_commit=False))


async def test_sweep_deletes_user_past_deadline(db_session, current_test_user):
    await _schedule_deletion(db_session, current_test_user.id, datetime.now(timezone.utc) - timedelta(days=1))
    db_session.add(Job(user_id=current_test_user.id, title="Old Job", status="generated"))
    await db_session.commit()

    await run_account_deletion_sweep({})

    from sqlalchemy import select
    query = select(User).where(User.id == current_test_user.id).execution_options(populate_existing=True)
    remaining = (await db_session.execute(query)).scalar_one_or_none()
    assert remaining is None


async def test_sweep_leaves_user_within_grace_period_alone(db_session, current_test_user):
    await _schedule_deletion(db_session, current_test_user.id, datetime.now(timezone.utc) + timedelta(days=3))

    await run_account_deletion_sweep({})

    from sqlalchemy import select
    query = select(User).where(User.id == current_test_user.id).execution_options(populate_existing=True)
    remaining = (await db_session.execute(query)).scalar_one_or_none()
    assert remaining is not None


async def test_sweep_leaves_user_with_no_pending_deletion_alone(db_session, current_test_user):
    await run_account_deletion_sweep({})

    from sqlalchemy import select
    remaining = (await db_session.execute(select(User).where(User.id == current_test_user.id))).scalar_one_or_none()
    assert remaining is not None
