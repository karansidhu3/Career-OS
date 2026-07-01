"""
Integration tests for POST /admin/profile/import (Phase 4 — resume import).

The Anthropic extraction call is mocked. Nothing here writes to the profile
tables — the endpoint only returns a draft for the frontend to review.
"""
import io
from unittest.mock import AsyncMock, patch

import pytest
from docx import Document

from app.models.ai_credential import AICredential
from app.services.crypto import encrypt

pytestmark = pytest.mark.integration

# Already in extract_profile_draft's *output* shape (empty strings cleaned to None,
# lists normalized) — this mock replaces the whole function, not just the AI call.
MOCK_DRAFT = {
    "personal": {"name": "Jane Doe", "email": "jane@example.com", "phone": None, "linkedin": None, "github": None, "location": None},
    "education": [{"school": "MIT", "degree": "BSc", "field": None, "minor": None, "start_date": None, "end_date": None}],
    "experience": [],
    "projects": [],
    "skills": [],
}


async def _add_api_key(db_session, user_id):
    encrypted_key, key_version = encrypt("sk-ant-test-fixture-key-1234")
    db_session.add(AICredential(
        user_id=user_id, provider="anthropic", encrypted_key=encrypted_key,
        key_version=key_version, key_hint="1234",
    ))
    await db_session.commit()


def _mock_llm_client():
    return patch("app.routers.profile.extract_profile_draft", new=AsyncMock(return_value=MOCK_DRAFT))


def _docx_bytes(paragraphs):
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def test_import_requires_api_key(client):
    resp = await client.post("/admin/profile/import", data={"text": "Some resume text"})
    assert resp.status_code == 400
    assert "API key" in resp.json()["detail"]


async def test_import_requires_file_or_text(client, db_session, current_test_user):
    await _add_api_key(db_session, current_test_user.id)
    resp = await client.post("/admin/profile/import")
    assert resp.status_code == 400


async def test_import_from_pasted_text(client, db_session, current_test_user):
    await _add_api_key(db_session, current_test_user.id)
    with _mock_llm_client():
        resp = await client.post("/admin/profile/import", data={"text": "Jane Doe resume text..."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["personal"]["name"] == "Jane Doe"
    assert data["personal"]["phone"] is None
    assert data["education"][0]["school"] == "MIT"


async def test_import_from_docx_upload(client, db_session, current_test_user):
    await _add_api_key(db_session, current_test_user.id)
    docx_bytes = _docx_bytes(["Jane Doe", "jane@example.com", "MIT, BSc"])
    with _mock_llm_client():
        resp = await client.post(
            "/admin/profile/import",
            files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert resp.status_code == 200
    assert resp.json()["personal"]["name"] == "Jane Doe"


async def test_import_rejects_unsupported_file_type(client, db_session, current_test_user):
    await _add_api_key(db_session, current_test_user.id)
    resp = await client.post(
        "/admin/profile/import",
        files={"file": ("resume.txt", b"plain text resume", "text/plain")},
    )
    assert resp.status_code == 400
    assert "PDF or DOCX" in resp.json()["detail"]


async def test_import_does_not_write_to_profile_tables(client, db_session, current_test_user):
    """The import endpoint must be read-only against the profile — it only returns a draft."""
    from sqlalchemy import select
    from app.models.profile import PersonalInfo

    await _add_api_key(db_session, current_test_user.id)
    with _mock_llm_client():
        resp = await client.post("/admin/profile/import", data={"text": "Jane Doe resume text..."})
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(PersonalInfo).where(PersonalInfo.user_id == current_test_user.id)
    )).scalar_one_or_none()
    assert row is None
