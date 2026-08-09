"""Resume import (Phase 4): PDF/DOCX/pasted text -> AI-extracted structured profile draft.

The draft is never written to the database. The route that calls this returns it straight
to the frontend, which shows it for review/edit — the user accepts (or corrects) each item
before it's saved via the existing profile CRUD endpoints. Billed to the requesting user's
own key (see app.services.credentials), never Karan's.
"""
import io
import zipfile
from uuid import UUID

from docx import Document
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.generation import CLAUDE_MODEL
from app.services.llm_client import get_llm_client
from app.services.llm_cost import record_llm_call

MAX_RESUME_TEXT_CHARS = 20_000

# A real resume's internal XML is a few hundred KB at most — this is a zip-bomb
# guard (DOCX is a zip archive), not a realistic-resume-size limit. Read from
# the central directory (zipfile.infolist() does not decompress anything) so
# the check itself can't be used to trigger the same exhaustion it prevents.
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024


def _check_docx_not_a_zip_bomb(data: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        total_uncompressed = sum(info.file_size for info in zf.infolist())
        if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
            raise ValueError("This file's internal content is too large to be a real resume.")

_EXTRACT_SYSTEM = (
    "You extract structured resume data from raw text. Extract only what is explicitly "
    "present in the text — never invent names, dates, companies, schools, technologies, "
    "or numbers. If a field is not present, use an empty string (or empty array for "
    "lists). Preserve exact numbers, technologies, and proper nouns from the source text. "
    "For experience and project descriptions, stay close to the original wording — do "
    "not rewrite, embellish, or infer accomplishments not stated."
)

_EXTRACT_TOOL = {
    "name": "extracted_profile",
    "description": "Structured profile data extracted from resume text, for the user to review before saving.",
    "input_schema": {
        "type": "object",
        "properties": {
            "personal": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "linkedin": {"type": "string"},
                    "github": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["name", "email"],
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "school": {"type": "string"},
                        "degree": {"type": "string"},
                        "field": {"type": "string"},
                        "minor": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                    },
                    "required": ["school", "degree"],
                },
            },
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "role": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "location": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["company", "role"],
                },
            },
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "github_url": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["category", "items"],
                },
            },
        },
        "required": ["personal", "education", "experience", "projects", "skills"],
    },
}


def extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(data: bytes) -> str:
    _check_docx_not_a_zip_bomb(data)
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


async def extract_profile_draft(
    resume_text: str,
    api_key: str,
    *,
    db: AsyncSession | None = None,
    user_id: UUID | None = None,
) -> dict:
    """Send raw resume text to Claude and return a structured draft for review.

    Never touches the database — the caller returns this straight to the frontend.
    """
    text = resume_text.strip()[:MAX_RESUME_TEXT_CHARS]
    if not text:
        raise ValueError("No text found to extract from.")

    llm = get_llm_client(api_key)
    result = await llm.call_tool(
        model=CLAUDE_MODEL,
        max_tokens=4000,
        system=_EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": text}],
        tool=_EXTRACT_TOOL,
        timeout=60.0,
    )
    if db is not None and user_id is not None:
        record_llm_call(db, user_id=user_id, job_id=None, purpose="resume_import", model=CLAUDE_MODEL, usage=result)
    data = result.tool_input
    personal = data.get("personal") or {}

    return {
        "personal": {
            "name": _clean(personal.get("name")),
            "email": _clean(personal.get("email")),
            "phone": _clean(personal.get("phone")),
            "linkedin": _clean(personal.get("linkedin")),
            "github": _clean(personal.get("github")),
            "location": _clean(personal.get("location")),
        },
        "education": [
            {
                "school": _clean(e.get("school")) or "",
                "degree": _clean(e.get("degree")) or "",
                "field": _clean(e.get("field")),
                "minor": _clean(e.get("minor")),
                "start_date": _clean(e.get("start_date")),
                "end_date": _clean(e.get("end_date")),
            }
            for e in data.get("education") or []
        ],
        "experience": [
            {
                "company": _clean(e.get("company")) or "",
                "role": _clean(e.get("role")) or "",
                "start_date": _clean(e.get("start_date")),
                "end_date": _clean(e.get("end_date")),
                "location": _clean(e.get("location")),
                "description": (e.get("description") or "").strip(),
            }
            for e in data.get("experience") or []
        ],
        "projects": [
            {
                "name": _clean(p.get("name")) or "",
                "start_date": _clean(p.get("start_date")),
                "end_date": _clean(p.get("end_date")),
                "github_url": _clean(p.get("github_url")),
                "description": (p.get("description") or "").strip(),
            }
            for p in data.get("projects") or []
        ],
        "skills": [
            {
                "category": _clean(s.get("category")) or "",
                "items": [i for i in (s.get("items") or []) if i],
            }
            for s in data.get("skills") or []
        ],
    }
