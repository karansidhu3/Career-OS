"""Account deletion (Phase 6): a 7-day grace period before hard delete. Requesting
deletion sends a confirmation email (see CLAUDE.md's email carve-out — the second
of the two allowed transactional triggers, mirrors app.services.account_export's
export-ready email). app.worker's cron sweep calls hard_delete_user on any user
whose grace period has passed.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account_export import AccountExport
from app.models.ai_credential import AICredential
from app.models.job import Job
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.models.user import User
from app.services.pdf_storage import account_export_key, cover_letter_pdf_key, get_pdf_storage, resume_pdf_key

GRACE_PERIOD_DAYS = 7

# RLS-protected, user_id-scoped tables that must be purged before the user row itself.
_USER_SCOPED_MODELS = (Job, PersonalInfo, Education, Experience, Project, SkillCategory, AICredential, AccountExport)


def deletion_deadline() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=GRACE_PERIOD_DAYS)


async def hard_delete_user(db: AsyncSession, user: User) -> None:
    """Deletes every row this user owns — including cached PDFs/exports in object
    storage — then the user row itself. Caller must have already set the RLS GUC
    to this user's id on `db` (see app.worker.run_generation_job for the pattern);
    every model here except User is RLS-protected."""
    jobs = list((await db.execute(select(Job).where(Job.user_id == user.id))).scalars().all())
    exports = list((await db.execute(select(AccountExport).where(AccountExport.user_id == user.id))).scalars().all())

    storage = get_pdf_storage()
    for job in jobs:
        await storage.delete(resume_pdf_key(job.id))
        await storage.delete(cover_letter_pdf_key(job.id))
    for export in exports:
        await storage.delete(account_export_key(export.id))

    for model in _USER_SCOPED_MODELS:
        await db.execute(delete(model).where(model.user_id == user.id))
    await db.execute(delete(User).where(User.id == user.id))
    await db.commit()
