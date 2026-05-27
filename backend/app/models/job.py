from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Job(Base):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String)
    description = Column(Text)
    url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # new → generated → applied / skipped
    status = Column(String, nullable=False, default="new")

    # Populated by generation service
    fit_score = Column(Integer, nullable=True)
    fit_rationale = Column(JSONB, nullable=True)  # list[str], 3 bullets
    resume_latex = Column(Text, nullable=True)
    cover_letter = Column(Text, nullable=True)
