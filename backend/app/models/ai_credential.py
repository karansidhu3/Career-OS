from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AICredential(Base):
    """A user's own encrypted AI provider API key (Phase 3 — BYO key).

    One row per (user_id, provider). encrypted_key is never returned by any API
    response — only key_hint (last 4 chars) and label are used for display.
    """

    __tablename__ = "ai_credentials"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_ai_credentials_user_provider"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False, default="anthropic")
    encrypted_key = Column(String, nullable=False)
    key_version = Column(Integer, nullable=False, default=1)
    key_hint = Column(String(4), nullable=False)
    label = Column(String)
    last_verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
