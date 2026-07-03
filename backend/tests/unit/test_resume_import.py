"""Unit tests for app.services.resume_import — text extraction and AI-extraction plumbing.

The Anthropic call itself is mocked (this module's job is deterministic text extraction
plus reshaping the tool's output — not re-testing Claude's accuracy).
"""
import io
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from docx import Document
from pypdf import PdfWriter

from app.services import resume_import
from app.services.llm_client import ToolCallResult


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_zip_bomb_bytes(uncompressed_size: int) -> bytes:
    """A real zip whose declared (central-directory) uncompressed size is huge
    but whose actual on-the-wire bytes are tiny, via a highly compressible
    repeated-byte payload — the same shape a real zip bomb takes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", b"A" * uncompressed_size)
    return buf.getvalue()


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extract_text_from_docx():
    data = _make_docx_bytes(["Karan Sidhu", "Software Engineer"])
    text = resume_import.extract_text_from_docx(data)
    assert "Karan Sidhu" in text
    assert "Software Engineer" in text


def test_extract_text_from_pdf_blank_page_returns_empty_string():
    data = _make_pdf_bytes()
    text = resume_import.extract_text_from_pdf(data)
    assert text == ""


def test_extract_text_from_docx_rejects_zip_bomb():
    """A real resume's internal XML is a few hundred KB at most — a DOCX
    whose declared uncompressed content vastly exceeds that is rejected
    before python-docx ever decompresses it."""
    data = _make_zip_bomb_bytes(resume_import.MAX_DOCX_UNCOMPRESSED_BYTES + 1)
    with pytest.raises(ValueError):
        resume_import.extract_text_from_docx(data)


def test_extract_text_from_docx_allows_realistic_size():
    data = _make_docx_bytes(["A perfectly normal resume paragraph."] * 50)
    text = resume_import.extract_text_from_docx(data)
    assert "perfectly normal resume paragraph" in text


@pytest.mark.asyncio
async def test_extract_profile_draft_shapes_ai_output():
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = ToolCallResult(tool_input={
        "personal": {"name": "Jane Doe", "email": "jane@example.com", "phone": "", "linkedin": "", "github": "", "location": ""},
        "education": [{"school": "MIT", "degree": "BSc", "field": "", "minor": "", "start_date": "", "end_date": ""}],
        "experience": [{"company": "Acme", "role": "Engineer", "start_date": "2020", "end_date": "2022", "location": "", "description": "Built things."}],
        "projects": [{"name": "Cool Project", "start_date": "", "end_date": "", "github_url": "", "description": "Did stuff."}],
        "skills": [{"category": "Languages", "items": ["Python", "Go"]}],
    })
    with patch("app.services.resume_import.get_llm_client", return_value=mock_client):
        draft = await resume_import.extract_profile_draft("Jane Doe resume text...", api_key="fake-key")

    assert draft["personal"]["name"] == "Jane Doe"
    assert draft["personal"]["email"] == "jane@example.com"
    assert draft["personal"]["phone"] is None  # empty string cleaned to None
    assert draft["education"][0]["school"] == "MIT"
    assert draft["experience"][0]["company"] == "Acme"
    assert draft["projects"][0]["name"] == "Cool Project"
    assert draft["skills"][0]["items"] == ["Python", "Go"]

    # The mock must have been invoked with the real api_key we passed in
    mock_client.call_tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_profile_draft_rejects_empty_text():
    with pytest.raises(ValueError):
        await resume_import.extract_profile_draft("   ", api_key="fake-key")


@pytest.mark.asyncio
async def test_extract_profile_draft_filters_blank_skill_items():
    mock_client = AsyncMock()
    mock_client.call_tool.return_value = ToolCallResult(tool_input={
        "personal": {"name": "Jane", "email": "jane@example.com"},
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [{"category": "Languages", "items": ["Python", "", None, "Go"]}],
    })
    with patch("app.services.resume_import.get_llm_client", return_value=mock_client):
        draft = await resume_import.extract_profile_draft("some resume text", api_key="fake-key")

    assert draft["skills"][0]["items"] == ["Python", "Go"]
