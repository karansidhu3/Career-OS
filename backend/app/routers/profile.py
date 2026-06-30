from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clerk_auth import get_current_user
from app.database import get_db
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.models.user import User
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
        await db.execute(select(Education).where(Education.user_id == current_user.id))
    ).scalars().all()
    experience = (
        await db.execute(
            select(Experience).where(Experience.user_id == current_user.id).order_by(Experience.sort_order)
        )
    ).scalars().all()
    projects = (
        await db.execute(
            select(Project).where(Project.user_id == current_user.id).order_by(Project.sort_order)
        )
    ).scalars().all()
    skills = (
        await db.execute(
            select(SkillCategory).where(SkillCategory.user_id == current_user.id).order_by(SkillCategory.sort_order)
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


# --- Education ---

@router.get("/education", response_model=list[EducationRead])
async def list_education(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(select(Education).where(Education.user_id == current_user.id))
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
        await db.execute(select(Education).where(Education.id == id, Education.user_id == current_user.id))
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
    row = (
        await db.execute(select(Education).where(Education.id == id, Education.user_id == current_user.id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.commit()


# --- Experience ---

@router.get("/experience", response_model=list[ExperienceRead])
async def list_experience(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(Experience).where(Experience.user_id == current_user.id).order_by(Experience.sort_order)
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
        await db.execute(select(Experience).where(Experience.id == id, Experience.user_id == current_user.id))
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
        await db.execute(select(Experience).where(Experience.id == id, Experience.user_id == current_user.id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.commit()


# --- Projects ---

@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(Project).where(Project.user_id == current_user.id).order_by(Project.sort_order)
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
        await db.execute(select(Project).where(Project.id == id, Project.user_id == current_user.id))
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
        await db.execute(select(Project).where(Project.id == id, Project.user_id == current_user.id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.commit()


# --- Skills ---

@router.get("/skills", response_model=list[SkillCategoryRead])
async def list_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return (
        await db.execute(
            select(SkillCategory).where(SkillCategory.user_id == current_user.id).order_by(SkillCategory.sort_order)
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
        await db.execute(select(SkillCategory).where(SkillCategory.id == id, SkillCategory.user_id == current_user.id))
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
        await db.execute(select(SkillCategory).where(SkillCategory.id == id, SkillCategory.user_id == current_user.id))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(row)
    await db.commit()
