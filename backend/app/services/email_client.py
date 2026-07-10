"""Provider-agnostic seam for the one transactional email CareerOS sends
(account deletion confirmation) — see CLAUDE.md's "What NOT to build" carve-out.
Mirrors the LLMClient/PDFStorage seam pattern: an abstract client, one real
adapter (Resend, a plain HTTP call via the httpx dependency already in use
elsewhere — no new SDK needed), and a no-op fallback so local dev without a
configured API key doesn't crash, it just logs and skips sending.
"""
import logging
from abc import ABC, abstractmethod

import httpx

_log = logging.getLogger(__name__)


class EmailClient(ABC):
    @abstractmethod
    async def send(self, *, to: str, subject: str, html_body: str) -> None: ...


class ResendAdapter(EmailClient):
    def __init__(self, api_key: str, from_address: str):
        self._api_key = api_key
        self._from_address = from_address

    async def send(self, *, to: str, subject: str, html_body: str) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": self._from_address,
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                },
                timeout=10.0,
            )
            response.raise_for_status()


class NoOpEmailClient(EmailClient):
    """Local dev / unconfigured fallback — logs instead of sending so nothing
    crashes when RESEND_API_KEY isn't set."""

    async def send(self, *, to: str, subject: str, html_body: str) -> None:
        _log.warning("EmailClient not configured — skipping send (to=%s, subject=%r)", to, subject)


def get_email_client() -> EmailClient:
    from app.config import settings
    if settings.resend_api_key:
        return ResendAdapter(settings.resend_api_key, settings.email_from_address)
    return NoOpEmailClient()
