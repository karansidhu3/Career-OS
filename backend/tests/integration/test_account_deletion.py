"""
Integration tests for app.services.account_deletion.hard_delete_user (Phase 6).
"""
import pytest
from sqlalchemy import select

from app.models.account_export import AccountExport
from app.models.ai_credential import AICredential
from app.models.job import Job
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.models.user import User
from app.services.account_deletion import hard_delete_user
from app.services.crypto import encrypt

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _pdf_storage_tmp_dir(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "pdf_storage_dir", str(tmp_path))


async def _seed_everything(db_session, user_id):
    db_session.add(PersonalInfo(user_id=user_id, name="Jane Dev", email="jane@example.com"))
    db_session.add(Education(user_id=user_id, school="State U", degree="BSc"))
    db_session.add(Experience(user_id=user_id, company="Acme", role="Engineer"))
    db_session.add(Project(user_id=user_id, name="Cool Project"))
    db_session.add(SkillCategory(user_id=user_id, category="Languages", items=["Python"]))
    db_session.add(Job(user_id=user_id, title="Backend Engineer", status="generated", resume_latex=r"\section{r}"))
    encrypted_key, key_version = encrypt("sk-ant-test-fixture")
    db_session.add(AICredential(user_id=user_id, provider="anthropic", encrypted_key=encrypted_key, key_version=key_version, key_hint="1234"))
    db_session.add(AccountExport(user_id=user_id, status="ready"))
    await db_session.commit()


async def test_hard_delete_removes_all_user_scoped_rows_and_the_user(db_session, current_test_user):
    await _seed_everything(db_session, current_test_user.id)

    await hard_delete_user(db_session, current_test_user)

    for model in (PersonalInfo, Education, Experience, Project, SkillCategory, Job, AICredential, AccountExport):
        remaining = (await db_session.execute(select(model).where(model.user_id == current_test_user.id))).scalars().all()
        assert remaining == [], f"{model.__name__} rows survived hard delete"

    user_row = (await db_session.execute(select(User).where(User.id == current_test_user.id))).scalar_one_or_none()
    assert user_row is None


async def test_hard_delete_removes_cached_pdfs_and_export_zip(db_session, current_test_user):
    from app.services.pdf_storage import account_export_key, get_pdf_storage, resume_pdf_key

    job = Job(user_id=current_test_user.id, title="Backend Engineer", status="generated", resume_latex=r"\section{r}")
    db_session.add(job)
    export = AccountExport(user_id=current_test_user.id, status="ready")
    db_session.add(export)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(export)

    storage = get_pdf_storage()
    await storage.save(resume_pdf_key(job.id), b"%PDF-fake")
    await storage.save(account_export_key(export.id), b"PK\x03\x04fake")

    await hard_delete_user(db_session, current_test_user)

    assert await storage.load(resume_pdf_key(job.id)) is None
    assert await storage.load(account_export_key(export.id)) is None


async def test_hard_delete_on_user_with_no_data_does_not_raise(db_session, current_test_user):
    await hard_delete_user(db_session, current_test_user)
    user_row = (await db_session.execute(select(User).where(User.id == current_test_user.id))).scalar_one_or_none()
    assert user_row is None
