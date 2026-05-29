import asyncio
import datetime

from fpdf import FPDF
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models.job import Job
from app.schemas.job import CandidacyInsightsRead, JobGenerateRequest, JobRead
from app.services.generation import generate_insights, generate_materials
from app.services.pdf import compile_latex_to_pdf

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _apply_result(job: Job, result: dict) -> None:
    """Write generation result dict onto a Job instance."""
    job.title = result.get("job_title") or "Untitled Role"
    job.company = result.get("job_company") or None
    job.fit_score = result["fit_score"]
    job.fit_rationale = result["fit_rationale"]
    job.resume_latex = result["resume_latex"]
    job.cover_letter = result["cover_letter"]
    job.strategic_note = result.get("strategic_note") or None
    job.input_tokens = result.get("input_tokens")
    job.output_tokens = result.get("output_tokens")
    job.cache_read_tokens = result.get("cache_read_tokens")
    job.cache_write_tokens = result.get("cache_write_tokens")


async def _run_generation(job_id: int, jd_text: str) -> None:
    """Background task: call Claude, write results to DB. No HTTP proxy timeout concern here."""
    async with AsyncSessionLocal() as db:
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
        if not job:
            return
        try:
            result = await generate_materials(db, jd_text)
            _apply_result(job, result)
            job.status = "generated"
        except Exception as exc:
            # Mark as failed so the UI can show a retry
            job.status = "failed"
            job.title = job.title if job.title != "Generating…" else "Generation failed"
        finally:
            await db.commit()


def _to_latin1(text: str) -> str:
    """
    Replace common Unicode typographic characters with ASCII equivalents so
    fpdf2's built-in Helvetica (latin-1 only) doesn't crash.
    Any character still outside latin-1 after replacements is dropped.
    """
    return (
        text
        .replace('—', '--')    # em dash  —
        .replace('–', '-')     # en dash  –
        .replace('‘', "'")     # left single quote  '
        .replace('’', "'")     # right single quote  '
        .replace('“', '"')     # left double quote  "
        .replace('”', '"')     # right double quote  "
        .replace('…', '...')   # ellipsis  …
        .replace(' ', ' ')     # non-breaking space
        .encode('latin-1', errors='ignore').decode('latin-1')
    )


def _build_cover_letter_pdf(job: Job) -> bytes:
    pdf = FPDF()
    pdf.set_margins(28, 28, 28)
    pdf.add_page()

    # ── Header: name ──────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 10, "Karanveer Sidhu", new_x="LMARGIN", new_y="NEXT")

    # Contact line
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(
        0, 5,
        "karansidhu5550@gmail.com  |  +1 (250) 509-2500  |  linkedin.com/in/karan-sidhu3  |  github.com/karansidhu3",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(3)
    pdf.set_draw_color(190, 190, 190)
    pdf.line(28, pdf.get_y(), 182, pdf.get_y())
    pdf.ln(10)

    # ── Date ──────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    date_str = datetime.date.today().strftime("%B %d, %Y")
    pdf.cell(0, 6, date_str, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(7)

    # ── Re: line ──────────────────────────────────────────────────────
    if job.title or job.company:
        re_parts = []
        if job.title:
            re_parts.append(_to_latin1(job.title))
        if job.company:
            re_parts.append(_to_latin1(job.company))
        re_line = "Re: " + " -- ".join(re_parts)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 6, re_line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(7)

    # ── Salutation ────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 6, "Dear Hiring Manager,", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Body paragraphs (justified) ───────────────────────────────────
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    paragraphs = [p.strip() for p in (job.cover_letter or "").split("\n\n") if p.strip()]
    for para in paragraphs:
        pdf.multi_cell(0, 6.5, _to_latin1(para), align="J")
        pdf.ln(5)

    # ── Closing ───────────────────────────────────────────────────────
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 6, "Sincerely,", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Karanveer Sidhu", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


@router.post("/generate", response_model=JobRead, status_code=201)
async def generate_job(
    body: JobGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create the job record immediately (status=processing), kick off generation in the background."""
    job = Job(
        description=body.description,
        url=body.url or None,
        title="Generating…",
        status="processing",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_run_generation, job.id, body.description)
    return job


@router.post("/{id}/regenerate", response_model=JobRead)
async def regenerate_job(
    id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    job = (await db.execute(select(Job).where(Job.id == id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    if not job.description:
        raise HTTPException(status_code=400, detail="No JD stored for this job")

    job.status = "processing"
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_run_generation, job.id, job.description)
    return job


@router.get("/{id}/resume.pdf")
async def download_resume_pdf(id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(Job).where(Job.id == id))).scalar_one_or_none()
    if not job or not job.resume_latex:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        pdf_bytes = await compile_latex_to_pdf(job.resume_latex)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="PDF compilation not available (tectonic not installed on this server)",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    company = (job.company or "company").replace(" ", "-").lower()
    filename = f"resume-{company}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{id}/cover-letter.pdf")
async def download_cover_letter(id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(Job).where(Job.id == id))).scalar_one_or_none()
    if not job or not job.cover_letter:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    pdf_bytes = _build_cover_letter_pdf(job)
    company = (job.company or "company").replace(" ", "-").lower()
    filename = f"cover-letter-{company}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/insights", response_model=CandidacyInsightsRead)
async def get_candidacy_insights(db: AsyncSession = Depends(get_db)):
    """Return a synthesized candidacy observation derived from all past applications."""
    completed_statuses = ("generated", "applied", "interview", "offer", "skipped")
    jobs = (await db.execute(
        select(Job)
        .where(Job.status.in_(completed_statuses))
        .order_by(Job.created_at.desc())
        .limit(20)
    )).scalars().all()

    count = len(jobs)
    if count < 3:
        return CandidacyInsightsRead(observation=None, count=count)

    summaries = [
        {
            "title": j.title,
            "company": j.company,
            "strategic_note": j.strategic_note,
            "description_snippet": (j.description or "")[:400] if not j.strategic_note else None,
        }
        for j in jobs
    ]

    result = await generate_insights(summaries)
    return CandidacyInsightsRead(
        headline=result.get("headline"),
        observation=result.get("observation"),
        count=count,
    )


@router.get("", response_model=list[JobRead])
async def list_jobs(status: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Job).order_by(Job.created_at.desc())
    if status:
        q = q.where(Job.status == status)
    return (await db.execute(q)).scalars().all()


@router.get("/{id}", response_model=JobRead)
async def get_job(id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(Job).where(Job.id == id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    return job


@router.patch("/{id}/status", response_model=JobRead)
async def update_status(id: int, status: str, db: AsyncSession = Depends(get_db)):
    if status not in {"generated", "applied", "skipped", "interview", "offer"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    job = (await db.execute(select(Job).where(Job.id == id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    job.status = status
    await db.commit()
    await db.refresh(job)
    return job
