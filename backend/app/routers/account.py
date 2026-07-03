import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import get_current_user
from app.database import get_db
from app.models.account_export import AccountExport
from app.models.user import User
from app.schemas.account import AccountDeletionStatus, AccountExportRead
from app.services.account_deletion import deletion_deadline
from app.services.email_client import get_email_client
from app.services.pdf_storage import account_export_key, get_pdf_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["account"])


async def _has_active_export(db: AsyncSession, user_id) -> bool:
    existing = (
        await db.execute(
            select(AccountExport.id).where(AccountExport.user_id == user_id, AccountExport.status == "processing").limit(1)
        )
    ).scalar_one_or_none()
    return existing is not None


@router.post("/export", response_model=AccountExportRead, status_code=201)
async def request_export(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue an async account data export. Emails the user (see
    app.services.email_client) once the worker finishes building the zip."""
    if await _has_active_export(db, current_user.id):
        raise HTTPException(status_code=409, detail="An export is already in progress. Wait for it to finish before requesting another.")

    export = AccountExport(user_id=current_user.id, status="processing")
    db.add(export)
    await db.commit()
    await db.refresh(export)

    await request.app.state.arq_pool.enqueue_job("run_export_job", export.id, str(current_user.id))
    return export


@router.get("/export/{id}", response_model=AccountExportRead)
async def get_export_status(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    export = (
        await db.execute(select(AccountExport).where(AccountExport.id == id, AccountExport.user_id == current_user.id))
    ).scalar_one_or_none()
    if not export:
        raise HTTPException(status_code=404, detail="Not found")
    return export


@router.get("/export/{id}/download")
async def download_export(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    export = (
        await db.execute(select(AccountExport).where(AccountExport.id == id, AccountExport.user_id == current_user.id))
    ).scalar_one_or_none()
    if not export or export.status != "ready":
        raise HTTPException(status_code=404, detail="Export not ready")

    zip_bytes = await get_pdf_storage().load(account_export_key(id))
    if zip_bytes is None:
        raise HTTPException(status_code=404, detail="Export file no longer available")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=\"careeros-export-{id}.zip\""},
    )


@router.get("/delete", response_model=AccountDeletionStatus)
async def get_deletion_status(current_user: User = Depends(get_current_user)):
    return AccountDeletionStatus(scheduled_deletion_at=current_user.scheduled_deletion_at)


@router.post("/delete", response_model=AccountDeletionStatus)
async def request_deletion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Starts the 7-day grace period. A confirmation email goes out immediately
    (see app.services.email_client) — the second of the two transactional email
    triggers this app sends (CLAUDE.md carve-out). The account is hard-deleted by
    app.worker's hourly cron sweep once the deadline passes; cancel any time before
    then with DELETE /admin/account/delete."""
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
