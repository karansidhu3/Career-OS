"""Contract tests for the active, quality-first generation prompt.

These assertions intentionally protect the ideas most likely to disappear in a
future cost or reliability rewrite. They are not a substitute for the six-role
document benchmark; they prevent the prompt from silently becoming a literal
fact copier or keyword filter again.
"""

from app import worker
from app.services import generation


def test_worker_uses_full_context_generator() -> None:
    assert worker.generate_materials is generation.generate_materials
    assert generation.GENERATION_VERSION == "ultimate-prompt-v2-quality-gated"


def test_prompt_optimizes_defensible_leverage_not_literal_copying() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "MAXIMUM DEFENSIBLE LEVERAGE" in prompt
    assert "Truth is the boundary" in prompt
    assert "The wording and conclusion do not need to appear verbatim" in prompt
    assert "DIRECT" in prompt
    assert "TRANSFERABLE" in prompt
    assert "ABSENT" in prompt
    assert "Never omit strong transferable evidence" in prompt


def test_prompt_preserves_original_editorial_quality_system() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "STEP 0 — Extract and tier all metrics" in prompt
    assert "Classify the company and role type" in prompt
    assert "BULLET 1 — THE PROJECT SALE" in prompt
    assert "BULLET 2 — THE ENGINEERING PROOF" in prompt
    assert "POSITIONING THESIS" in prompt
    assert "PORTFOLIO COVERAGE" in prompt
    assert "ONE-PAGE HARD LIMIT" in prompt
    assert "SELF-REVIEW" in prompt


def test_prompt_rejects_known_v36_failure_modes() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "Never use a raw profile sentence as a fallback" in prompt
    assert "A technology inventory is not" in prompt
    assert "No fragment, project name alone, passive stack inventory" in prompt
    assert "No two bullets from the same source communicate the same fact" in prompt
    assert "Never put disclaimers, missing requirements, or gap language" in prompt


def _entry(*bullets: str) -> str:
    items = "\n".join(rf"\item \small{{{bullet}}}" for bullet in bullets)
    return rf"\resumeSubheading{{Source}}{{Jun 2026 -- Present}}{{Developer}}{{BC}}\resumeItemListStart{items}\resumeItemListEnd"


def _project(*bullets: str) -> str:
    items = "\n".join(rf"\item \small{{{bullet}}}" for bullet in bullets)
    return rf"\projectSubheading{{Project | Descriptor}}{{Jun 2026 -- Present}}{{Python}}{{}}{{https://example.com}}\resumeItemListStart{items}\resumeItemListEnd"


def test_editorial_gate_accepts_complete_distinct_resume_bullets() -> None:
    body = (
        r"\section{Experience}"
        + _entry(
            "Built a scheduling workflow for retail employees, replacing manual weekly coordination with mobile shift access and dependable attendance records.",
            "Modeled planned shifts separately from actual time entries in PostgreSQL, preserving corrections without rewriting the original schedule.",
        )
        + r"\section{Projects}"
        + _project(
            "Built a transactional records service that centralizes approvals, audit history, and controlled state changes for business applications.",
            "Enforced mutations and immutable audit writes inside one transaction boundary, preventing partial records during concurrent workflow updates.",
        )
        + _project(
            "Developed a document-generation product that converts persistent candidate evidence into tailored resumes and focused cover letters.",
            "Moved long-running generation behind background workers after synchronous requests timed out, making every job recoverable after infrastructure failures.",
        )
        + r"\section{Skills}\begin{itemize}\item \textbf{Languages:} Python\end{itemize}"
    )

    assert generation._resume_quality_errors(body, "Complete candidate source text without numeric claims.") == []


def test_editorial_gate_rejects_the_exact_deployed_failure_modes() -> None:
    body = (
        r"\section{Experience}"
        + _entry(
            "Built a useful scheduling platform for employees and administrators across daily business operations.",
            "The platform was developed using Next.js, React, Node.js, PostgreSQL, and Dockerized development infrastructure.",
        )
        + r"\section{Projects}"
        + _project(
            "Transactional backend infrastructure platform serving as the authoritative source of truth for business-critical records and audit history.",
            "Ledger is a transactional backend infrastructure platform serving as the authoritative source of truth for business-critical records and audit history.",
        )
        + _project(
            "Application intelligence platform generating tailored resumes and cover letters from a persistent structured career profile for candidates.",
            "CareerOS",
        )
        + r"\section{Skills}\begin{itemize}\item \textbf{Languages:} Python\end{itemize}"
    )

    errors = generation._resume_quality_errors(body, "Next.js React Node.js PostgreSQL Docker")

    assert any("passive project or technology inventory" in error for error in errors)
    assert any("semantically repetitive" in error for error in errors)
    assert any("has 1 words" in error for error in errors)
