"""
Integration tests for app.services.account_export.build_export_zip (Phase 6).

compile_latex_to_pdf is mocked — this suite verifies zip contents/structure,
not Tectonic itself.
"""
import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import pytest

from app.models.job import Job
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.services.account_export import build_export_zip

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _pdf_storage_tmp_dir(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "pdf_storage_dir", str(tmp_path))


async def _seed_full_profile(db_session, user_id):
    db_session.add(PersonalInfo(user_id=user_id, name="Jane Dev", email="jane@example.com"))
    db_session.add(Education(user_id=user_id, school="State U", degree="BSc", start_date="2020", end_date="2024"))
    db_session.add(Experience(user_id=user_id, company="Acme", role="Engineer", start_date="2024", end_date="Present", description="Built things."))
    db_session.add(Project(user_id=user_id, name="Cool Project", start_date="2024", end_date="2024", description="Did a thing."))
    db_session.add(SkillCategory(user_id=user_id, category="Languages", items=["Python", "TypeScript"]))
    job = Job(
        user_id=user_id, title="Backend Engineer", company="Widgets Inc", status="generated",
        resume_latex=r"\section{Resume}", cover_letter="Dear hiring manager,\n\nI am great.\n\nBest,\nJane",
    )
    db_session.add(job)
    await db_session.commit()


async def test_export_zip_contains_profile_account_and_history(db_session, current_test_user):
    await _seed_full_profile(db_session, current_test_user.id)

    with patch("app.services.account_export.compile_latex_to_pdf", AsyncMock(return_value=b"%PDF-fake")):
        zip_bytes = await build_export_zip(db_session, current_test_user)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "profile/profile.json" in names
        assert "profile/profile.md" in names
        assert "account.json" in names
        assert "applications/history.json" in names
        assert "applications/history.csv" in names

        profile = json.loads(zf.read("profile/profile.json"))
        assert profile["personal_info"]["name"] == "Jane Dev"
        assert len(profile["education"]) == 1
        assert len(profile["experience"]) == 1
        assert len(profile["projects"]) == 1
        assert len(profile["skills"]) == 1

        account = json.loads(zf.read("account.json"))
        assert account["email"] == current_test_user.email

        history = json.loads(zf.read("applications/history.json"))
        assert len(history) == 1
        assert history[0]["company"] == "Widgets Inc"


async def test_export_zip_includes_resume_and_cover_letter_per_job(db_session, current_test_user):
    await _seed_full_profile(db_session, current_test_user.id)

    with patch("app.services.account_export.compile_latex_to_pdf", AsyncMock(return_value=b"%PDF-fake")):
        zip_bytes = await build_export_zip(db_session, current_test_user)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        job_files = [n for n in zf.namelist() if n.startswith("applications/") and "widgets" in n.lower()]
        assert any(n.endswith("resume.tex") for n in job_files)
        assert any(n.endswith("resume.pdf") for n in job_files)
        assert any(n.endswith("cover_letter.txt") for n in job_files)
        assert any(n.endswith("cover_letter.pdf") for n in job_files)


async def test_export_zip_skips_pdf_when_compile_fails_but_keeps_latex(db_session, current_test_user):
    await _seed_full_profile(db_session, current_test_user.id)

    with patch("app.services.account_export.compile_latex_to_pdf", AsyncMock(side_effect=RuntimeError("boom"))):
        zip_bytes = await build_export_zip(db_session, current_test_user)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert any(n.endswith("resume.tex") for n in names)
        assert not any(n.endswith("resume.pdf") for n in names)


async def test_export_zip_handles_empty_profile_gracefully(db_session, current_test_user):
    zip_bytes = await build_export_zip(db_session, current_test_user)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        profile = json.loads(zf.read("profile/profile.json"))
        assert profile["personal_info"] is None
        assert profile["education"] == []
        history = json.loads(zf.read("applications/history.json"))
        assert history == []
