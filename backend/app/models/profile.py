from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class PersonalInfo(Base):
    __tablename__ = "personal_info"

    id = Column(Integer, primary_key=True)
    # No longer a global singleton — one row per user.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)
    linkedin = Column(String)
    github = Column(String)
    location = Column(String)
    target_roles = Column(JSONB, default=list)
    target_locations = Column(JSONB, default=list)
    cover_letter_voice = Column(Text, default="")


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    school = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field = Column(String)
    minor = Column(String)
    start_date = Column(String)
    end_date = Column(String)
    # Phase 6 — soft-delete + undo. NULL means active; list/get endpoints filter
    # these out, DELETE endpoints set this instead of removing the row, and a
    # /restore endpoint clears it. Career history is the most irreplaceable data
    # in the product — accidental deletes must be recoverable.
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Experience(Base):
    __tablename__ = "experience"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    start_date = Column(String)
    end_date = Column(String)
    location = Column(Text)
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    start_date = Column(String)
    end_date = Column(String)
    github_url = Column(Text)
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class SkillCategory(Base):
    __tablename__ = "skill_category"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)
    items = Column(JSONB, default=list)
    sort_order = Column(Integer, default=0)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
