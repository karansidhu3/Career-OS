"""
Integration tests for /admin/account/export (Phase 6 — data export).

Export generation runs on the ARQ worker, same pattern as job generation (Phase 5) —
these routes just enqueue and return immediately. arq_pool_mock (conftest.py)
replaces the real Redis-backed pool.
"""
import pytest

from app.models.account_export import AccountExport

pytestmark = pytest.mark.integration


async def test_request_export_returns_201_processing(client, arq_pool_mock):
    resp = await client.post("/admin/account/export")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "processing"
    assert "id" in data


async def test_request_export_enqueues_on_arq_pool(client, current_test_user, arq_pool_mock):
    resp = await client.post("/admin/account/export")
    export_id = resp.json()["id"]
    arq_pool_mock.enqueue_job.assert_awaited_once_with(
        "run_export_job", export_id, str(current_test_user.id)
    )


async def test_request_export_rejects_second_concurrent_export(client, arq_pool_mock):
    first = await client.post("/admin/account/export")
    assert first.status_code == 201
    second = await client.post("/admin/account/export")
    assert second.status_code == 409


async def test_get_export_status(client, db_session, current_test_user):
    export = AccountExport(user_id=current_test_user.id, status="processing")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)

    resp = await client.get(f"/admin/account/export/{export.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"


async def test_get_export_status_404_for_missing(client):
    resp = await client.get("/admin/account/export/999999")
    assert resp.status_code == 404


async def test_download_export_404_when_not_ready(client, db_session, current_test_user):
    export = AccountExport(user_id=current_test_user.id, status="processing")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)

    resp = await client.get(f"/admin/account/export/{export.id}/download")
    assert resp.status_code == 404


async def test_download_export_returns_zip_when_ready(client, db_session, current_test_user, tmp_path, monkeypatch):
    from app.config import settings
    from app.services import pdf_storage

    monkeypatch.setattr(settings, "pdf_storage_dir", str(tmp_path))
    export = AccountExport(user_id=current_test_user.id, status="ready")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(export)

    storage = pdf_storage.get_pdf_storage()
    await storage.save(pdf_storage.account_export_key(export.id), b"PK\x03\x04fake-zip-bytes")

    resp = await client.get(f"/admin/account/export/{export.id}/download")
    assert resp.status_code == 200
    assert resp.content == b"PK\x03\x04fake-zip-bytes"
    assert resp.headers["content-type"] == "application/zip"
