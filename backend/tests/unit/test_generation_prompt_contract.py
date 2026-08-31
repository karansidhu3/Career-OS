"""Contract tests for the restored original Claude generation prompt."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app import worker
from app.services import generation
from app.services.llm_client import ToolCallResult


def test_worker_uses_full_context_generator() -> None:
    assert worker.generate_materials is generation.generate_materials
    assert (
        generation.GENERATION_VERSION
        == "original-v1-qg-local-recovery"
    )


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


def test_quality_repair_prompt_keeps_margin_below_validator_ceiling() -> None:
    prompt = generation._QUALITY_REPAIR_SYSTEM

    assert "Target 16-24 words per bullet" in prompt
    assert "keep every bullet at 30 words or fewer" in prompt
    assert "emergency ceiling is 38, not a writing target" in prompt


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


def test_local_recovery_shortens_exact_40_word_production_failure() -> None:
    overlong = (
        "Architected a Redis-backed generation queue that moved document compilation "
        "outside the request lifecycle and preserved application state across worker "
        "retries, reducing initial feedback latency while preventing proxy timeouts "
        "during long-running resume and cover-letter generation requests across all "
        "submitted production jobs."
    )
    assert generation._bullet_word_count(overlong) == 40

    body = (
        r"\section{Experience}"
        + _entry(
            overlong,
            "Modeled planned shifts separately from actual time entries in PostgreSQL, preserving corrections without rewriting the original schedule.",
        )
        + r"\section{Projects}"
        + _project(
            "Built a transactional records service that centralizes approvals, audit history, and controlled state changes for business applications.",
            "Enforced mutations and audit writes inside one transaction boundary, preventing partial records during concurrent workflow updates.",
        )
        + _project(
            "Developed a document-generation product that converts persistent candidate evidence into tailored resumes and focused cover letters.",
            "Moved long-running generation behind background workers after synchronous requests timed out, making interrupted jobs recoverable.",
        )
        + r"\section{Skills}\begin{itemize}\item \textbf{Languages:} Python\end{itemize}"
    )

    recovered, actions = generation._recover_overlong_bullets(body)

    assert actions == ["shortened_bullet:1:40->20"]
    assert "reducing initial feedback latency" not in recovered
    assert generation._resume_quality_errors(
        recovered,
        "Redis PostgreSQL candidate source text without numeric claims.",
    ) == []


def test_local_recovery_preserves_latex_special_characters() -> None:
    overlong = (
        "Built C# billing controls that reconciled 100% of recorded account events "
        "inside one auditable transaction boundary for finance operators, replacing "
        "manual exception handling with a comprehensive recovery path that preserved "
        "every accepted payment record during controlled database fault injection trials."
    )
    assert generation._bullet_word_count(overlong) > 38

    shortened = generation._shorten_overlong_bullet(overlong)

    assert shortened is not None
    assert r"C\#" in shortened
    assert r"100\%" in shortened
    assert generation._bullet_word_count(shortened) <= 38


def test_local_recovery_refuses_arbitrary_mid_clause_truncation() -> None:
    overlong = "Built " + " ".join(f"component{index}" for index in range(1, 41)) + "."
    assert generation._bullet_word_count(overlong) == 41

    assert generation._shorten_overlong_bullet(overlong) is None


def test_local_recovery_removes_filler_without_damaging_grammar() -> None:
    text = "Built a reliable, robust, scalable service and a modular and reusable client."

    assert generation._remove_low_value_bullet_words(text) == (
        "Built a reliable service and a client."
    )


async def test_generation_pipeline_recovers_repaired_overflow_without_third_call() -> None:
    valid_body = (
        r"\section{Experience}"
        + _entry(
            "Built a scheduling workflow for retail employees, replacing manual weekly coordination with mobile shift access and dependable attendance records.",
            "Modeled planned shifts separately from actual time entries in PostgreSQL, preserving corrections without rewriting the original schedule.",
        )
        + r"\section{Projects}"
        + _project(
            "Built a transactional records service that centralizes approvals, audit history, and controlled state changes for business applications.",
            "Enforced mutations and audit writes inside one transaction boundary, preventing partial records during concurrent workflow updates.",
        )
        + _project(
            "Developed a document-generation product that converts persistent candidate evidence into tailored resumes and focused cover letters.",
            "Moved long-running generation behind background workers after synchronous requests timed out, making interrupted jobs recoverable.",
        )
        + r"\section{Skills}\begin{itemize}\item \textbf{Languages:} Python\end{itemize}"
    )
    initial_body = valid_body.replace("dependable attendance records.", "dependable attendance records")
    overlong = (
        "Architected a Redis-backed generation queue that moved document compilation "
        "outside the request lifecycle and preserved application state across worker "
        "retries, reducing initial feedback latency while preventing proxy timeouts "
        "during long-running resume and cover-letter generation requests across all "
        "submitted production jobs."
    )
    repaired_body = valid_body.replace(
        "Built a scheduling workflow for retail employees, replacing manual weekly coordination with mobile shift access and dependable attendance records.",
        overlong,
    )

    empty_rows = MagicMock()
    empty_rows.scalars.return_value.all.return_value = []
    no_personal = MagicMock()
    no_personal.scalar_one_or_none.return_value = None
    db = SimpleNamespace(execute=AsyncMock(side_effect=[no_personal, empty_rows, empty_rows, empty_rows, empty_rows]))
    llm = SimpleNamespace(call_tool=AsyncMock(return_value=ToolCallResult(
        tool_input={
            "selected_projects": ["Project"],
            "fit_score": 7,
            "resume_latex": initial_body,
            "cover_letter": "Focused cover letter.",
            "job_title": "Software Engineer",
            "job_company": "Acme",
            "strategic_note": "GOOD FIT\n• Python\n\nGAPS\n• None\n\nIMPROVEMENT PLAN\n• Continue",
        },
        input_tokens=100,
        output_tokens=50,
    )))
    repaired = ToolCallResult(
        tool_input={"resume_latex": repaired_body},
        input_tokens=20,
        output_tokens=10,
    )

    async def keep_compiled_body(assembled, *_args, **_kwargs):
        return assembled, 0, []

    with patch("app.services.generation.get_llm_client", return_value=llm), \
         patch("app.services.generation._repair_resume_quality", AsyncMock(return_value=repaired)) as repair_mock, \
         patch("app.services.generation._compress_if_needed", side_effect=keep_compiled_body):
        result = await generation.generate_materials(db, "Software Engineer with Python", "sk-ant-test")

    repair_mock.assert_awaited_once()
    llm.call_tool.assert_awaited_once()
    assert result["generation_metadata"]["quality_repair_attempts"] == 1
    assert result["generation_metadata"]["local_editorial_rescue_actions"] == [
        "shortened_bullet:1:40->20"
    ]
    assert result["input_tokens"] == 120
    assert result["output_tokens"] == 60
    assert generation._resume_quality_errors(result["resume_latex"], "") == []
