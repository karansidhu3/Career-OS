from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class JobGenerateRequest(BaseModel):
    description: str = Field(..., min_length=10, max_length=50_000)
    url: str = Field("", max_length=2_048)


class CoverLetterUpdate(BaseModel):
    cover_letter: str = Field(..., min_length=1, max_length=10_000)


class StatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(generated|applied|skipped|interview|offer)$")


class JobListRead(BaseModel):
    """Lightweight projection for list endpoints — omits large fields."""
    id: int
    title: str
    company: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    status: str
    fit_score: Optional[int] = None
    strategic_note: Optional[str] = None
    selected_projects: Optional[list[str]] = None
    compression_attempts: Optional[int] = None
    generation_version: Optional[str] = None
    page_count: Optional[int] = None

    model_config = {"from_attributes": True}


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
    strategic_note: Optional[str] = None
    selected_projects: Optional[list[str]] = None

    # Token tracking
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None

    compression_attempts: Optional[int] = None
    generation_version: Optional[str] = None
    generation_metadata: Optional[dict] = None
    page_count: Optional[int] = None
    total_cost_usd: Optional[float] = None

    @computed_field
    @property
    def cost_usd(self) -> Optional[float]:
        if self.total_cost_usd is not None:
            return round(self.total_cost_usd, 4)
        if self.input_tokens is None:
            return None
        cost = (
            (self.input_tokens or 0) * 3.00 / 1_000_000
            + (self.cache_write_tokens or 0) * 3.75 / 1_000_000
            + (self.cache_read_tokens or 0) * 0.30 / 1_000_000
            + (self.output_tokens or 0) * 15.00 / 1_000_000
        )
        return round(cost, 4)

    model_config = {"from_attributes": True}


class CandidacyInsightsRead(BaseModel):
    headline: Optional[str] = None
    observed: Optional[str] = None
    gap: Optional[str] = None
    action: Optional[str] = None
    count: int
