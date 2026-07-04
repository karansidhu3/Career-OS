"""
Unit tests for generation.py pure helper functions.

No database, no HTTP, no Claude API — these run anywhere in under a second.
"""
from types import SimpleNamespace

import pytest

from app.services.generation import (
    LATEX_PREAMBLE,
    _assemble_resume_latex,
    _extract_gaps,
    _extract_resume_body,
    _format_profile,
    _preprocess_jd,
)


# ── Factories ─────────────────────────────────────────────────────────────────

def make_personal(**kwargs):
    return SimpleNamespace(**{
        "name": "Test User",
        "email": "test@example.com",
        "phone": None,
        "location": None,
        "cover_letter_voice": "",
        **kwargs,
    })


def make_experience(**kwargs):
    return SimpleNamespace(**{
        "company": "Acme",
        "role": "Engineer",
        "start_date": "Jan 2024",
        "end_date": None,
        "location": None,
        "description": "Built things.",
        **kwargs,
    })


def make_project(**kwargs):
    return SimpleNamespace(**{
        "name": "MyProject",
        "start_date": "Jan 2024",
        "end_date": None,
        "github_url": None,
        "description": "A cool project.",
        **kwargs,
    })


def make_skill(**kwargs):
    return SimpleNamespace(**{"category": "Languages", "items": ["Python", "JS"], **kwargs})


# ── _preprocess_jd ────────────────────────────────────────────────────────────

def test_preprocess_strips_html_tags():
    assert _preprocess_jd("<p>Hello <b>world</b></p>") == "Hello world"


def test_preprocess_strips_nested_html():
    assert _preprocess_jd("<div><span>text</span></div>") == "text"


def test_preprocess_collapses_multiple_spaces():
    result = _preprocess_jd("hello   world\t\there")
    assert "  " not in result
    assert "hello world here" == result


def test_preprocess_collapses_excess_newlines():
    result = _preprocess_jd("line1\n\n\n\nline2")
    assert "\n\n\n" not in result


def test_preprocess_strips_leading_trailing_whitespace():
    assert _preprocess_jd("  hello  ") == "hello"


def test_preprocess_truncates_at_6000_chars_with_marker():
    long_jd = "x" * 7000
    result = _preprocess_jd(long_jd)
    assert len(result) <= 6000 + len("\n\n[truncated — full posting was longer]")
    assert "[truncated" in result


def test_preprocess_does_not_truncate_short_jd():
    jd = "Senior Software Engineer role." * 10
    result = _preprocess_jd(jd)
    assert "[truncated" not in result


def test_preprocess_custom_max_chars():
    result = _preprocess_jd("a" * 200, max_chars=100)
    assert "[truncated" in result


def test_preprocess_handles_empty_string():
    assert _preprocess_jd("") == ""


def test_preprocess_strips_html_leaving_clean_text():
    result = _preprocess_jd("<h1>Job Title</h1><ul><li>Python</li><li>FastAPI</li></ul>")
    assert "Job Title" in result
    assert "Python" in result
    assert "FastAPI" in result
    assert "<" not in result


# ── _format_profile ───────────────────────────────────────────────────────────

def test_format_profile_contains_header():
    result = _format_profile(None, [], [], [])
    assert "CANDIDATE FACT BANK" in result


def test_format_profile_includes_experience_role_and_company():
    exp = make_experience(role="SWE", company="Google")
    result = _format_profile(None, [exp], [], [])
    assert "SWE" in result
    assert "Google" in result


def test_format_profile_includes_experience_description():
    exp = make_experience(description="Built a distributed cache using Redis.")
    result = _format_profile(None, [exp], [], [])
    assert "distributed cache" in result


def test_format_profile_includes_project_name_and_description():
    proj = make_project(name="MarketMind", description="Multi-agent investment platform.")
    result = _format_profile(None, [], [proj], [])
    assert "MarketMind" in result
    assert "Multi-agent" in result


def test_format_profile_includes_github_url_when_present():
    proj = make_project(github_url="https://github.com/user/repo")
    result = _format_profile(None, [], [proj], [])
    assert "github.com/user/repo" in result


def test_format_profile_omits_github_when_absent():
    proj = make_project(github_url=None)
    result = _format_profile(None, [], [proj], [])
    assert "GitHub:" not in result


def test_format_profile_includes_skills():
    skill = make_skill(category="Languages", items=["Python", "Go", "Rust"])
    result = _format_profile(None, [], [], [skill])
    assert "Languages" in result
    assert "Python" in result
    assert "Go" in result


def test_format_profile_includes_cover_letter_voice():
    personal = make_personal(cover_letter_voice="Direct. Short sentences. No filler.")
    result = _format_profile(personal, [], [], [])
    assert "Direct. Short sentences. No filler." in result


def test_format_profile_omits_voice_section_when_empty():
    personal = make_personal(cover_letter_voice="")
    result = _format_profile(personal, [], [], [])
    assert "COVER LETTER VOICE" not in result


def test_format_profile_uses_present_when_end_date_missing():
    exp = make_experience(end_date=None)
    result = _format_profile(None, [exp], [], [])
    assert "Present" in result


def test_format_profile_includes_location_when_present():
    exp = make_experience(location="Kelowna, BC")
    result = _format_profile(None, [exp], [], [])
    assert "Kelowna, BC" in result


def test_format_profile_multiple_experience_entries_indexed():
    exps = [make_experience(company="A"), make_experience(company="B")]
    result = _format_profile(None, exps, [], [])
    assert "[1]" in result
    assert "[2]" in result


def test_format_profile_handles_all_none():
    result = _format_profile(None, [], [], [])
    assert isinstance(result, str)
    assert len(result) > 0


# ── _extract_resume_body ──────────────────────────────────────────────────────

BODY_SECTION = "%-----------EXPERIENCE\n\\section{Experience}\n\\resumeSubheading{Acme}{}{Engineer}{2024}"

FULL_DOC = (
    "\\documentclass[letterpaper,11pt]{article}\n"
    "\\begin{document}\n"
    + BODY_SECTION
    + "\n\\end{document}"
)


def test_extract_from_full_doc_via_experience_marker():
    result = _extract_resume_body(FULL_DOC)
    assert "\\section{Experience}" in result
    assert "\\documentclass" not in result
    assert "\\end{document}" not in result


def test_extract_body_only_passthrough():
    body_only = "%-----------EXPERIENCE\n\\section{Experience}\nContent here"
    result = _extract_resume_body(body_only)
    assert "\\section{Experience}" in result
    assert "\\documentclass" not in result


def test_extract_strips_stray_end_document_from_body_only():
    body_with_tail = "%-----------EXPERIENCE\n\\section{Experience}\n\\end{document}"
    result = _extract_resume_body(body_with_tail)
    assert "\\end{document}" not in result


def test_extract_handles_full_doc_without_experience_marker():
    # Falls back to stripping everything before \begin{document}
    doc = "\\documentclass{article}\n\\begin{document}\n\\section{Skills}\n\\end{document}"
    result = _extract_resume_body(doc)
    assert "\\section{Skills}" in result
    assert "\\documentclass" not in result
    assert "\\end{document}" not in result


def test_extract_returns_input_when_no_markers():
    raw = "Some plain text with no LaTeX markers"
    result = _extract_resume_body(raw)
    assert result == raw


def test_extract_handles_empty_string():
    assert _extract_resume_body("") == ""


# ── _assemble_resume_latex ────────────────────────────────────────────────────

def test_assemble_prepends_latex_preamble():
    result = _assemble_resume_latex(BODY_SECTION)
    assert result.startswith(LATEX_PREAMBLE)


def test_assemble_appends_end_document():
    result = _assemble_resume_latex(BODY_SECTION)
    assert result.strip().endswith("\\end{document}")


def test_assemble_includes_body_content():
    result = _assemble_resume_latex(BODY_SECTION)
    assert "\\section{Experience}" in result


def test_assemble_extracts_body_before_wrapping():
    # If given a full doc, strips the preamble before re-assembling.
    # The result should not duplicate the preamble.
    result = _assemble_resume_latex(FULL_DOC)
    assert result.count("\\documentclass") == 1


def test_assemble_produces_compilable_document_structure():
    result = _assemble_resume_latex(BODY_SECTION)
    assert "\\begin{document}" in result
    assert "\\end{document}" in result


# ── _extract_gaps (candidacy insights token optimization) ─────────────────────

def test_extract_gaps_pulls_only_gaps_section():
    note = (
        "GOOD FIT\n"
        "- Strong Python and FastAPI overlap\n"
        "- Docker experience matches\n"
        "\n"
        "GAPS\n"
        "- No Kubernetes experience\n"
        "- No Go experience\n"
        "\n"
        "IMPROVEMENT PLAN\n"
        "- Add a Kubernetes deployment to Relay\n"
    )
    result = _extract_gaps(note)
    assert "No Kubernetes experience" in result
    assert "No Go experience" in result
    assert "Strong Python" not in result
    assert "Add a Kubernetes deployment" not in result


def test_extract_gaps_handles_gaps_as_last_section():
    # No IMPROVEMENT PLAN section at all — GAPS runs to the end of the string.
    note = "GOOD FIT\n- Strong match\n\nGAPS\n- No Rust experience\n"
    result = _extract_gaps(note)
    assert "No Rust experience" in result
    assert "Strong match" not in result


def test_extract_gaps_falls_back_to_full_note_when_unstructured():
    # Older, pre-format notes are a single prose paragraph with no section headers.
    note = "This role wants five years of Rust which the candidate doesn't have."
    assert _extract_gaps(note) == note


def test_extract_gaps_handles_empty_string():
    assert _extract_gaps("") == ""
