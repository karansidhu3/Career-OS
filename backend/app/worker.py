"""ARQ worker (Phase 5): runs generation jobs in a separate process from the API.

The previous approach — FastAPI's in-process BackgroundTasks — silently dropped
in-flight jobs on redeploy or crash. That was an acceptable risk with one user;
it's a real trust problem once other people depend on it (losing someone's resume
generation on an application deadline is bad). Redis-backed ARQ jobs survive an
API restart: the worker just picks them back up.

Run locally with: arq app.worker.WorkerSettings
"""
import logging
import uuid

from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy import select, text

from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.account_export import AccountExport
from app.models.job import Job
from app.models.user import User
from app.services.account_deletion import hard_delete_user
from app.services.account_export import build_export_zip
from app.services.credentials import get_decrypted_key
from app.services.email_client import get_email_client
from app.services.generation import generate_materials
from app.services.pdf_storage import account_export_key, cache_resume_pdf, get_pdf_storage

logger = logging.getLogger(__name__)


def _apply_result(job: Job, result: dict) -> None:
    """Write generation result dict onto a Job instance. Caps all AI-generated text lengths."""
    job.title = (result.get("job_title") or "Untitled Role")[:200]
    job.company = (result.get("job_company") or None)
    if job.company:
        job.company = job.company[:200]
    job.fit_score = result["fit_score"]
    # Cap AI output lengths — malformed responses cannot exhaust DB storage
    job.resume_latex = (result.get("resume_latex") or "")[:120_000]
    # Strip em dashes from cover letter — model sometimes ignores the language rule.
    # " — " → ", "  |  bare "—" → ", "  (handles spaced and unspaced variants)
    cover = (result.get("cover_letter") or "")
    cover = cover.replace(" — ", ", ").replace("— ", ", ").replace(" —", ",").replace("—", ", ")
    job.cover_letter = cover[:10_000]
    job.strategic_note = (result.get("strategic_note") or None)
    if job.strategic_note:
        job.strategic_note = job.strategic_note[:2_000]
    job.selected_projects = result.get("selected_projects") or None
    job.input_tokens = result.get("input_tokens")
    job.output_tokens = result.get("output_tokens")
    job.cache_read_tokens = result.get("cache_read_tokens")
    job.cache_write_tokens = result.get("cache_write_tokens")
    job.compression_attempts = result.get("compression_attempts", 0)


async def run_generation_job(ctx, job_id: int, jd_text: str, user_id: str) -> None:
    """ARQ task: call Claude, write results to DB, compile+cache the resume PDF.

    Runs on its own DB session outside the request/dependency cycle — the RLS GUC
    that app.clerk_auth.get_current_user normally sets per-request is never applied
    here, so it's set explicitly using the caller-supplied user_id (known at enqueue
    time) before touching the job row at all.
    """
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": str(user_id)})
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
        if not job:
            return
        try:
            api_key = await get_decrypted_key(db, uuid.UUID(str(user_id)))
            if not api_key:
                raise ValueError("No Anthropic API key on file")
            result = await generate_materials(db, jd_text, api_key)
            _apply_result(job, result)
            job.status = "generated"
        except Exception as e:
            logger.exception("Generation failed for job %d: %s", job_id, e)
            job.status = "failed"
            job.title = job.title if job.title != "Generating…" else "Generation failed"
        finally:
            await db.commit()

    if job.status == "generated" and job.resume_latex:
        try:
            await cache_resume_pdf(job_id, job.resume_latex)
        except Exception:
            logger.exception("Resume PDF caching failed for job %d — will compile on first request", job_id)


async def run_export_job(ctx, export_id: int, user_id: str) -> None:
    """ARQ task: build the account data export zip, store it, email the user
    that it's ready (see app.services.email_client — one of the two transactional
    email triggers this app sends, per CLAUDE.md's carve-out).
    """
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": str(user_id)})
        export = (await db.execute(select(AccountExport).where(AccountExport.id == export_id))).scalar_one_or_none()
        if not export:
            return
        user = (await db.execute(select(User).where(User.id == export.user_id))).scalar_one_or_none()
        try:
            zip_bytes = await build_export_zip(db, user)
            await get_pdf_storage().save(account_export_key(export_id), zip_bytes)
            export.status = "ready"
            export.completed_at = datetime.now(timezone.utc)
            export.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        except Exception as e:
            logger.exception("Export failed for export %d: %s", export_id, e)
            export.status = "failed"
            export.error_message = str(e)[:500]
        finally:
            await db.commit()

    if export.status == "ready" and user:
        link_line = f'<p><a href="{settings.frontend_url}">Sign in to CareerOS</a> to download it.</p>' if settings.frontend_url else "<p>Sign in to CareerOS to download it.</p>"
        try:
            await get_email_client().send(
                to=user.email,
                subject="Your CareerOS data export is ready",
                html_body=f"<p>Your account data export is ready — it includes your profile, every generated resume and cover letter, and your application history.</p>{link_line}<p>This download link expires in 7 days.</p>",
            )
        except Exception:
            logger.exception("Failed to send export-ready email for export %d", export_id)


async def run_account_deletion_sweep(ctx) -> None:
    """ARQ cron job (hourly — see WorkerSettings.cron_jobs): hard-deletes any user
    whose account-deletion grace period (Phase 6) has passed. No email on this
    trigger — the confirmation email already went out when deletion was requested;
    this sweep is silent, matching the two-transactional-email limit in CLAUDE.md.
    """
    async with AsyncSessionLocal() as db:
        due_users = list(
            (
                await db.execute(
                    select(User).where(
                        User.scheduled_deletion_at.is_not(None),
                        User.scheduled_deletion_at <= datetime.now(timezone.utc),
                    )
                )
            )
            .scalars()
            .all()
        )

    for user in due_users:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": str(user.id)})
            try:
                await hard_delete_user(db, user)
                logger.info("Hard-deleted user %s after grace period expired", user.id)
            except Exception:
                logger.exception("Failed to hard-delete user %s during deletion sweep", user.id)
                await db.rollback()


class WorkerSettings:
    functions = [run_generation_job, run_export_job]
    cron_jobs = [cron(run_account_deletion_sweep, hour=None, minute=0)]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
