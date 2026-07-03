from sqlalchemy import Column, DateTime, Integer, String, func

from app.database import Base


class WaitlistEntry(Base):
    """A pre-auth waitlist signup (Phase 8). Not user-scoped — collected before
    anyone has a Clerk account — so no RLS policy applies here, unlike every
    other table in this app. Karan reviews entries directly and invites people
    manually via Clerk (no automated invite-email flow is built here — see
    CLAUDE.md's "no email digests/marketing" carve-out; this stays a plain
    signup list, not a mailing list)."""

    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_at = Column(DateTime(timezone=True), nullable=True)
