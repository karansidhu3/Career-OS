"""Sentry integration (Phase 7) — exception tracking with per-request user
context. Unlike LLMClient/PDFStorage/EmailClient, this isn't a per-call
adapter seam: the Sentry SDK is a global capture hook, installed once at
import time and left running in the background. The "no-op when
unconfigured" idiom still applies — everything here is a no-op whenever
SENTRY_DSN is unset, so local dev never talks to Sentry and never needs a DSN.
"""
import logging

from app.config import settings

_log = logging.getLogger(__name__)


def _scrub_pii(event: dict, hint: dict) -> dict:
    """Defense in depth beyond send_default_pii=False — this app's requests can
    carry a Clerk bearer token or (never intentionally logged, but headers are
    an easy place for something to leak) a decrypted Anthropic key. Strip auth
    headers from any captured event rather than trust the SDK's PII heuristics.
    """
    request = event.get("request")
    if request:
        headers = request.get("headers")
        if headers:
            for key in list(headers):
                if key.lower() in ("authorization", "cookie"):
                    headers.pop(key, None)
    return event


def init_error_tracking() -> None:
    if not settings.sentry_dsn:
        _log.info("SENTRY_DSN not set — error tracking disabled")
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.0,  # error tracking only — no perf tracing, no added cost
        send_default_pii=False,
        before_send=_scrub_pii,
    )
    _log.info("Sentry error tracking enabled")


def set_user_context(user_id: str) -> None:
    """Tag the current Sentry scope with the local user id, so any exception
    raised for the rest of this request shows up attributed to a user in the
    Sentry UI. Only the id — never email or other PII."""
    if not settings.sentry_dsn:
        return
    import sentry_sdk

    sentry_sdk.set_user({"id": user_id})
