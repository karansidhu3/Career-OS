"""Clerk session management (Phase 6) — list/revoke a user's sessions via
Clerk's Backend API. Mirrors app.clerk_auth._fetch_clerk_email's httpx +
bearer-secret-key pattern, the only other place this app calls Clerk's API.
"""
import httpx

from app.config import settings

_CLERK_API_BASE = "https://api.clerk.com/v1"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.clerk_secret_key}"}


async def list_sessions(clerk_user_id: str) -> list[dict]:
    """Active sessions for this Clerk user, newest activity first."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{_CLERK_API_BASE}/sessions",
            params={"user_id": clerk_user_id, "status": "active"},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
    sessions = data.get("data", data) if isinstance(data, dict) else data
    return sorted(sessions, key=lambda s: s.get("last_active_at") or 0, reverse=True)


async def get_session(session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_CLERK_API_BASE}/sessions/{session_id}", headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def revoke_session(session_id: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{_CLERK_API_BASE}/sessions/{session_id}/revoke", headers=_headers())
        resp.raise_for_status()
