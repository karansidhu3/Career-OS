"""Lookup helper for a user's own AI provider credential (Phase 3, BYO key).

Used by both the /admin/settings/api-key router (status/verify/delete) and the
jobs router (fetching the requesting user's key before every generation or
insights call). There is no shared fallback key — a missing credential means
the caller cannot generate, by design.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_credential import AICredential
from app.services.crypto import decrypt

DEFAULT_PROVIDER = "anthropic"


async def get_credential(
    db: AsyncSession, user_id: uuid.UUID, provider: str = DEFAULT_PROVIDER
) -> AICredential | None:
    return (
        await db.execute(
            select(AICredential).where(AICredential.user_id == user_id, AICredential.provider == provider)
        )
    ).scalar_one_or_none()


async def get_decrypted_key(
    db: AsyncSession, user_id: uuid.UUID, provider: str = DEFAULT_PROVIDER
) -> str | None:
    cred = await get_credential(db, user_id, provider)
    return decrypt(cred.encrypted_key) if cred else None
