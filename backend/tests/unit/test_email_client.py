"""Unit tests for app.services.email_client — the Resend transactional-email seam."""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.email_client import NoOpEmailClient, ResendAdapter, get_email_client


async def test_noop_client_does_not_raise():
    await NoOpEmailClient().send(to="a@example.com", subject="hi", html_body="<p>hi</p>")


@pytest.fixture
def mock_post():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(raise_for_status=MagicMock())
        yield mock


async def test_resend_sends_expected_payload(mock_post):
    adapter = ResendAdapter(api_key="key123", from_address="CareerOS <hi@careeros.dev>")
    await adapter.send(to="user@example.com", subject="Your export is ready", html_body="<p>done</p>")

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.resend.com/emails"
    assert kwargs["headers"]["Authorization"] == "Bearer key123"
    assert kwargs["json"] == {
        "from": "CareerOS <hi@careeros.dev>",
        "to": ["user@example.com"],
        "subject": "Your export is ready",
        "html": "<p>done</p>",
    }


async def test_resend_raises_on_http_error(mock_post):
    mock_post.return_value = MagicMock(
        raise_for_status=MagicMock(side_effect=httpx.HTTPStatusError("bad", request=MagicMock(), response=MagicMock()))
    )
    adapter = ResendAdapter(api_key="key123", from_address="CareerOS <hi@careeros.dev>")
    with pytest.raises(httpx.HTTPStatusError):
        await adapter.send(to="user@example.com", subject="s", html_body="<p>x</p>")


def test_get_email_client_uses_noop_when_unconfigured():
    from app.config import settings
    with patch.object(settings, "resend_api_key", ""):
        assert isinstance(get_email_client(), NoOpEmailClient)


def test_get_email_client_uses_resend_when_configured():
    from app.config import settings
    with patch.object(settings, "resend_api_key", "key123"):
        assert isinstance(get_email_client(), ResendAdapter)
