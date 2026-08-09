import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from slowapi import Limiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import get_current_user
from app.database import get_db
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.models.user import User
from app.rate_limit import limiter_key
from app.schemas.profile import (
    EducationBase,
    EducationRead,
    ExperienceBase,
    ExperienceRead,
    FullProfile,
    PersonalInfoBase,
    PersonalInfoRead,
    ProjectBase,
    ProjectRead,
    SkillCategoryBase,
    SkillCategoryRead,
)
from app.schemas.profile_import import ProfileImportDraft
from app.services.credentials import get_decrypted_key
from app.services.generation import compile_template_preview
from app.services.resume_import import extract_profile_draft, extract_text_from_docx, extract_text_from_pdf

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=limiter_key)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=FullProfile)
async def get_full_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    personal = (
        await db.execute(select(PersonalInfo).where(PersonalInfo.user_id == current_user.id).limit(1))
    ).scalar_one_or_none()
    education = (
        await db.execute(
            select(Education).where(Education.user_id == current_user.id, Education.deleted_at.is_(None))
        )
    ).scalars().all()
    experience = (
        await db.execute(
            select(Experience)
            .where(Experience.user_id == current_user.id, Experience.deleted_at.is_(None))
            .order_by(Experience.sort_order)
        )
    ).scalars().all()
    projects = (
        await db.execute(
            select(Project)
            .where(Project.user_id == current_user.id, Project.deleted_at.is_(None))
            .order_by(Project.sort_order)
        )
    ).scalars().all()
    skills = (
        await db.execute(
            select(SkillCategory)
            .where(SkillCategory.user_id == current_user.id, SkillCategory.deleted_at.is_(None))
            .order_by(SkillCategory.sort_order)
        )
    ).scalars().all()
    return FullProfile(
        personal=personal,
        education=list(education),
        experience=list(experience),
        projects=list(projects),
        skills=list(skills),
    )


# --- Personal info (one row per user) ---

@router.get("/personal", response_model=PersonalInfoRead)
async def get_personal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(PersonalInfo).where(PersonalInfo.user_id == current_user.id).limit(1))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="No personal info found")
    return row


@router.put("/personal", response_model=PersonalInfoRead)
async def upsert_personal(
    body: PersonalInfoBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(PersonalInfo).where(PersonalInfo.user_id == current_user.id).limit(1))
    ).scalar_one_or_none()
    if row:
        for k, v in body.model_dump().items():
            setattr(row, k, v)
    else:
        row = PersonalInfo(user_id=current_user.id, **body.model_dump())
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# --- Template previews ---

VALID_TEMPLATES = {"jake", "crisp", "modern", "sharp", "classic", "minimal"}


@router.get("/template-preview/{template}")
async def get_template_preview(
    template: str,
    current_user: User = Depends(get_current_user),
) -> Response:
    if template not in VALID_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown template '{template}'. Valid: {sorted(VALID_TEMPLATES)}")
    try:
        pdf = await compile_template_preview(template)
    except Exception as exc:
        logger.exception("Template preview compile failed for %s", template)
        raise HTTPException(status_code=500, detail=str(exc))
    return Response(content=pdf, media_type="application/pdf")


class CustomPreambleBody(BaseModel):
    preamble: str


@router.post("/template-preview/custom")
async def preview_custom_template(
    body: CustomPreambleBody,
    current_user: User = Depends(get_current_user),
) -> Response:
    if not body.preamble.strip():
        raise HTTPException(status_code=400, detail="Preamble cannot be empty")
    try:
        pdf = await compile_template_preview("custom", custom_preamble=body.preamble)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Custom template preview compile failed")
        raise HTTPException(status_code=422, detail=f"LaTeX compile error: {exc}")
    return Response(content=pdf, media_type="application/pdf")


# --- Education ---

@router.get("/education", response_model=list[EducationRead])
async def list_education(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(Education).where(Education.user_id == current_user.id, Education.deleted_at.is_(None))
        )
    ).scalars().all()


@router.post("/education", response_model=EducationRead, status_code=201)
async def create_education(
    body: EducationBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = Education(user_id=current_user.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.put("/education/{id}", response_model=EducationRead)
async def update_education(
    id: int,
    body: EducationBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Education).where(Education.id == id, Education.user_id == current_user.id, Education.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/education/{id}", status_code=204)
async def delete_education(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete (Phase 6) — sets deleted_at rather than removing the row, so
    it's recoverable via POST .../restore. Career history is the most
    irreplaceable data in the product."""
    row = (
        await db.execute(
            select(Education).where(Education.id == id, Education.user_id == current_user.id, Education.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/education/{id}/restore", response_model=EducationRead)
async def restore_education(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Education).where(Education.id == id, Education.user_id == current_user.id, Education.deleted_at.is_not(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = None
    await db.commit()
    await db.refresh(row)
    return row


# --- Experience ---

@router.get("/experience", response_model=list[ExperienceRead])
async def list_experience(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(Experience)
            .where(Experience.user_id == current_user.id, Experience.deleted_at.is_(None))
            .order_by(Experience.sort_order)
        )
    ).scalars().all()


@router.post("/experience", response_model=ExperienceRead, status_code=201)
async def create_experience(
    body: ExperienceBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = Experience(user_id=current_user.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.put("/experience/{id}", response_model=ExperienceRead)
async def update_experience(
    id: int,
    body: ExperienceBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Experience).where(Experience.id == id, Experience.user_id == current_user.id, Experience.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/experience/{id}", status_code=204)
async def delete_experience(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Experience).where(Experience.id == id, Experience.user_id == current_user.id, Experience.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/experience/{id}/restore", response_model=ExperienceRead)
async def restore_experience(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Experience).where(Experience.id == id, Experience.user_id == current_user.id, Experience.deleted_at.is_not(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = None
    await db.commit()
    await db.refresh(row)
    return row


# --- Projects ---

@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(Project)
            .where(Project.user_id == current_user.id, Project.deleted_at.is_(None))
            .order_by(Project.sort_order)
        )
    ).scalars().all()


@router.post("/projects", response_model=ProjectRead, status_code=201)
async def create_project(
    body: ProjectBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = Project(user_id=current_user.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.put("/projects/{id}", response_model=ProjectRead)
async def update_project(
    id: int,
    body: ProjectBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Project).where(Project.id == id, Project.user_id == current_user.id, Project.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/projects/{id}", status_code=204)
async def delete_project(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Project).where(Project.id == id, Project.user_id == current_user.id, Project.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/projects/{id}/restore", response_model=ProjectRead)
async def restore_project(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(Project).where(Project.id == id, Project.user_id == current_user.id, Project.deleted_at.is_not(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = None
    await db.commit()
    await db.refresh(row)
    return row


# --- Skills ---

@router.get("/skills", response_model=list[SkillCategoryRead])
async def list_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(SkillCategory)
            .where(SkillCategory.user_id == current_user.id, SkillCategory.deleted_at.is_(None))
            .order_by(SkillCategory.sort_order)
        )
    ).scalars().all()


@router.post("/skills", response_model=SkillCategoryRead, status_code=201)
async def create_skill_category(
    body: SkillCategoryBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = SkillCategory(user_id=current_user.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.put("/skills/{id}", response_model=SkillCategoryRead)
async def update_skill_category(
    id: int,
    body: SkillCategoryBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(SkillCategory).where(SkillCategory.id == id, SkillCategory.user_id == current_user.id, SkillCategory.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/skills/{id}", status_code=204)
async def delete_skill_category(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(SkillCategory).where(SkillCategory.id == id, SkillCategory.user_id == current_user.id, SkillCategory.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/skills/{id}/restore", response_model=SkillCategoryRead)
async def restore_skill_category(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(SkillCategory).where(SkillCategory.id == id, SkillCategory.user_id == current_user.id, SkillCategory.deleted_at.is_not(None))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    row.deleted_at = None
    await db.commit()
    await db.refresh(row)
    return row


# --- Resume import (Phase 4) ---

_SUPPORTED_EXTENSIONS = (".pdf", ".docx")
# A real resume file is never anywhere close to this — this is a resource-exhaustion
# guard for the raw upload (separate from resume_import's own zip-bomb check on the
# DOCX's *uncompressed* content), since nothing else caps this today.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.post("/import", response_model=ProfileImportDraft)
@limiter.limit("10/hour")
async def import_resume(
    request: Request,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract a structured profile draft from an uploaded resume (PDF/DOCX) or
    pasted text. Returns the draft for the frontend to show for review/edit —
    nothing is written to the profile tables here. Billed to the requesting
    user's own key; requires one to already be on file (Phase 3 gate).
    """
    api_key = await get_decrypted_key(db, current_user.id)
    if not api_key:
        raise HTTPException(status_code=400, detail="Add your Anthropic API key in Settings before importing a resume.")

    if file is not None:
        filename = (file.filename or "").lower()
        if not filename.endswith(_SUPPORTED_EXTENSIONS):
            raise HTTPException(status_code=400, detail="Unsupported file type — upload a PDF or DOCX.")
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File is too large — resumes should be under 5MB.")
        try:
            resume_text = extract_text_from_docx(data) if filename.endswith(".docx") else extract_text_from_pdf(data)
        except Exception:
            logger.exception("Failed to extract text from uploaded resume")
            raise HTTPException(status_code=400, detail="Could not read this file. Try pasting the text directly.")
    elif text:
        resume_text = text
    else:
        raise HTTPException(status_code=400, detail="Provide a resume file or pasted text.")

    try:
        draft = await extract_profile_draft(resume_text, api_key, db=db, user_id=current_user.id)
        await db.commit()
        return draft
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Resume import extraction failed")
        raise HTTPException(status_code=502, detail="Could not extract profile data from this resume. Try pasting the text directly.")
