"""Contract tests for the restored original Claude generation prompt."""

from app import worker
from app.services import generation


def test_worker_uses_full_context_generator() -> None:
    assert worker.generate_materials is generation.generate_materials
    assert generation.GENERATION_VERSION == "original-prompt-v1-quality-gated"


def test_prompt_restores_original_claude_editorial_system() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "STEP 0 — Extract and tier all metrics" in prompt
    assert "TIER 1 — Always include" in prompt
    assert "STEP 1 — Classify the company and role type. State it explicitly." in prompt
    assert "BULLET 1 — THE PROJECT SALE" in prompt
    assert "BULLET 2 — THE ENGINEERING PROOF" in prompt
    assert "Target 12-16 words per bullet" in prompt
    assert "One project at genuine technical depth" in prompt
    assert "ONE-PAGE HARD LIMIT" in prompt
    assert "SELF-REVIEW" in prompt


def test_prompt_does_not_contain_later_ultimate_prompt_rewrite() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "MAXIMUM DEFENSIBLE LEVERAGE" not in prompt
    assert "POSITIONING THESIS" not in prompt
    assert "PORTFOLIO COVERAGE" not in prompt
    assert "Target 18-26 words per bullet" not in prompt


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
