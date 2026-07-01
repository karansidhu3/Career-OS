"""
Integration tests for /admin/settings/api-key (Phase 3 — BYO AI provider key).

The validation call to Anthropic is mocked (never hits the real API in tests).
Encryption uses the real app.services.crypto against the test-only Fernet key
set in tests/conftest.py.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.models.ai_credential import AICredential
from app.services.llm_client import ToolCallResult

pytestmark = pytest.mark.integration


def _mock_llm_client():
    """Patches get_llm_client so add_api_key's validation call succeeds without
    a real Anthropic call, while still exercising the real encrypt/store path."""
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = ToolCallResult(tool_input={"ok": True})
    return patch("app.routers.credentials.get_llm_client", return_value=mock_client)


# ── GET /admin/settings/api-key ───────────────────────────────────────────────

async def test_get_status_with_no_key(client):
    resp = await client.get("/admin/settings/api-key")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_key"] is False
    assert data["key_hint"] is None


async def test_get_status_with_existing_key(client, db_session, current_test_user):
    db_session.add(AICredential(
        user_id=current_test_user.id, provider="anthropic", encrypted_key="ciphertext",
        key_version=1, key_hint="ab12", label="My key",
    ))
    await db_session.commit()

    resp = await client.get("/admin/settings/api-key")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_key"] is True
    assert data["key_hint"] == "ab12"
    assert data["label"] == "My key"


# ── POST /admin/settings/api-key ──────────────────────────────────────────────

async def test_add_key_stores_encrypted_and_returns_hint(client):
    with _mock_llm_client():
        resp = await client.post("/admin/settings/api-key", json={"api_key": "sk-ant-real-looking-key-9876"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_key"] is True
    assert data["key_hint"] == "9876"
    assert data["last_verified_at"] is not None


async def test_add_key_never_returns_raw_key(client):
    with _mock_llm_client():
        resp = await client.post("/admin/settings/api-key", json={"api_key": "sk-ant-super-secret-value-0000"})
    assert "sk-ant-super-secret-value-0000" not in resp.text


async def test_add_key_persists_decryptable_ciphertext(client, db_session, current_test_user):
    from sqlalchemy import select
    from app.services.crypto import decrypt

    with _mock_llm_client():
        resp = await client.post("/admin/settings/api-key", json={"api_key": "sk-ant-round-trip-check-1111"})
    assert resp.status_code == 200

    cred = (await db_session.execute(
        select(AICredential).where(AICredential.user_id == current_test_user.id)
    )).scalar_one()
    assert decrypt(cred.encrypted_key) == "sk-ant-round-trip-check-1111"


async def test_add_key_rotates_existing_key(client, db_session, current_test_user):
    db_session.add(AICredential(
        user_id=current_test_user.id, provider="anthropic", encrypted_key="old-ciphertext",
        key_version=1, key_hint="0000",
    ))
    await db_session.commit()

    with _mock_llm_client():
        resp = await client.post("/admin/settings/api-key", json={"api_key": "sk-ant-new-rotated-key-2222"})
    assert resp.status_code == 200
    assert resp.json()["key_hint"] == "2222"

    from sqlalchemy import select
    creds = (await db_session.execute(
        select(AICredential).where(AICredential.user_id == current_test_user.id)
    )).scalars().all()
    assert len(creds) == 1  # upsert, not a second row


async def test_add_key_rejects_invalid_key(client):
    import anthropic
    import httpx

    fake_response = httpx.Response(status_code=401, request=httpx.Request("POST", "https://api.anthropic.com"))
    mock_client = AsyncMock()
    mock_client.call_tool.side_effect = anthropic.AuthenticationError("invalid", response=fake_response, body=None)
    with patch("app.routers.credentials.get_llm_client", return_value=mock_client):
        resp = await client.post("/admin/settings/api-key", json={"api_key": "sk-ant-invalid-key-3333"})
    assert resp.status_code == 400
    assert "Invalid" in resp.json()["detail"]


async def test_add_key_rejects_too_short(client):
    resp = await client.post("/admin/settings/api-key", json={"api_key": "short"})
    assert resp.status_code == 422


# ── DELETE /admin/settings/api-key ────────────────────────────────────────────

async def test_delete_key_removes_row(client, db_session, current_test_user):
    db_session.add(AICredential(
        user_id=current_test_user.id, provider="anthropic", encrypted_key="ciphertext",
        key_version=1, key_hint="ab12",
    ))
    await db_session.commit()

    resp = await client.delete("/admin/settings/api-key")
    assert resp.status_code == 204

    status_resp = await client.get("/admin/settings/api-key")
    assert status_resp.json()["has_key"] is False


async def test_delete_key_without_existing_returns_404(client):
    resp = await client.delete("/admin/settings/api-key")
    assert resp.status_code == 404
