import asyncio
import logging
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import get_current_user
from app.database import get_db
from app.models.ai_credential import AICredential
from app.models.user import User
from app.rate_limit import limiter_key
from app.schemas.credentials import CredentialCreate, CredentialStatus
from app.services.credentials import DEFAULT_PROVIDER, get_credential
from app.services.crypto import encrypt
from app.services.generation import CLAUDE_MODEL
from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=limiter_key)

router = APIRouter(prefix="/settings", tags=["settings"])

_VALIDATION_TOOL = {
    "name": "ack",
    "description": "Acknowledge the ping.",
    "input_schema": {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
    },
}


def _to_status(cred: AICredential | None) -> CredentialStatus:
    if not cred:
        return CredentialStatus(provider=DEFAULT_PROVIDER, has_key=False)
    return CredentialStatus(
        provider=cred.provider,
        has_key=True,
        key_hint=cred.key_hint,
        label=cred.label,
        last_verified_at=cred.last_verified_at,
    )


@router.get("/api-key", response_model=CredentialStatus)
async def get_api_key_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _to_status(await get_credential(db, current_user.id))


@router.post("/api-key", response_model=CredentialStatus)
@limiter.limit("10/hour")
async def add_api_key(
    request: Request,
    body: CredentialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate the submitted key with a tiny real Claude call (billed to the
    submitter's own key, never Karan's) before storing it encrypted. Overwrites
    any existing key for this provider — this is also how a user rotates their key.
    """
    llm = get_llm_client(body.api_key)
    try:
        await llm.call_tool(
            model=CLAUDE_MODEL,
            max_tokens=16,
            system="Call the ack tool with ok=true.",
            messages=[{"role": "user", "content": "ping"}],
            tool=_VALIDATION_TOOL,
            timeout=15.0,
        )
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=400, detail="Invalid Anthropic API key.")
    except anthropic.PermissionDeniedError:
        raise HTTPException(status_code=400, detail="This API key doesn't have permission to call the Claude API.")
    except (anthropic.APIStatusError, anthropic.APIConnectionError, asyncio.TimeoutError):
        raise HTTPException(status_code=400, detail="Could not verify this key with Anthropic. Check the key and try again.")
    except Exception:
        logger.exception("Unexpected error validating API key for user %s", current_user.id)
        raise HTTPException(status_code=400, detail="Could not verify this key. Check that you pasted the whole key and try again.")

    encrypted_key, key_version = encrypt(body.api_key)
    now = datetime.now(timezone.utc)

    cred = await get_credential(db, current_user.id)
    if cred:
        cred.encrypted_key = encrypted_key
        cred.key_version = key_version
        cred.key_hint = body.api_key[-4:]
        cred.label = body.label
        cred.last_verified_at = now
    else:
        cred = AICredential(
            user_id=current_user.id,
            provider=DEFAULT_PROVIDER,
            encrypted_key=encrypted_key,
            key_version=key_version,
            key_hint=body.api_key[-4:],
            label=body.label,
            last_verified_at=now,
        )
        db.add(cred)

    await db.commit()
    await db.refresh(cred)
    return _to_status(cred)


@router.delete("/api-key", status_code=204)
async def delete_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cred = await get_credential(db, current_user.id)
    if not cred:
        raise HTTPException(status_code=404, detail="No API key on file")
    await db.delete(cred)
    await db.commit()
