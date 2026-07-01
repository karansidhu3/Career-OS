from typing import Optional
from pydantic import BaseModel


class ImportedPersonal(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None


class ImportedEducation(BaseModel):
    school: str
    degree: str
    field: Optional[str] = None
    minor: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ImportedExperience(BaseModel):
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    description: str = ""


class ImportedProject(BaseModel):
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    github_url: Optional[str] = None
    description: str = ""


class ImportedSkillCategory(BaseModel):
    category: str
    items: list[str] = []


class ProfileImportDraft(BaseModel):
    """Extracted from a resume, never written to the DB directly — the frontend
    shows this for review/edit before the user accepts any of it."""
    personal: ImportedPersonal
    education: list[ImportedEducation] = []
    experience: list[ImportedExperience] = []
    projects: list[ImportedProject] = []
    skills: list[ImportedSkillCategory] = []
