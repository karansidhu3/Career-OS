from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class Job(Base):
    __tablename__ = "job"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
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
    strategic_note = Column(Text, nullable=True)
    selected_projects = Column(JSONB, nullable=True)  # list[str] — project names emphasized

    # Token usage from Claude API response
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cache_read_tokens = Column(Integer, nullable=True)
    cache_write_tokens = Column(Integer, nullable=True)

    # Number of times the resume was recompressed to fit one page (0 = no compression needed)
    compression_attempts = Column(Integer, nullable=True)

    # Generation v2 audit fields. These make quality/cost claims inspectable rather
    # than reconstructing them from logs after the fact.
    generation_version = Column(String(32), nullable=True)
    generation_metadata = Column(JSONB, nullable=True)
    page_count = Column(Integer, nullable=True)
    total_cost_usd = Column(Float, nullable=True)
