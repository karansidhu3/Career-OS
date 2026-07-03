"""Public, unauthenticated waitlist signup (Phase 8).

Not under /admin (see ADR-006) — there is no authenticated user yet at this
point in the funnel. Rate-limited by IP since anonymous public endpoints that
write to the database are otherwise a spam/abuse surface with no other gate.
"""
import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database import get_db
from app.models.waitlist import WaitlistEntry
from app.rate_limit import get_client_ip
from app.schemas.waitlist import WaitlistSignup, WaitlistSignupResponse

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_client_ip)

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.post("", response_model=WaitlistSignupResponse, status_code=201)
@limiter.limit("5/hour")
async def join_waitlist(
    request: Request,
    body: WaitlistSignup,
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(select(WaitlistEntry.id).where(WaitlistEntry.email == body.email))
    ).scalar_one_or_none()
    if existing:
        # Same response as a fresh signup — do not reveal whether an email is
        # already on the list to an unauthenticated caller.
        return WaitlistSignupResponse(status="joined")

    db.add(WaitlistEntry(email=body.email))
    try:
        await db.commit()
    except IntegrityError:
        # Race: two concurrent signups for the same email between the SELECT
        # above and this COMMIT. The unique constraint is the real guard;
        # this just keeps the response the same instead of a 500.
        await db.rollback()
    return WaitlistSignupResponse(status="joined")
