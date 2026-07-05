"""
Integration tests for the Phase 5 PDF caching behavior: compile once at
generation/first-request time, serve cached bytes on subsequent requests, and
invalidate the cover letter cache when its text is edited.

compile_latex_to_pdf is mocked — this suite verifies the caching logic, not
Tectonic itself.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.models.job import Job

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _pdf_storage_tmp_dir(tmp_path, monkeypatch):
    """Every get_pdf_storage() call resolves this same tmp dir — hermetic per test,
    regardless of which module imported the function."""
    from app.config import settings
    monkeypatch.setattr(settings, "pdf_storage_dir", str(tmp_path))


async def _make_job(db_session, user_id, **kwargs):
    job = Job(user_id=user_id, title="Test Job", status="generated", resume_latex=r"\section{Test}", **kwargs)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_resume_pdf_compiles_once_and_serves_cache_on_second_request(client, db_session, current_test_user):
    job = await _make_job(db_session, current_test_user.id)
    mock_compile = AsyncMock(return_value=b"%PDF-fake-resume")

    with patch("app.services.pdf.compile_latex_to_pdf", mock_compile):
        r1 = await client.get(f"/admin/jobs/{job.id}/resume.pdf")
        assert r1.status_code == 200
        assert mock_compile.await_count == 1

        r2 = await client.get(f"/admin/jobs/{job.id}/resume.pdf")
        assert r2.status_code == 200
        assert mock_compile.await_count == 1  # served from cache, not recompiled

    assert r1.content == r2.content == b"%PDF-fake-resume"


async def test_resume_preview_shares_the_same_cache_as_download(client, db_session, current_test_user):
    job = await _make_job(db_session, current_test_user.id)
    mock_compile = AsyncMock(return_value=b"%PDF-shared")

    with patch("app.services.pdf.compile_latex_to_pdf", mock_compile):
        r1 = await client.get(f"/admin/jobs/{job.id}/resume-preview.pdf")
        assert mock_compile.await_count == 1
        r2 = await client.get(f"/admin/jobs/{job.id}/resume.pdf")
        assert mock_compile.await_count == 1  # preview already populated the cache


async def test_cover_letter_pdf_caches_and_invalidates_on_edit(client, db_session, current_test_user):
    job = await _make_job(db_session, current_test_user.id, cover_letter="Original.\n\nBody.\n\nClose.")

    with patch("app.services.pdf.compile_latex_to_pdf", AsyncMock(return_value=b"%PDF-v1")) as mock_v1:
        r1 = await client.get(f"/admin/jobs/{job.id}/cover-letter.pdf")
        assert r1.status_code == 200 and r1.content == b"%PDF-v1"
        assert mock_v1.await_count == 1

        r2 = await client.get(f"/admin/jobs/{job.id}/cover-letter.pdf")
        assert mock_v1.await_count == 1  # cached, not recompiled

    resp = await client.patch(f"/admin/jobs/{job.id}/cover-letter", json={"cover_letter": "Updated.\n\nBody.\n\nClose."})
    assert resp.status_code == 200

    with patch("app.services.pdf.compile_latex_to_pdf", AsyncMock(return_value=b"%PDF-v2")) as mock_v2:
        r3 = await client.get(f"/admin/jobs/{job.id}/cover-letter.pdf")
        assert r3.content == b"%PDF-v2"
        assert mock_v2.await_count == 1  # recompiled after the edit invalidated the cache


async def test_cover_letter_preview_shares_the_same_cache_as_download(client, db_session, current_test_user):
    job = await _make_job(db_session, current_test_user.id, cover_letter="Original.\n\nBody.\n\nClose.")
    mock_compile = AsyncMock(return_value=b"%PDF-shared-cl")

    with patch("app.services.pdf.compile_latex_to_pdf", mock_compile):
        r1 = await client.get(f"/admin/jobs/{job.id}/cover-letter-preview.pdf")
        assert r1.status_code == 200
        assert mock_compile.await_count == 1
        r2 = await client.get(f"/admin/jobs/{job.id}/cover-letter.pdf")
        assert mock_compile.await_count == 1  # preview already populated the cache


async def test_delete_job_removes_cached_pdfs(client, db_session, current_test_user):
    job = await _make_job(db_session, current_test_user.id, cover_letter="Text.\n\nBody.\n\nClose.")

    with patch("app.services.pdf.compile_latex_to_pdf", AsyncMock(return_value=b"%PDF")):
        await client.get(f"/admin/jobs/{job.id}/resume.pdf")
        await client.get(f"/admin/jobs/{job.id}/cover-letter.pdf")

    from app.services.pdf_storage import cover_letter_pdf_key, get_pdf_storage, resume_pdf_key
    storage = get_pdf_storage()
    assert await storage.load(resume_pdf_key(job.id)) is not None
    assert await storage.load(cover_letter_pdf_key(job.id)) is not None

    resp = await client.delete(f"/admin/jobs/{job.id}")
    assert resp.status_code == 204

    assert await storage.load(resume_pdf_key(job.id)) is None
    assert await storage.load(cover_letter_pdf_key(job.id)) is None
