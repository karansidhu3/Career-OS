from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job
from app.schemas.job import JobGenerateRequest, JobRead
from app.services.generation import generate_materials

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/generate", response_model=JobRead, status_code=201)
async def generate_job(body: JobGenerateRequest, db: AsyncSession = Depends(get_db)):
    result = await generate_materials(db, body.description)

    job = Job(
        title=body.title or "Untitled Role",
        company=body.company or None,
        description=body.description,
        url=body.url or None,
        status="generated",
        fit_score=result["fit_score"],
        fit_rationale=result["fit_rationale"],
        resume_latex=result["resume_latex"],
        cover_letter=result["cover_letter"],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


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
