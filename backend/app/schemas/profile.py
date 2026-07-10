from typing import Optional
from pydantic import BaseModel, Field


class PersonalInfoBase(BaseModel):
    name: str = Field(..., max_length=200)
    email: str = Field(..., max_length=254)
    phone: Optional[str] = Field(None, max_length=50)
    linkedin: Optional[str] = Field(None, max_length=200)
    github: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    target_roles: list[str] = []
    target_locations: list[str] = []
    # Stored up to 2000 chars; truncated to 800 when injected into Claude prompts
    cover_letter_voice: str = Field("", max_length=2000)
    resume_template: Optional[str] = Field(None, max_length=32)
    custom_preamble: Optional[str] = Field(None, max_length=20_000)


class PersonalInfoRead(PersonalInfoBase):
    id: int
    model_config = {"from_attributes": True}


class EducationBase(BaseModel):
    school: str = Field(..., max_length=200)
    degree: str = Field(..., max_length=200)
    field: Optional[str] = Field(None, max_length=200)
    minor: Optional[str] = Field(None, max_length=200)
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)


class EducationRead(EducationBase):
    id: int
    model_config = {"from_attributes": True}


class ExperienceBase(BaseModel):
    company: str = Field(..., max_length=200)
    role: str = Field(..., max_length=200)
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=200)
    # Stored up to 10000 chars; Claude prompt context uses this verbatim so keep it focused
    description: str = Field("", max_length=10_000)
    sort_order: int = Field(0, ge=0, le=9999)


class ExperienceRead(ExperienceBase):
    id: int
    model_config = {"from_attributes": True}


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=200)
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)
    github_url: Optional[str] = Field(None, max_length=500)
    # Stored up to 10000 chars; Claude prompt context uses this verbatim so keep it focused
    description: str = Field("", max_length=10_000)
    sort_order: int = Field(0, ge=0, le=9999)


class ProjectRead(ProjectBase):
    id: int
    model_config = {"from_attributes": True}


class SkillCategoryBase(BaseModel):
    category: str = Field(..., max_length=100)
    items: list[str] = Field([], max_length=50)  # max 50 items per category
    sort_order: int = Field(0, ge=0, le=9999)


class SkillCategoryRead(SkillCategoryBase):
    id: int
    model_config = {"from_attributes": True}


class FullProfile(BaseModel):
    personal: Optional[PersonalInfoRead] = None
    education: list[EducationRead] = []
    experience: list[ExperienceRead] = []
    projects: list[ProjectRead] = []
    skills: list[SkillCategoryRead] = []
