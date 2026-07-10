import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.account import AccountDeletionStatus
from app.services.account_deletion import deletion_deadline, hard_delete_user
from app.services.email_client import get_email_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/delete", response_model=AccountDeletionStatus)
async def get_deletion_status(current_user: User = Depends(get_current_user)):
    return AccountDeletionStatus(scheduled_deletion_at=current_user.scheduled_deletion_at)


@router.post("/delete", response_model=AccountDeletionStatus)
async def request_deletion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Starts the 7-day grace period. A confirmation email goes out immediately
    (see app.services.email_client) — the one transactional email trigger this
    app sends (CLAUDE.md carve-out). The account is hard-deleted by
    app.worker's hourly cron sweep once the deadline passes; cancel any time before
    then with DELETE /admin/account/delete, or skip the wait entirely with
    POST /admin/account/delete/now."""
    current_user.scheduled_deletion_at = deletion_deadline()
    await db.commit()

    try:
        await get_email_client().send(
            to=current_user.email,
            subject="Your CareerOS account is scheduled for deletion",
            html_body=(
                "<p>You requested account deletion. Your account and all associated data "
                "(profile, resumes, cover letters, application history) will be permanently "
                f"deleted on {current_user.scheduled_deletion_at.strftime('%B %-d, %Y')}.</p>"
                "<p>Changed your mind? Sign in and cancel the deletion any time before then.</p>"
            ),
        )
    except Exception:
        logger.exception("Failed to send deletion-confirmation email for user %s", current_user.id)

    return AccountDeletionStatus(scheduled_deletion_at=current_user.scheduled_deletion_at)


@router.delete("/delete", response_model=AccountDeletionStatus)
async def cancel_deletion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.scheduled_deletion_at = None
    await db.commit()
    return AccountDeletionStatus(scheduled_deletion_at=None)


@router.post("/delete/now", status_code=204)
async def delete_now(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Skips the remainder of the grace period and deletes immediately. Only
    reachable once a deletion is already scheduled (POST /admin/account/delete) —
    this is an acceleration of an in-progress deletion, not a separate path
    around the confirmation step that started it. No further email: the
    confirmation email already went out when deletion was first requested.
    get_current_user has already set the RLS GUC on `db` for this user (see
    app.clerk_auth._set_rls_user), same as app.worker's cron sweep does manually
    for its own out-of-request-context session."""
    if current_user.scheduled_deletion_at is None:
        raise HTTPException(status_code=400, detail="No deletion is scheduled for this account.")
    await hard_delete_user(db, current_user)
