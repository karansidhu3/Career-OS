"""Account data export (Phase 6): builds a zip of everything a user has stored in
CareerOS — profile (JSON + markdown), every application's resume/cover letter
(LaTeX + PDF), application history (JSON + CSV), and account metadata. Async by
design — compiling every job's PDF can take a while — see app.worker.run_export_job
for the ARQ task that calls this and app.services.email_client for the
"your export is ready" notification.
"""
import csv
import io
import json
import zipfile
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.profile import Education, Experience, PersonalInfo, Project, SkillCategory
from app.models.user import User
from app.routers.jobs import _build_cover_letter_latex
from app.services.pdf import compile_latex_to_pdf
from app.services.pdf_storage import cover_letter_pdf_key, get_pdf_storage, resume_pdf_key


def _slugify(value: str, max_len: int = 40) -> str:
    safe = "".join(c if c.isalnum() else "-" for c in value.strip().lower())
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe.strip("-")[:max_len] or "untitled"


def _profile_markdown(
    personal: PersonalInfo | None,
    education: list[Education],
    experience: list[Experience],
    projects: list[Project],
    skills: list[SkillCategory],
) -> str:
    lines: list[str] = []
    if personal:
        lines += [f"# {personal.name}", "", personal.email or ""]
        if personal.phone:
            lines.append(personal.phone)
        if personal.linkedin:
            lines.append(personal.linkedin)
        if personal.github:
            lines.append(personal.github)
        if personal.location:
            lines.append(personal.location)
        lines.append("")
    if education:
        lines.append("## Education")
        for e in education:
            lines.append(f"- {e.school} — {e.degree}{f', {e.field}' if e.field else ''} ({e.start_date}–{e.end_date})")
        lines.append("")
    if experience:
        lines.append("## Experience")
        for e in sorted(experience, key=lambda x: x.sort_order or 0):
            lines.append(f"### {e.role}, {e.company} ({e.start_date}–{e.end_date})")
            if e.description:
                lines.append(e.description)
            lines.append("")
    if projects:
        lines.append("## Projects")
        for p in sorted(projects, key=lambda x: x.sort_order or 0):
            lines.append(f"### {p.name} ({p.start_date}–{p.end_date})")
            if p.description:
                lines.append(p.description)
            lines.append("")
    if skills:
        lines.append("## Skills")
        for s in sorted(skills, key=lambda x: x.sort_order or 0):
            lines.append(f"- **{s.category}**: {', '.join(s.items or [])}")
        lines.append("")
    return "\n".join(lines)


async def build_export_zip(db: AsyncSession, user: User) -> bytes:
    personal = (
        await db.execute(select(PersonalInfo).where(PersonalInfo.user_id == user.id))
    ).scalar_one_or_none()
    education = list((await db.execute(select(Education).where(Education.user_id == user.id))).scalars().all())
    experience = list((await db.execute(select(Experience).where(Experience.user_id == user.id))).scalars().all())
    projects = list((await db.execute(select(Project).where(Project.user_id == user.id))).scalars().all())
    skills = list((await db.execute(select(SkillCategory).where(SkillCategory.user_id == user.id))).scalars().all())
    jobs = list(
        (await db.execute(select(Job).where(Job.user_id == user.id).order_by(Job.created_at))).scalars().all()
    )

    storage = get_pdf_storage()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        profile_dict = {
            "personal_info": {
                c.name: getattr(personal, c.name) for c in PersonalInfo.__table__.columns
            } if personal else None,
            "education": [{c.name: getattr(e, c.name) for c in Education.__table__.columns} for e in education],
            "experience": [{c.name: getattr(e, c.name) for c in Experience.__table__.columns} for e in experience],
            "projects": [{c.name: getattr(p, c.name) for c in Project.__table__.columns} for p in projects],
            "skills": [{c.name: getattr(s, c.name) for c in SkillCategory.__table__.columns} for s in skills],
        }
        zf.writestr("profile/profile.json", json.dumps(profile_dict, indent=2, default=str))
        zf.writestr("profile/profile.md", _profile_markdown(personal, education, experience, projects, skills))

        zf.writestr(
            "account.json",
            json.dumps(
                {
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
        )

        history_rows = [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "status": j.status,
                "fit_score": j.fit_score,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
        zf.writestr("applications/history.json", json.dumps(history_rows, indent=2, default=str))
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=["id", "title", "company", "status", "fit_score", "created_at"])
        writer.writeheader()
        writer.writerows(history_rows)
        zf.writestr("applications/history.csv", csv_buf.getvalue())

        for job in jobs:
            folder = f"applications/{job.id}_{_slugify(job.company or job.title)}"
            if job.resume_latex:
                zf.writestr(f"{folder}/resume.tex", job.resume_latex)
                pdf_bytes = await storage.load(resume_pdf_key(job.id))
                if pdf_bytes is None:
                    try:
                        pdf_bytes = await compile_latex_to_pdf(job.resume_latex)
                    except Exception:
                        pdf_bytes = None
                if pdf_bytes:
                    zf.writestr(f"{folder}/resume.pdf", pdf_bytes)
            if job.cover_letter:
                zf.writestr(f"{folder}/cover_letter.txt", job.cover_letter)
                cl_pdf = await storage.load(cover_letter_pdf_key(job.id))
                if cl_pdf is None:
                    try:
                        latex = _build_cover_letter_latex(job, personal)
                        cl_pdf = await compile_latex_to_pdf(latex)
                    except Exception:
                        cl_pdf = None
                if cl_pdf:
                    zf.writestr(f"{folder}/cover_letter.pdf", cl_pdf)

    return buffer.getvalue()
