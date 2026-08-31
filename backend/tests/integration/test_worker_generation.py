"""Integration coverage for durable generation-worker terminal states."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.worker as worker_module
from app.models.job import Job

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _worker_session_factory(test_engine, monkeypatch):
    monkeypatch.setattr(
        worker_module,
        "AsyncSessionLocal",
        async_sessionmaker(test_engine, expire_on_commit=False),
    )


async def test_commit_constraint_failure_becomes_retryable_failure(
    db_session,
    current_test_user,
    monkeypatch,
):
    """Reproduce job 75: a too-long audit label must not strand processing."""
    job = Job(
        user_id=current_test_user.id,
        title="Generating…",
        status="processing",
        description="Backend engineer role using Python and PostgreSQL.",
        generation_metadata={"started_at": "2026-08-31T01:41:46+00:00"},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    job_id = job.id
    job_description = job.description

    monkeypatch.setattr(worker_module, "GENERATION_VERSION", "x" * 33)
    monkeypatch.setattr(
        worker_module,
        "get_decrypted_key",
        AsyncMock(return_value="sk-ant-test"),
    )
    monkeypatch.setattr(
        worker_module,
        "generate_materials",
        AsyncMock(return_value={
            "job_title": "Backend Engineer",
            "job_company": "Acme",
            "fit_score": 8,
            "resume_latex": r"\documentclass{article}\begin{document}Resume\end{document}",
            "cover_letter": "A focused letter.",
            "strategic_note": "GOOD FIT\nGrounded evidence.",
            "selected_projects": ["CareerOS"],
            "generation_metadata": {"editorial_repair_used": False},
        }),
    )
    cache_mock = AsyncMock()
    monkeypatch.setattr(worker_module, "cache_resume_pdf", cache_mock)

    await worker_module.run_generation_job(
        {},
        job_id,
        job_description,
        str(current_test_user.id),
    )

    db_session.expire_all()
    persisted = (
        await db_session.execute(
            select(Job)
            .where(Job.id == job_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()

    assert persisted.status == "failed"
    assert persisted.title == "Generation failed"
    assert persisted.generation_version is None
    assert persisted.generation_metadata["failure_code"] == "generation_failed"
    assert "failed_at" in persisted.generation_metadata
    cache_mock.assert_not_awaited()
