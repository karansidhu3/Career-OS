"""API key authentication dependency.

In production: set API_KEY env var. All /admin/* routes require X-API-Key header.
In local dev: set DEV_MODE=true in .env to bypass auth.
"""
import hmac
import logging

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_log = logging.getLogger(__name__)


async def verify_api_key(x_api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency — raises 401 if the key is wrong or missing (when auth is enabled)."""
    if not settings.api_key:
        # Dev mode — auth disabled. Startup already logged a warning.
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")
