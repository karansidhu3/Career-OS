from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class PersonalInfo(Base):
    __tablename__ = "personal_info"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)
    linkedin = Column(String)
    github = Column(String)
    location = Column(String)
    target_roles = Column(JSONB, default=list)
    target_locations = Column(JSONB, default=list)


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True)
    school = Column(String, nullable=False)
    degree = Column(String, nullable=False)
    field = Column(String)
    minor = Column(String)
    start_date = Column(String)
    end_date = Column(String)


class Experience(Base):
    __tablename__ = "experience"

    id = Column(Integer, primary_key=True)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    start_date = Column(String)
    end_date = Column(String)
    bullets = Column(JSONB, default=list)
    sort_order = Column(Integer, default=0)


class Project(Base):
    __tablename__ = "project"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    tech = Column(JSONB, default=list)
    start_date = Column(String)
    end_date = Column(String)
    bullets = Column(JSONB, default=list)
    sort_order = Column(Integer, default=0)


class SkillCategory(Base):
    __tablename__ = "skill_category"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)
    items = Column(JSONB, default=list)
    sort_order = Column(Integer, default=0)
