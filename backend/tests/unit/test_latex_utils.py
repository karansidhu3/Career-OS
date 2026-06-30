"""
Unit tests for LaTeX helper functions in routers/jobs.py.

_escape_latex  — special character escaping for LaTeX document bodies
_safe_filename — Content-Disposition filename sanitization
_build_cover_letter_latex — full cover letter LaTeX document construction

All pure functions. No database, no network.
"""
import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.routers.jobs import _build_cover_letter_latex, _escape_latex, _safe_filename


# ── _escape_latex ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    # LaTeX special characters
    ("50%",              r"50\%"),
    ("R&D",             r"R\&D"),
    ("pay $100k",       r"pay \$100k"),
    ("#1 ranked",       r"\#1 ranked"),
    ("foo_bar_baz",     r"foo\_bar\_baz"),
    # Typographic replacements
    ("long—dash",  "long---dash"),       # em dash → ---
    ("en–dash",    "en--dash"),          # en dash → --
    ("‘left’",  "'left'"),          # curly singles → straight
    ("“left”",  "``left''"),        # curly doubles → LaTeX double-quote
    ("wait…",      "wait..."),           # ellipsis → ...
    ("non break",  "non break"),         # NBSP → space
    # Clean input is unchanged
    ("clean text",      "clean text"),
    ("",                ""),
    # Multiple specials in one string
    ("50% R&D $100",    r"50\% R\&D \$100"),
])
def test_escape_latex(raw, expected):
    assert _escape_latex(raw) == expected


def test_escape_latex_preserves_normal_punctuation():
    text = "Hello, world. How are you?"
    assert _escape_latex(text) == text


def test_escape_latex_handles_multiple_percent_signs():
    assert _escape_latex("10% off 20%") == r"10\% off 20\%"


# ── _safe_filename ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value, expected", [
    ("Acme Corp",       "acme-corp"),
    ("Google LLC",      "google-llc"),
    ("A & B, Inc.",     "a-b-inc"),
    ("  Spaces  ",      "spaces"),
    ("already-clean",   "already-clean"),
    ("UPPERCASE",       "uppercase"),
    # Edge cases
    ("",                "company"),           # empty → fallback
    ("!@#$%^",          "company"),           # all special → fallback
    ("---",             "company"),           # all dashes → stripped → fallback
])
def test_safe_filename(value, expected):
    assert _safe_filename(value) == expected


def test_safe_filename_truncates_at_max_len():
    long_name = "verylongcompanyname" * 5  # 95 chars
    result = _safe_filename(long_name, max_len=50)
    assert len(result) <= 50


def test_safe_filename_custom_fallback():
    assert _safe_filename("", fallback="resume") == "resume"


def test_safe_filename_collapses_consecutive_dashes():
    # "A & B" → "A---B" → "A-B" after collapsing
    result = _safe_filename("A & B")
    assert "--" not in result


def test_safe_filename_no_leading_or_trailing_dashes():
    result = _safe_filename("  -Company-  ")
    assert not result.startswith("-")
    assert not result.endswith("-")


# ── _build_cover_letter_latex ─────────────────────────────────────────────────

def make_job(**kwargs):
    defaults = {
        "title": "Software Engineer",
        "company": "Acme Corp",
        "cover_letter": "First paragraph about the role.\n\nSecond paragraph about my work.\n\nThird closing paragraph.",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_personal(**kwargs):
    defaults = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+1 555 000 0000",
        "linkedin": "linkedin.com/in/janedoe",
        "github": "github.com/janedoe",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_cover_letter_contains_role_title():
    job = make_job(title="Backend Engineer")
    result = _build_cover_letter_latex(job, None)
    assert "Backend Engineer" in result


def test_cover_letter_contains_company_name():
    job = make_job(company="Stripe")
    result = _build_cover_letter_latex(job, None)
    assert "Stripe" in result


def test_cover_letter_re_line_combines_title_and_company():
    job = make_job(title="SWE", company="Google")
    result = _build_cover_letter_latex(job, None)
    assert "SWE" in result
    assert "Google" in result
    assert r"\textit{Re:" in result


def test_cover_letter_no_re_line_when_title_and_company_absent():
    job = make_job(title=None, company=None)
    result = _build_cover_letter_latex(job, None)
    assert r"\textit{Re:" not in result


def test_cover_letter_escapes_ampersand_in_company():
    job = make_job(company="Acme & Sons")
    result = _build_cover_letter_latex(job, None)
    assert r"Acme \& Sons" in result
    assert "Acme & Sons" not in result


def test_cover_letter_escapes_percent_in_title():
    job = make_job(title="Top 10% Engineer")
    result = _build_cover_letter_latex(job, None)
    assert r"10\%" in result


def test_cover_letter_includes_body_paragraphs():
    job = make_job(cover_letter="Paragraph one.\n\nParagraph two.")
    result = _build_cover_letter_latex(job, None)
    assert "Paragraph one." in result
    assert "Paragraph two." in result


def test_cover_letter_handles_empty_cover_letter_text():
    job = make_job(cover_letter="")
    result = _build_cover_letter_latex(job, None)
    assert isinstance(result, str)
    assert "\\begin{document}" in result


def test_cover_letter_includes_today_date():
    fixed_date = datetime.date(2026, 6, 29)
    with patch("app.routers.jobs.datetime") as mock_dt:
        mock_dt.date.today.return_value = fixed_date
        result = _build_cover_letter_latex(make_job(), None)
    assert "June 29, 2026" in result


def test_cover_letter_is_valid_latex_document_structure():
    result = _build_cover_letter_latex(make_job(), None)
    assert "\\documentclass" in result
    assert "\\begin{document}" in result
    assert "\\end{document}" in result


def test_cover_letter_em_dash_in_body_is_escaped():
    # em dash in cover letter body should become --- for LaTeX
    job = make_job(cover_letter="I built this—it was complex.")
    result = _build_cover_letter_latex(job, None)
    assert "---" in result
    assert "—" not in result


# ── _build_cover_letter_latex — per-user identity (no hardcoded contact info) ──

def test_cover_letter_uses_personal_name_not_hardcoded():
    personal = make_personal(name="Alex Chen")
    result = _build_cover_letter_latex(make_job(), personal)
    assert "Alex Chen" in result
    assert "Karanveer Sidhu" not in result


def test_cover_letter_falls_back_to_applicant_when_personal_missing():
    result = _build_cover_letter_latex(make_job(), None)
    assert "Applicant" in result
    assert "Karanveer Sidhu" not in result


def test_cover_letter_includes_personal_email_link():
    personal = make_personal(email="alex@example.com")
    result = _build_cover_letter_latex(make_job(), personal)
    assert r"\href{mailto:alex@example.com}" in result


def test_cover_letter_omits_contact_fields_that_are_absent():
    personal = make_personal(phone=None, linkedin=None, github=None)
    result = _build_cover_letter_latex(make_job(), personal)
    assert r"\faPhone" not in result
    assert r"\faLinkedin" not in result
    assert r"\faGithub" not in result


def test_cover_letter_escapes_special_chars_in_name():
    personal = make_personal(name="A & B")
    result = _build_cover_letter_latex(make_job(), personal)
    assert r"A \& B" in result
