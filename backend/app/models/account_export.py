from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AccountExport(Base):
    """Tracks an async account-data-export job (Phase 6).

    One row per export request. status starts "processing"; the worker sets it to
    "ready" (with storage_key pointing at the generated zip in PDFStorage-style
    object storage) or "failed" (with error_message). expires_at bounds how long
    the download link and underlying zip stay around.
    """

    __tablename__ = "account_exports"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="processing")
    storage_key = Column(String)
    error_message = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
