"""Sentry integration (Phase 7) — exception tracking with per-request user
context. Unlike LLMClient/PDFStorage/EmailClient, this isn't a per-call
adapter seam: the Sentry SDK is a global capture hook, installed once at
import time and left running in the background. The "no-op when
unconfigured" idiom still applies — everything here is a no-op whenever
SENTRY_DSN is unset, so local dev never talks to Sentry and never needs a DSN.
"""
import logging
import re

from app.config import settings

_log = logging.getLogger(__name__)

# Anthropic keys always start with this prefix — matches regardless of which
# exact code path let one reach an exception/log message (header-stripping
# alone doesn't cover a key that ended up inside a raised exception's own text,
# e.g. some future SDK version echoing back part of a rejected key).
_KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}")


def _redact_keys(text: str) -> str:
    return _KEY_PATTERN.sub("sk-ant-[REDACTED]", text)


def _scrub_pii(event: dict, hint: dict) -> dict:
    """Defense in depth beyond send_default_pii=False — this app's requests can
    carry a Clerk bearer token or a decrypted Anthropic key. Strip auth headers
    from any captured event rather than trust the SDK's PII heuristics, and
    redact key-shaped substrings from exception/log message text itself, since
    header-stripping alone doesn't cover a key that ended up embedded in an
    exception's own message rather than a header.
    """
    request = event.get("request")
    if request:
        headers = request.get("headers")
        if headers:
            for key in list(headers):
                if key.lower() in ("authorization", "cookie"):
                    headers.pop(key, None)

    for exc in (event.get("exception") or {}).get("values") or []:
        if exc.get("value"):
            exc["value"] = _redact_keys(exc["value"])

    logentry = event.get("logentry")
    if logentry:
        if logentry.get("message"):
            logentry["message"] = _redact_keys(logentry["message"])
        if logentry.get("formatted"):
            logentry["formatted"] = _redact_keys(logentry["formatted"])

    if event.get("message"):
        event["message"] = _redact_keys(event["message"])

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
