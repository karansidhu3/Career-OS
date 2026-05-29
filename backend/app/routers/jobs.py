import asyncio
import datetime

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
        except Exception:
            job.status = "failed"
            job.title = job.title if job.title != "Generating…" else "Generation failed"
        finally:
            await db.commit()


# ── Cover letter LaTeX builder ────────────────────────────────────────────────

def _escape_latex(text: str) -> str:
    """Escape plain text content for use inside a LaTeX document body."""
    return (
        text
        .replace("—", "---")      # em dash
        .replace("–", "--")       # en dash
        .replace("‘", "'")        # left single quote
        .replace("’", "'")        # right single quote
        .replace("“", "``")       # left double quote
        .replace("”", "''")       # right double quote
        .replace("…", "...")      # ellipsis
        .replace(" ", " ")        # non-breaking space
        .replace("%",  r"\%")
        .replace("&",  r"\&")
        .replace("$",  r"\$")
        .replace("#",  r"\#")
        .replace("_",  r"\_")
    )


# LaTeX cover letter template.
# Uses charter font, eso-pic gray header band, fontawesome5 contact icons.
# Placeholders: <<DATE>>, <<RELINE>>, <<BODY>>
_COVER_LETTER_LATEX = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{charter}
\usepackage[left=0.85in, right=0.85in, top=0.5in, bottom=0.85in]{geometry}
\usepackage{fontawesome5}
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
{\fontsize{26}{30}\selectfont\scshape Karanveer Sidhu}\\[5pt]
{\small\color[RGB]{80,80,80}
  \href{mailto:karansidhu5550@gmail.com}{\faEnvelope\enspace karansidhu5550@gmail.com}\hspace{10pt}%
  \href{tel:+12505092500}{\faPhone\enspace +1 (250) 509-2500}\hspace{10pt}%
  \href{https://linkedin.com/in/karan-sidhu3}{\faLinkedinIn\enspace linkedin.com/in/karan-sidhu3}\hspace{10pt}%
  \href{https://github.com/karansidhu3}{\faGithub\enspace github.com/karansidhu3}%
}
\end{center}
\vspace*{0.18in}

<<DATE>>

\vspace{-4pt}<<RELINE>>

Dear Hiring Manager,

<<BODY>>

\vspace{4pt}Sincerely,

\vspace{18pt}\textbf{Karanveer Sidhu}

\end{document}
"""


def _build_cover_letter_latex(job: Job) -> str:
    """Build a LaTeX cover letter document for compilation by Tectonic."""
    date_str = datetime.date.today().strftime("%B %d, %Y")

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
        .replace("<<DATE>>", date_str)
        .replace("<<RELINE>>", re_line)
        .replace("<<BODY>>", body)
    )


# ── Routes ────────────────────────────────────────────────────────────────────

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

    try:
        latex = _build_cover_letter_latex(job)
        pdf_bytes = await compile_latex_to_pdf(latex)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="PDF compilation not available (tectonic not installed on this server)",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

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
