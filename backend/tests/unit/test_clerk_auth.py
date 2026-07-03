"""
Unit tests for app.clerk_auth — Clerk session token verification and
the Clerk Backend API email lookup used during JIT user provisioning.

All network and JWKS lookups are mocked. No database, no real Clerk calls.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest

from app.clerk_auth import _decode_clerk_token, _fetch_clerk_email


# ── _decode_clerk_token ────────────────────────────────────────────────────────

def _mock_jwks_client(signing_key="fake-key"):
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = MagicMock(key=signing_key)
    return client


def test_decode_clerk_token_returns_claims_on_success():
    claims = {"sub": "user_123", "azp": "http://localhost:3000"}
    with patch("app.clerk_auth._get_jwks_client", return_value=_mock_jwks_client()), \
         patch("app.clerk_auth.jwt.decode", return_value=claims), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_frontend_api_domain = "test.clerk.accounts.dev"
        mock_settings.cors_origins.return_value = ["http://localhost:3000"]
        result = _decode_clerk_token("fake.jwt.token")
    assert result == claims


def test_decode_clerk_token_rejects_disallowed_azp():
    claims = {"sub": "user_123", "azp": "https://evil.example.com"}
    with patch("app.clerk_auth._get_jwks_client", return_value=_mock_jwks_client()), \
         patch("app.clerk_auth.jwt.decode", return_value=claims), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_frontend_api_domain = "test.clerk.accounts.dev"
        mock_settings.cors_origins.return_value = ["http://localhost:3000"]
        with pytest.raises(pyjwt.InvalidTokenError):
            _decode_clerk_token("fake.jwt.token")


def test_decode_clerk_token_allows_missing_azp():
    """Some Clerk session tokens omit azp entirely — must not be rejected for that alone."""
    claims = {"sub": "user_123"}
    with patch("app.clerk_auth._get_jwks_client", return_value=_mock_jwks_client()), \
         patch("app.clerk_auth.jwt.decode", return_value=claims), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_frontend_api_domain = "test.clerk.accounts.dev"
        mock_settings.cors_origins.return_value = ["http://localhost:3000"]
        result = _decode_clerk_token("fake.jwt.token")
    assert result == claims


def test_decode_clerk_token_rejects_azp_when_allowed_origins_empty():
    """Fails closed, not open — if ALLOWED_ORIGINS were ever accidentally
    emptied in production, a token with an azp claim must still be rejected
    rather than silently passing because there was nothing to check it against."""
    claims = {"sub": "user_123", "azp": "https://evil.example.com"}
    with patch("app.clerk_auth._get_jwks_client", return_value=_mock_jwks_client()), \
         patch("app.clerk_auth.jwt.decode", return_value=claims), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_frontend_api_domain = "test.clerk.accounts.dev"
        mock_settings.cors_origins.return_value = []
        with pytest.raises(pyjwt.InvalidTokenError):
            _decode_clerk_token("fake.jwt.token")


def test_decode_clerk_token_propagates_signature_errors():
    with patch("app.clerk_auth._get_jwks_client", return_value=_mock_jwks_client()), \
         patch("app.clerk_auth.jwt.decode", side_effect=pyjwt.InvalidSignatureError("bad sig")), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_frontend_api_domain = "test.clerk.accounts.dev"
        with pytest.raises(pyjwt.InvalidSignatureError):
            _decode_clerk_token("fake.jwt.token")


# ── _fetch_clerk_email ──────────────────────────────────────────────────────────

def _mock_httpx_response(json_body):
    resp = MagicMock()
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    return resp


async def test_fetch_clerk_email_returns_primary_email():
    body = {
        "primary_email_address_id": "idn_2",
        "email_addresses": [
            {"id": "idn_1", "email_address": "old@example.com"},
            {"id": "idn_2", "email_address": "primary@example.com"},
        ],
    }
    mock_client = AsyncMock()
    mock_client.get.return_value = _mock_httpx_response(body)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.clerk_auth.httpx.AsyncClient", return_value=mock_client), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_secret_key = "sk_test_fake"
        email = await _fetch_clerk_email("user_123")
    assert email == "primary@example.com"


async def test_fetch_clerk_email_falls_back_to_first_when_primary_id_unmatched():
    body = {
        "primary_email_address_id": "idn_missing",
        "email_addresses": [{"id": "idn_1", "email_address": "only@example.com"}],
    }
    mock_client = AsyncMock()
    mock_client.get.return_value = _mock_httpx_response(body)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.clerk_auth.httpx.AsyncClient", return_value=mock_client), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_secret_key = "sk_test_fake"
        email = await _fetch_clerk_email("user_123")
    assert email == "only@example.com"


async def test_fetch_clerk_email_falls_back_to_placeholder_when_no_emails():
    body = {"primary_email_address_id": None, "email_addresses": []}
    mock_client = AsyncMock()
    mock_client.get.return_value = _mock_httpx_response(body)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.clerk_auth.httpx.AsyncClient", return_value=mock_client), \
         patch("app.clerk_auth.settings") as mock_settings:
        mock_settings.clerk_secret_key = "sk_test_fake"
        email = await _fetch_clerk_email("user_123")
    assert email == "user_123@unknown.clerk"
