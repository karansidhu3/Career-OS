import datetime
import io
import logging
import re

from pypdf import PdfReader, PdfWriter

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from slowapi import Limiter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.job import Job
from app.rate_limit import limiter_key
from app.models.profile import Experience, PersonalInfo, Project, SkillCategory
from app.models.user import User
from app.schemas.job import CandidacyInsightsRead, CoverLetterUpdate, JobGenerateRequest, JobListRead, JobRead, StatusUpdate
from app.services.credentials import get_decrypted_key
from app.services.generation import generate_insights
from app.services.pdf_storage import cache_cover_letter_pdf, cache_resume_pdf, cover_letter_pdf_key, get_pdf_storage, invalidate_cover_letter_pdf, resume_pdf_key

logger = logging.getLogger(__name__)


limiter = Limiter(key_func=limiter_key)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _safe_filename(value: str, fallback: str = "company", max_len: int = 50) -> str:
    """Sanitize AI-generated strings used in Content-Disposition filenames."""
    safe = re.sub(r'[^a-zA-Z0-9\-]', '-', value)
    safe = re.sub(r'-{2,}', '-', safe).strip('-').lower()
    return (safe or fallback)[:max_len]


# ── Cover letter LaTeX builder ────────────────────────────────────────────────

# Single-pass regex substitution prevents double-escaping (e.g. \ → \textbackslash{}
# must not have its {} further escaped). Unicode typography is normalised first via
# chained .replace() because none of those replacements produce LaTeX special chars.
_LATEX_SPECIAL_RE = re.compile(r'[\\{}&$%#_]')
_LATEX_CHAR_MAP: dict[str, str] = {
    '\\': r'\textbackslash{}',
    '{':  r'\{',
    '}':  r'\}',
    '&':  r'\&',
    '$':  r'\$',
    '%':  r'\%',
    '#':  r'\#',
    '_':  r'\_',
}


def _escape_latex(text: str) -> str:
    """Escape plain text content for use inside a LaTeX document body."""
    text = (
        text
        .replace("—", "---")  # em dash
        .replace("–", "--")   # en dash
        .replace("‘", "'")    # left single quote
        .replace("’", "'")    # right single quote
        .replace("“", "``")   # left double quote
        .replace("”", "''")   # right double quote
        .replace("…", "...")   # ellipsis
        .replace(" ", " ")  # non-breaking space
    )
    return _LATEX_SPECIAL_RE.sub(lambda m: _LATEX_CHAR_MAP[m.group()], text)


# LaTeX cover letter template.
# Uses charter font, eso-pic gray header band, fontawesome contact icons.
# Placeholders: <<NAME>>, <<CONTACT>>, <<DATE>>, <<RELINE>>, <<BODY>>
_COVER_LETTER_LATEX = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{charter}
\usepackage[left=0.85in, right=0.85in, top=0.5in, bottom=0.85in]{geometry}
\usepackage{fontawesome}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor}
\usepackage{eso-pic}
\pagestyle{empty}
\definecolor{hdrbg}{RGB}{234,234,230}
\setlength{\parindent}{0pt}
\setlength{\parskip}{10pt}

\begin{document}

\AddToShipoutPictureBG*{%
  \color{hdrbg}%
  \AtPageUpperLeft{\rule[-1.30in]{\paperwidth}{1.30in}}%
}

\vspace*{0.04in}
\begin{center}
{\fontsize{26}{30}\selectfont\scshape <<NAME>>}\\\vspace{5pt}
{\small\color[RGB]{80,80,80}
  <<CONTACT>>%
}
\end{center}
\vspace*{0.18in}

<<DATE>>

\vspace{-4pt}<<RELINE>>

Dear Hiring Manager,

<<BODY>>

\vspace{4pt}Sincerely,

\vspace{18pt}\textbf{<<NAME>>}

\end{document}
"""


def _build_cover_letter_latex(job: Job, personal: PersonalInfo | None) -> str:
    """Build a LaTeX cover letter document for compilation by Tectonic.
    Header identity (name, email, phone, links) comes from the requesting user's
    own profile — never hardcoded, since every user's cover letter carries their own.
    """
    date_str = datetime.date.today().strftime("%B %d, %Y")

    name = _escape_latex(personal.name) if personal and personal.name else "Applicant"

    contact_parts: list[str] = []
    if personal and personal.email:
        contact_parts.append(
            rf"\href{{mailto:{personal.email}}}{{\faEnvelope\enspace {_escape_latex(personal.email)}}}"
        )
    if personal and personal.phone:
        phone_digits = re.sub(r'[^\d+]', '', personal.phone)
        contact_parts.append(
            rf"\href{{tel:{phone_digits}}}{{\faPhone\enspace {_escape_latex(personal.phone)}}}"
        )
    if personal and personal.linkedin:
        linkedin_url = personal.linkedin if personal.linkedin.startswith("http") else f"https://{personal.linkedin}"
        contact_parts.append(
            rf"\href{{{linkedin_url}}}{{\faLinkedin\enspace {_escape_latex(personal.linkedin)}}}"
        )
    if personal and personal.github:
        github_url = personal.github if personal.github.startswith("http") else f"https://{personal.github}"
        contact_parts.append(
            rf"\href{{{github_url}}}{{\faGithub\enspace {_escape_latex(personal.github)}}}"
        )
    contact_line = r"\hspace{10pt}".join(contact_parts)

    re_parts: list[str] = []
    if job.title:
        re_parts.append(_escape_latex(job.title))
    if job.company:
        re_parts.append(_escape_latex(job.company))
    re_line = (r"\textit{Re:\ " + " -- ".join(re_parts) + "}") if re_parts else ""

    paragraphs = [
        _escape_latex(p.strip())
        for p in (job.cover_letter or "").split("\n\n")
        if p.strip()
    ]
    body = "\n\n".join(paragraphs)

    return (
        _COVER_LETTER_LATEX
        .replace("<<NAME>>", name)
        .replace("<<CONTACT>>", contact_line)
        .replace("<<DATE>>", date_str)
        .replace("<<RELINE>>", re_line)
        .replace("<<BODY>>", body)
    )


# ── Routes ────────────────────────────────────────────────────────────────────

async def _has_active_generation(db: AsyncSession, user_id) -> bool:
    """Per-user concurrency limit (Phase 5) — one active generation at a time, to
    avoid two concurrent runs racing on the same profile/session state."""
    existing = (
        await db.execute(select(Job.id).where(Job.user_id == user_id, Job.status == "processing").limit(1))
    ).scalar_one_or_none()
    return existing is not None


# ── Guardrails (Phase 7) ────────────────────────────────────────────────────
#
# Counted in Redis via the existing ARQ pool connection (ArqRedis subclasses
# redis.asyncio.Redis, so plain get/incr/expire work directly on it) rather
# than a new DB column — a `Job` row isn't created on every generation attempt
# (regenerate reuses the existing row), so counting Job rows would undercount
# actual Anthropic calls.

def _daily_cap_key(user_id) -> str:
    return f"daily_gen_count:{user_id}"


def _velocity_key(user_id) -> str:
    return f"gen_velocity:{user_id}"


async def _daily_generation_count(pool, user_id) -> int:
    """Per-user daily generation cap — protects a user whose leaked API key is
    being drained through CareerOS, and protects this app's own infra from
    runaway load. Rolling 24h window (not calendar day), so it can't be reset
    by waiting for midnight UTC."""
    value = await pool.get(_daily_cap_key(user_id))
    return int(value) if value else 0


async def _record_generation(pool, user_id) -> None:
    """Called once a generation attempt has actually passed every other gate
    and been enqueued — increments both the daily cap counter (24h TTL) and
    the velocity counter (10min TTL), logging a structured anomaly warning the
    moment the velocity counter first crosses the threshold. Anomaly detection
    only logs; it never blocks — the daily cap above is the actual hard limit.
    """
    daily_key = _daily_cap_key(user_id)
    daily_count = await pool.incr(daily_key)
    if daily_count == 1:
        await pool.expire(daily_key, 24 * 3600)

    velocity_key = _velocity_key(user_id)
    velocity_count = await pool.incr(velocity_key)
    if velocity_count == 1:
        await pool.expire(velocity_key, 600)
    if velocity_count == settings.velocity_anomaly_threshold:
        logger.warning(
            "Generation velocity anomaly: user exceeded threshold",
            extra={
                "user_id": str(user_id),
                "anomaly": "generation_velocity",
                "count": velocity_count,
                "window_seconds": 600,
            },
        )


@router.post("/generate", response_model=JobRead, status_code=201)
@limiter.limit("30/hour")
async def generate_job(
    request: Request,
    body: JobGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create the job record immediately (status=processing), enqueue generation
    on the ARQ worker (runs in a separate process — survives an API redeploy)."""
    if not await get_decrypted_key(db, current_user.id):
        raise HTTPException(status_code=400, detail="Add your Anthropic API key in Settings before generating.")
    if await _has_active_generation(db, current_user.id):
        raise HTTPException(status_code=409, detail="A generation is already in progress. Wait for it to finish before starting another.")
    pool = request.app.state.arq_pool
    if await _daily_generation_count(pool, current_user.id) >= settings.daily_generation_limit:
        raise HTTPException(status_code=429, detail=f"Daily generation limit reached ({settings.daily_generation_limit}/24h). Try again later.")

    job = Job(
        user_id=current_user.id,
        description=body.description,
        url=body.url or None,
        title="Generating…",
        status="processing",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await pool.enqueue_job("run_generation_job", job.id, body.description, str(current_user.id))
    await _record_generation(pool, current_user.id)
    return job


@router.post("/{id}/regenerate", response_model=JobRead)
@limiter.limit("30/hour")
async def regenerate_job(
    request: Request,
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    if not job.description:
        raise HTTPException(status_code=400, detail="No JD stored for this job")
    if not await get_decrypted_key(db, current_user.id):
        raise HTTPException(status_code=400, detail="Add your Anthropic API key in Settings before generating.")
    if await _has_active_generation(db, current_user.id):
        raise HTTPException(status_code=409, detail="A generation is already in progress. Wait for it to finish before starting another.")
    pool = request.app.state.arq_pool
    if await _daily_generation_count(pool, current_user.id) >= settings.daily_generation_limit:
        raise HTTPException(status_code=429, detail=f"Daily generation limit reached ({settings.daily_generation_limit}/24h). Try again later.")

    job.status = "processing"
    await db.commit()
    await db.refresh(job)

    await pool.enqueue_job("run_generation_job", job.id, job.description, str(current_user.id))
    await _record_generation(pool, current_user.id)
    return job


@router.get("/{id}/resume.pdf")
async def download_resume_pdf(
    id: int,
    first_page: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job or not job.resume_latex:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        pdf_bytes = await get_pdf_storage().load(resume_pdf_key(job.id))
        if pdf_bytes is None:
            pdf_bytes = await cache_resume_pdf(job.id, job.resume_latex)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="PDF compilation not available")
    except RuntimeError:
        logger.exception("Resume PDF compilation failed for job %d", id)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    if first_page:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        writer.add_page(reader.pages[0])
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

    filename = f"resume-{_safe_filename(job.company or 'company')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/{id}/resume-preview.pdf")
async def preview_resume_pdf(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Serve resume PDF inline — for browser embedding, not forced download."""
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job or not job.resume_latex:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        pdf_bytes = await get_pdf_storage().load(resume_pdf_key(job.id))
        if pdf_bytes is None:
            pdf_bytes = await cache_resume_pdf(job.id, job.resume_latex)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="PDF compilation not available")
    except RuntimeError:
        logger.exception("Resume preview compilation failed for job %d", id)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@router.patch("/{id}/cover-letter", response_model=JobRead)
async def update_cover_letter(
    id: int,
    body: CoverLetterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist an edited cover letter. Invalidates the cached PDF (Phase 5) so the
    download endpoint recompiles from the updated text instead of serving stale bytes."""
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    job.cover_letter = body.cover_letter
    await db.commit()
    await db.refresh(job)
    await invalidate_cover_letter_pdf(job.id)
    return job


@router.get("/{id}/cover-letter.pdf")
async def download_cover_letter(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job or not job.cover_letter:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    try:
        pdf_bytes = await get_pdf_storage().load(cover_letter_pdf_key(job.id))
        if pdf_bytes is None:
            personal = (
                await db.execute(select(PersonalInfo).where(PersonalInfo.user_id == current_user.id).limit(1))
            ).scalar_one_or_none()
            latex = _build_cover_letter_latex(job, personal)
            pdf_bytes = await cache_cover_letter_pdf(job.id, latex)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="PDF compilation not available")
    except RuntimeError:
        logger.exception("Cover letter PDF compilation failed for job %d", id)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    filename = f"cover-letter-{_safe_filename(job.company or 'company')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/insights", response_model=CandidacyInsightsRead)
@limiter.limit("20/hour")
async def get_candidacy_insights(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a synthesized candidacy observation derived from recent applications."""
    completed_statuses = ("generated", "applied", "interview", "offer", "skipped")

    # True total drives the "3+ applications" gate and the count shown to the user —
    # kept separate from how many notes actually get sent to the model below, so
    # someone with 30+ applications still sees their real total, not the capped
    # sample size.
    count = (await db.execute(
        select(func.count()).select_from(Job)
        .where(Job.user_id == current_user.id, Job.status.in_(completed_statuses))
    )).scalar_one()
    if count < 3:
        return CandidacyInsightsRead(observation=None, count=count)

    api_key = await get_decrypted_key(db, current_user.id)
    if not api_key:
        # Insights is an automatic background fetch, not a user-initiated action —
        # fail quietly the same way "not enough applications yet" does, rather than
        # surfacing a hard error for something the user didn't explicitly trigger.
        return CandidacyInsightsRead(observation=None, count=count)

    # A genuinely repeated gap shows up just as reliably in the most recent dozen
    # applications as in the full history — capped here to limit how much of the
    # per-note text (see _extract_gaps) gets sent, not to change what the user sees.
    jobs = (await db.execute(
        select(Job)
        .where(Job.user_id == current_user.id, Job.status.in_(completed_statuses))
        .order_by(Job.created_at.desc())
        .limit(12)
    )).scalars().all()

    summaries = [
        {
            "title": j.title,
            "company": j.company,
            "strategic_note": j.strategic_note,
            "description_snippet": (j.description or "")[:400] if not j.strategic_note else None,
        }
        for j in jobs
    ]

    skill_categories = (await db.execute(
        select(SkillCategory).where(SkillCategory.user_id == current_user.id).order_by(SkillCategory.sort_order)
    )).scalars().all()
    experiences = (await db.execute(
        select(Experience).where(Experience.user_id == current_user.id).order_by(Experience.sort_order)
    )).scalars().all()
    projects = (await db.execute(
        select(Project).where(Project.user_id == current_user.id).order_by(Project.sort_order)
    )).scalars().all()

    profile_lines: list[str] = []
    if experiences:
        profile_lines.append("Experience:")
        for e in experiences:
            line = f"- {e.role} at {e.company}"
            if e.description:
                line += f": {e.description}"
            profile_lines.append(line)
    if projects:
        profile_lines.append("Projects:")
        for p in projects:
            line = f"- {p.name}"
            if p.description:
                line += f": {p.description}"
            profile_lines.append(line)
    if skill_categories:
        profile_lines.append("Skills:")
        for cat in skill_categories:
            if cat.items:
                profile_lines.append(f"- {cat.category}: {', '.join(cat.items)}")
    profile_context = "\n".join(profile_lines) if profile_lines else None

    result = await generate_insights(summaries, api_key, profile_context=profile_context)
    return CandidacyInsightsRead(
        headline=result.get("headline"),
        observed=result.get("observed"),
        gap=result.get("gap"),
        action=result.get("action"),
        count=count,
    )


@router.delete("/{id}", status_code=204)
async def delete_job(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single job record and all its generated content."""
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(job)
    await db.commit()
    storage = get_pdf_storage()
    await storage.delete(resume_pdf_key(id))
    await storage.delete(cover_letter_pdf_key(id))


@router.get("", response_model=list[JobListRead])
async def list_jobs(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Job).where(Job.user_id == current_user.id).order_by(Job.created_at.desc())
    if status:
        q = q.where(Job.status == status)
    return (await db.execute(q)).scalars().all()


@router.get("/{id}", response_model=JobRead)
async def get_job(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    return job


@router.patch("/{id}/status", response_model=JobRead)
async def update_status(
    id: int,
    body: StatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update job status. Status is validated by Pydantic pattern, not a query string."""
    job = (
        await db.execute(select(Job).where(Job.id == id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    job.status = body.status
    await db.commit()
    await db.refresh(job)
    return job
