from fpdf import FPDF
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job
from app.schemas.job import JobGenerateRequest, JobRead
from app.services.generation import generate_materials

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _apply_result(job: Job, result: dict) -> None:
    """Write generation result dict onto a Job instance."""
    job.title = result.get("job_title") or "Untitled Role"
    job.company = result.get("job_company") or None
    job.fit_score = result["fit_score"]
    job.fit_rationale = result["fit_rationale"]
    job.resume_latex = result["resume_latex"]
    job.cover_letter = result["cover_letter"]
    job.input_tokens = result.get("input_tokens")
    job.output_tokens = result.get("output_tokens")
    job.cache_read_tokens = result.get("cache_read_tokens")
    job.cache_write_tokens = result.get("cache_write_tokens")


def _build_cover_letter_pdf(job: Job) -> bytes:
    pdf = FPDF()
    pdf.set_margins(25, 25, 25)
    pdf.add_page()

    # Name
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Karanveer Sidhu", new_x="LMARGIN", new_y="NEXT")

    # Contact
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(
        0, 6,
        "karansidhu5550@gmail.com  ·  +1 (250) 509-2500  ·  linkedin.com/in/karan-sidhu3  ·  github.com/karansidhu3",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)
    pdf.set_draw_color(210, 210, 210)
    pdf.line(25, pdf.get_y(), 185, pdf.get_y())
    pdf.ln(8)

    # Role / company
    if job.title or job.company:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 0, 0)
        header = job.title or ""
        if job.company:
            header += f" — {job.company}"
        pdf.cell(0, 8, header, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Body
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    paragraphs = [p.strip() for p in (job.cover_letter or "").split("\n\n") if p.strip()]
    for para in paragraphs:
        pdf.multi_cell(0, 6, para)
        pdf.ln(5)

    return bytes(pdf.output())


@router.post("/generate", response_model=JobRead, status_code=201)
async def generate_job(body: JobGenerateRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await generate_materials(db, body.description)
    except ValueError as e:
        raise HTTPException(status_code=504, detail=str(e))

    job = Job(
        description=body.description,
        url=body.url or None,
        status="generated",
    )
    _apply_result(job, result)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{id}/regenerate", response_model=JobRead)
async def regenerate_job(id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(Job).where(Job.id == id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    if not job.description:
        raise HTTPException(status_code=400, detail="No JD stored for this job")

    try:
        result = await generate_materials(db, job.description)
    except ValueError as e:
        raise HTTPException(status_code=504, detail=str(e))
    _apply_result(job, result)
    job.status = "generated"
    await db.commit()
    await db.refresh(job)
    return job


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
    if status not in {"generated", "applied", "skipped"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    job = (await db.execute(select(Job).where(Job.id == id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
    job.status = status
    await db.commit()
    await db.refresh(job)
    return job
