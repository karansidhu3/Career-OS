from typing import Optional
from pydantic import BaseModel


class PersonalInfoBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None
    target_roles: list[str] = []
    target_locations: list[str] = []


class PersonalInfoRead(PersonalInfoBase):
    id: int
    model_config = {"from_attributes": True}


class EducationBase(BaseModel):
    school: str
    degree: str
    field: Optional[str] = None
    minor: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class EducationRead(EducationBase):
    id: int
    model_config = {"from_attributes": True}


class ExperienceBase(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: list[str] = []
    sort_order: int = 0


class ExperienceRead(ExperienceBase):
    id: int
    model_config = {"from_attributes": True}


class ProjectBase(BaseModel):
    name: str
    tech: list[str] = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: list[str] = []
    sort_order: int = 0


class ProjectRead(ProjectBase):
    id: int
    model_config = {"from_attributes": True}


class SkillCategoryBase(BaseModel):
    category: str
    items: list[str] = []
    sort_order: int = 0


class SkillCategoryRead(SkillCategoryBase):
    id: int
    model_config = {"from_attributes": True}


class FullProfile(BaseModel):
    personal: Optional[PersonalInfoRead] = None
    education: list[EducationRead] = []
    experience: list[ExperienceRead] = []
    projects: list[ProjectRead] = []
    skills: list[SkillCategoryRead] = []
