from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobGenerateRequest(BaseModel):
    description: str
    title: str = ""
    company: str = ""
    url: str = ""


class JobRead(BaseModel):
    id: int
    title: str
    company: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    status: str
    fit_score: Optional[int] = None
    fit_rationale: Optional[list[str]] = None
    resume_latex: Optional[str] = None
    cover_letter: Optional[str] = None

    model_config = {"from_attributes": True}
