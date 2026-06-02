"""API key authentication dependency.

In production: set API_KEY env var. All /admin/* routes require X-API-Key header.
In local dev: leave API_KEY unset (empty string) to disable auth — matches current behaviour.
"""
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency — raises 401 if the key is wrong or missing (when auth is enabled)."""
    if not settings.api_key:
        # Auth not configured — allow. Log a warning so it's visible in Railway logs.
        import logging
        logging.getLogger(__name__).warning(
            "API_KEY is not set — all /admin routes are unauthenticated. "
            "Set API_KEY in environment variables for production."
        )
        return
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
