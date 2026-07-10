"""Clerk session token verification and JIT user provisioning.

Replaces the old static X-API-Key scheme. Every authenticated request carries
an `Authorization: Bearer <clerk-session-jwt>` header (attached by the
frontend proxy route, never visible to the browser as a long-lived secret).
We verify the JWT against Clerk's published JWKS, then resolve it to a local
`users` row — creating one on first sighting (JIT provisioning).

The very first user ever created locally inherits all pre-multi-tenant data
(rows with user_id IS NULL) — see _claim_legacy_data. This only fires once.
"""

import logging

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import ElevatedSessionLocal, get_db
from app.models.job import Job
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.models.user import User
from app.services.error_tracking import set_user_context

_log = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

_jwks_client: PyJWKClient | None = None

# Tables that predate multi-tenancy and need their user_id backfilled exactly once.
_LEGACY_TABLES = (Job, PersonalInfo, Education, Experience, Project, SkillCategory)


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.clerk_frontend_api_domain:
            raise RuntimeError("CLERK_FRONTEND_API_DOMAIN is not configured")
        jwks_url = f"https://{settings.clerk_frontend_api_domain}/.well-known/jwks.json"
        # PyJWKClient caches keys in-memory and only re-fetches on a kid miss or after lifespan expiry.
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def _decode_clerk_token(token: str) -> dict:
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=f"https://{settings.clerk_frontend_api_domain}",
        options={"verify_aud": False},  # Clerk session tokens don't set aud
    )
    # Defense in depth: reject tokens minted for a different frontend origin
    # under the same Clerk instance, if azp is present. Deliberately fails
    # closed — if ALLOWED_ORIGINS were ever accidentally emptied in production,
    # a token that does carry an azp claim must still be rejected rather than
    # silently passing because there was nothing configured to check it against.
    allowed = settings.cors_origins()
    azp = claims.get("azp")
    if azp and azp not in allowed:
        raise jwt.InvalidTokenError(f"Token authorized party {azp!r} is not an allowed origin")
    return claims


async def _fetch_clerk_email(clerk_user_id: str) -> str:
    """One-time Clerk Backend API lookup for a user's primary email, called only on first sighting."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        )
        resp.raise_for_status()
        data = resp.json()

    primary_id = data.get("primary_email_address_id")
    emails = data.get("email_addresses", [])
    for addr in emails:
        if addr.get("id") == primary_id:
            return addr["email_address"]
    return emails[0]["email_address"] if emails else f"{clerk_user_id}@unknown.clerk"


async def _claim_legacy_data(user_id) -> None:
    """Assign every pre-multi-tenant row (user_id IS NULL) to the first real account.
    Runs exactly once — guarded by the caller checking this is the first user ever created.

    Row-Level Security normally hides these rows entirely: the policy is
    `user_id = current_setting('app.current_user_id')`, and NULL never equals
    anything — even SET row_security = off can't help, since the tables have
    FORCE ROW LEVEL SECURITY (without FORCE, RLS would be a no-op: the app's
    owner role would silently bypass it). DDL is exempt from RLS entirely, so
    toggling FORCE off for the duration of this operation — then back on — is
    the bypass. But DDL also requires table ownership, which the request's
    normal session (app.database.AsyncSessionLocal, bound to the restricted
    APP_DATABASE_URL role) deliberately does not have — that's the whole point
    of that role. So this runs on its own connection via ElevatedSessionLocal,
    bound to the owning role, fully independent of the caller's transaction.

    Caller must commit the new user row before calling this — the UPDATE here
    sets a foreign key to that user's id from a different connection, and
    Postgres checks FK constraints immediately, not at the other transaction's
    eventual commit.
    """
    table_names = [model.__tablename__ for model in _LEGACY_TABLES]
    async with ElevatedSessionLocal() as db:
        for name in table_names:
            await db.execute(text(f"ALTER TABLE {name} NO FORCE ROW LEVEL SECURITY"))
        for model in _LEGACY_TABLES:
            await db.execute(update(model).where(model.user_id.is_(None)).values(user_id=user_id))
        for name in table_names:
            await db.execute(text(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY"))
        await db.commit()
    _log.info("Legacy data claimed by first provisioned user %s", user_id)


async def _set_rls_user(db: AsyncSession, user_id) -> None:
    """Set the session-scoped RLS GUC for the rest of this request's connection.
    Session-scoped (the `false` third arg), not transaction-scoped, so it survives
    any commits a route handler makes mid-request. Reset on teardown in app.database.get_db.
    """
    await db.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": str(user_id)})


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        claims = _decode_clerk_token(creds.credentials)
    except jwt.PyJWTError as e:
        _log.warning("Clerk token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Invalid session token")

    user = (
        await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    ).scalar_one_or_none()
    if user:
        await _set_rls_user(db, user.id)
        request.state.user_id = str(user.id)
        set_user_context(str(user.id))
        return user

    # First time this Clerk identity has hit the backend — provision locally.
    # Two concurrent requests for the same brand-new identity (e.g. the
    # frontend onboarding gate's Promise.all([getProfile, getApiKeyStatus])
    # on a user's very first sign-in) can both reach this point believing
    # they're first, since neither has committed yet — a classic
    # check-then-insert race. clerk_user_id is unique, so the loser's commit
    # raises IntegrityError; recover by re-fetching the row the winner just
    # created instead of bubbling a 500 up to the caller. Left unhandled,
    # that 500 made Promise.all reject, which the frontend's onboarding gate
    # treated as "transient error, fail open" — dropping a brand-new,
    # zero-profile, zero-key user straight onto the full generation screen.
    is_first_ever_user = (
        await db.execute(select(User.id).limit(1))
    ).scalar_one_or_none() is None

    email = await _fetch_clerk_email(clerk_user_id)
    user = User(clerk_user_id=clerk_user_id, email=email)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        user = (
            await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
        ).scalar_one()
    else:
        await db.refresh(user)
        if is_first_ever_user:
            # Runs on its own elevated connection (see _claim_legacy_data) — needs
            # the user row already committed and visible there, hence the commit above.
            await _claim_legacy_data(user.id)

    await _set_rls_user(db, user.id)
    request.state.user_id = str(user.id)
    set_user_context(str(user.id))
    return user
