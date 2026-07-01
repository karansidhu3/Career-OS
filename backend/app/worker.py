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
from sqlalchemy import select, text

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.job import Job
from app.services.credentials import get_decrypted_key
from app.services.generation import generate_materials
from app.services.pdf_storage import cache_resume_pdf

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


class WorkerSettings:
    functions = [run_generation_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
