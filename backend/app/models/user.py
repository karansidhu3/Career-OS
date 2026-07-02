import uuid

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Phase 6 — account deletion grace period. Set when the user requests deletion;
    # NULL means no deletion pending. app.worker's cron sweep hard-deletes any user
    # whose scheduled_deletion_at has passed.
    scheduled_deletion_at = Column(DateTime(timezone=True), nullable=True)
