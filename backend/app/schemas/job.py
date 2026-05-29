from datetime import datetime
from typing import Optional

from pydantic import BaseModel, computed_field


class JobGenerateRequest(BaseModel):
    description: str
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
    strategic_note: Optional[str] = None

    # Token tracking
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None

    @computed_field
    @property
    def cost_usd(self) -> Optional[float]:
        if self.input_tokens is None:
            return None
        non_cached = max(
            0,
            (self.input_tokens or 0)
            - (self.cache_read_tokens or 0)
            - (self.cache_write_tokens or 0),
        )
        cost = (
            non_cached * 3.00 / 1_000_000
            + (self.cache_write_tokens or 0) * 3.75 / 1_000_000
            + (self.cache_read_tokens or 0) * 0.30 / 1_000_000
            + (self.output_tokens or 0) * 15.00 / 1_000_000
        )
        return round(cost, 4)

    model_config = {"from_attributes": True}


class CandidacyInsightsRead(BaseModel):
    observation: Optional[str] = None
    count: int
