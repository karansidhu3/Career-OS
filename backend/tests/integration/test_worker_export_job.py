"""
Integration tests for app.worker.run_export_job (Phase 6).

build_export_zip and the email client are mocked — this suite verifies the
job's status transitions, storage write, and email trigger, not zip-building
or Resend itself (covered separately in test_account_export.py and
test_email_client.py).

app.worker.AsyncSessionLocal is a module-level global bound to app_engine,
which is constructed from settings.database_url/app_database_url at import
time — NOT from TEST_DATABASE_URL. Left unpatched, running this job for real
would write to the actual dev database, not the test one. _worker_session_factory
below rebinds it to the same test_engine every other integration test uses,
for the duration of each test only.
"""
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.account_export import AccountExport
from app.worker import run_export_job

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _pdf_storage_tmp_dir(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "pdf_storage_dir", str(tmp_path))


@pytest.fixture(autouse=True)
def _worker_session_factory(test_engine, monkeypatch):
    """Rebind app.worker.AsyncSessionLocal (module-level, imported at collection
    time from the real DATABASE_URL) to the test database for this test only."""
    import app.worker as worker_module
    test_session_local = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(worker_module, "AsyncSessionLocal", test_session_local)


async def _make_export(db_session, user_id):
    export = AccountExport(user_id=user_id, status="processing")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)
    return export


async def test_run_export_job_marks_ready_and_saves_zip(db_session, current_test_user):
    export = await _make_export(db_session, current_test_user.id)
    mock_email = AsyncMock()

    with patch("app.worker.build_export_zip", AsyncMock(return_value=b"PK\x03\x04fake")), \
         patch("app.worker.get_email_client", return_value=mock_email):
        await run_export_job({}, export.id, str(current_test_user.id))

    from app.services.pdf_storage import account_export_key, get_pdf_storage
    query = select(AccountExport).where(AccountExport.id == export.id).execution_options(populate_existing=True)
    refreshed = (await db_session.execute(query)).scalar_one()
    assert refreshed.status == "ready"
    assert refreshed.completed_at is not None
    assert refreshed.expires_at is not None

    stored = await get_pdf_storage().load(account_export_key(export.id))
    assert stored == b"PK\x03\x04fake"

    mock_email.send.assert_awaited_once()
    kwargs = mock_email.send.await_args.kwargs
    assert kwargs["to"] == current_test_user.email
    assert "export is ready" in kwargs["subject"].lower()


async def test_run_export_job_marks_failed_on_error_and_skips_email(db_session, current_test_user):
    export = await _make_export(db_session, current_test_user.id)
    mock_email = AsyncMock()

    with patch("app.worker.build_export_zip", AsyncMock(side_effect=RuntimeError("boom"))), \
         patch("app.worker.get_email_client", return_value=mock_email):
        await run_export_job({}, export.id, str(current_test_user.id))

    query = select(AccountExport).where(AccountExport.id == export.id).execution_options(populate_existing=True)
    refreshed = (await db_session.execute(query)).scalar_one()
    assert refreshed.status == "failed"
    assert "boom" in refreshed.error_message
    mock_email.send.assert_not_awaited()


async def test_run_export_job_is_noop_for_missing_export(current_test_user):
    # Must not raise even though export id 999999 doesn't exist.
    await run_export_job({}, 999999, str(current_test_user.id))
