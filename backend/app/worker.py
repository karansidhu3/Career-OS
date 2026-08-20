"""ARQ worker (Phase 5): runs generation jobs in a separate process from the API.

The previous approach — FastAPI's in-process BackgroundTasks — silently dropped
in-flight jobs on redeploy or crash. That was an acceptable risk with one user;
it's a real trust problem once other people depend on it (losing someone's resume
generation on an application deadline is bad). Redis-backed ARQ jobs survive an
API restart: the worker just picks them back up.

Run locally with: arq app.worker.WorkerSettings
"""
import asyncio
import logging
import re
import uuid

import anthropic
from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy import select, text

from datetime import datetime, timezone

from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import configure_logging
from app.models.job import Job
from app.models.user import User
from app.services.account_deletion import hard_delete_user
from app.services.credentials import get_decrypted_key
from app.services.crypto import validate_master_keys
from app.services.error_tracking import init_error_tracking, set_user_context
from app.services.generation import GENERATION_VERSION, generate_materials
from app.services.generation_v2 import _normalize_generated_prose
from app.services.llm_client import StructuredOutputError, StructuredOutputTruncatedError
from app.services.pdf_storage import cache_resume_pdf, get_pdf_storage, resume_pdf_key

logger = logging.getLogger(__name__)


def _generation_failure_code(error: Exception) -> str:
    """Return a stable, non-sensitive reason the frontend can act on."""
    if isinstance(error, (asyncio.TimeoutError, anthropic.APITimeoutError)):
        return "anthropic_timeout"
    if isinstance(error, anthropic.AuthenticationError):
        return "api_key_invalid"
    if isinstance(error, anthropic.RateLimitError):
        return "anthropic_rate_limit"
    if isinstance(error, anthropic.BadRequestError):
        return "generation_configuration"
    if isinstance(error, StructuredOutputTruncatedError):
        return "generation_output_too_large"
    if isinstance(error, StructuredOutputError):
        return "generation_output_invalid"
    if isinstance(error, (anthropic.APIConnectionError, anthropic.InternalServerError)):
        return "anthropic_unavailable"
    return "generation_failed"


async def _on_startup(ctx) -> None:
    """The worker runs as its own process (`arq app.worker.WorkerSettings`) —
    it never imports app.main, so Phase 7's JSON logging / Sentry init (wired
    there) would otherwise never run here. This is arguably where it matters
    most: Anthropic calls, LaTeX compilation, and export/deletion sweeps are
    the most exception-prone code in the app. Also validates ENCRYPTION_MASTER_KEY
    eagerly (same reasoning as app.main's lifespan) — this is the process that
    actually decrypts user API keys during generation.
    """
    configure_logging()
    init_error_tracking()
    validate_master_keys()


def _apply_result(job: Job, result: dict) -> None:
    """Write generation result dict onto a Job instance. Caps all AI-generated text lengths."""
    job.title = (result.get("job_title") or "Untitled Role")[:200]
    job.company = (result.get("job_company") or None)
    if job.company:
        job.company = job.company[:200]
    job.fit_score = result["fit_score"]
    # Cap AI output lengths — malformed responses cannot exhaust DB storage
    job.resume_latex = (result.get("resume_latex") or "")[:120_000]
    # Preserve paragraph boundaries while applying the same safe punctuation
    # normalization used by generation validation.
    cover = (result.get("cover_letter") or "")
    cover = "\n\n".join(
        _normalize_generated_prose(paragraph)
        for paragraph in re.split(r"\n\s*\n", cover)
    )
    job.cover_letter = cover[:10_000]
    job.strategic_note = (result.get("strategic_note") or None)
    if job.strategic_note:
        # Structured analysis is bounded before rendering. Keep the complete
        # sections instead of slicing a recommendation in the middle of a
        # sentence at the historical 2,000-character boundary.
        job.strategic_note = job.strategic_note[:10_000]
    job.selected_projects = result.get("selected_projects") or None
    job.input_tokens = result.get("input_tokens")
    job.output_tokens = result.get("output_tokens")
    job.cache_read_tokens = result.get("cache_read_tokens")
    job.cache_write_tokens = result.get("cache_write_tokens")
    job.compression_attempts = result.get("compression_attempts", 0)
    job.generation_version = result.get("generation_version")
    job.generation_metadata = result.get("generation_metadata")
    job.page_count = result.get("page_count")
    job.total_cost_usd = result.get("total_cost_usd")


async def run_generation_job(ctx, job_id: int, jd_text: str, user_id: str) -> None:
    """ARQ task: call Claude, write results to DB, compile+cache the resume PDF.

    Runs on its own DB session outside the request/dependency cycle — the RLS GUC
    that app.clerk_auth.get_current_user normally sets per-request is never applied
    here, so it's set explicitly using the caller-supplied user_id (known at enqueue
    time) before touching the job row at all.
    """
    async with AsyncSessionLocal() as db:
        job = None
        generated_pdf: bytes | None = None
        try:
            # set_config/the job fetch live inside this try too — a dead pooled
            # connection surfacing here previously escaped uncaught (see the
            # `finally: await db.commit()` below, which never ran), leaving the
            # job stuck at status="processing" forever with no way to retry.
            # pool_pre_ping on the engine (app.database) should prevent the dead
            # connection in the first place; this is the backstop for anything else.
            await db.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": str(user_id)})
            set_user_context(str(user_id))
            job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
            if not job:
                return
            api_key = await get_decrypted_key(db, uuid.UUID(str(user_id)))
            if not api_key:
                raise ValueError("No Anthropic API key on file")
            result = await generate_materials(db, jd_text, api_key)
            result["generation_version"] = GENERATION_VERSION
            result["page_count"] = 1
            result["generation_metadata"] = {
                **(result.get("generation_metadata") or {}),
                "pipeline": "full_context_quality_gated",
                "temporary_quality_rollback": False,
            }
            generated_pdf = result.pop("pdf_bytes", None)
            _apply_result(job, result)
            job.status = "generated"
        except Exception as e:
            logger.exception("Generation failed for job %d: %s", job_id, e)
            if job is not None:
                job.status = "failed"
                job.title = job.title if job.title != "Generating…" else "Generation failed"
                metadata = dict(job.generation_metadata) if isinstance(job.generation_metadata, dict) else {}
                metadata["failure_code"] = _generation_failure_code(e)
                if (failed_cost := getattr(e, "recorded_cost_usd", None)) is not None:
                    job.total_cost_usd = float(job.total_cost_usd or 0) + float(failed_cost)
                    metadata["failed_call_cost_usd"] = float(failed_cost)
                job.generation_metadata = metadata
        finally:
            await db.commit()

    if job is not None and job.status == "generated" and job.resume_latex:
        try:
            if generated_pdf is not None:
                await get_pdf_storage().save(resume_pdf_key(job_id), generated_pdf)
            else:
                await cache_resume_pdf(job_id, job.resume_latex)
        except Exception:
            logger.exception("Resume PDF caching failed for job %d — will compile on first request", job_id)


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
            set_user_context(str(user.id))
            try:
                await hard_delete_user(db, user)
                logger.info("Hard-deleted user %s after grace period expired", user.id)
            except Exception:
                logger.exception("Failed to hard-delete user %s during deletion sweep", user.id)
                await db.rollback()


class WorkerSettings:
    functions = [run_generation_job]
    cron_jobs = [cron(run_account_deletion_sweep, hour=None, minute=0)]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    # ARQ's default poll_delay (0.5s) issues one Redis command per cycle even
    # when idle -- roughly 5M commands/month on Upstash's metered pricing for
    # a worker that's simply always on, which is most of a 500k/month free-tier
    # quota gone before a single real generation job runs. 8s trades a worse-case
    # ~8s delay before an enqueued job starts (negligible next to the ~20s
    # generation itself) for keeping idle-baseline usage comfortably under quota.
    poll_delay = 8
    on_startup = _on_startup
