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


def test_prompt_contains_the_approved_editorial_system() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "STEP 0 — Rank supported evidence before writing" in prompt
    assert "Priority A: recruiter-legible scope or outcome" in prompt
    assert "STEP 1 — Classify the JD internally" in prompt
    assert "BULLET 1 — PROJECT SALE" in prompt
    assert "BULLET 2 — ENGINEERING PROOF" in prompt
    assert "target 18-28 words" in prompt
    assert "exactly one project, named once" in prompt
    assert "ONE-PAGE CONTENT BUDGET" in prompt
    assert "SELF-REVIEW" in prompt


def test_prompt_removes_stale_project_and_keyword_rules() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "Generate a descriptor for every selected project" not in prompt
    assert "Select 2-4 projects" not in prompt
    assert "Extract 10-15 JD terms" not in prompt
    assert generation.GENERATE_TOOL["input_schema"]["properties"]["selected_projects"]["maxItems"] == 3


def test_quality_repair_prompt_keeps_margin_below_validator_ceiling() -> None:
    prompt = generation._QUALITY_REPAIR_SYSTEM

    assert "Target 16-24 words per bullet" in prompt
    assert "keep every bullet at 30 words or fewer" in prompt
    assert "validator's ceiling is 32, not a writing target" in prompt


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


def test_editorial_gate_accepts_equivalent_numeric_wording() -> None:
    body = (
        r"\section{Experience}"
        + _entry(
            "Owned applicant workflow delivery within a 6-person team, replacing manual coordination for more than 10 recurring application steps.",
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

    profile = "Owned the workflow in a six-person team and replaced 10+ recurring application steps."

    assert generation._resume_quality_errors(body, profile) == []


def test_editorial_gate_treats_33_to_36_words_as_soft_style_range() -> None:
    long_but_complete = (
        "Built a scheduling and attendance workflow for retail employees and administrators, "
        "replacing weekly spreadsheet coordination with mobile shift access while preserving "
        "planned schedules separately from corrected time records in PostgreSQL for daily "
        "operational use."
    )
    assert 33 <= generation._bullet_word_count(long_but_complete) <= 36

    body = (
        r"\section{Experience}"
        + _entry(
            long_but_complete,
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

    assert generation._resume_quality_errors(body, "PostgreSQL") == []


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
    assert generation._bullet_word_count(shortened) <= 32


def test_local_recovery_refuses_arbitrary_mid_clause_truncation() -> None:
    overlong = "Built " + " ".join(f"component{index}" for index in range(1, 41)) + "."
    assert generation._bullet_word_count(overlong) == 41

    assert generation._shorten_overlong_bullet(overlong) is None


def test_local_recovery_removes_filler_without_damaging_grammar() -> None:
    text = "Built a reliable, robust, scalable service and a modular and reusable client."

    assert generation._remove_low_value_bullet_words(text) == (
        "Built a reliable service and a client."
    )


async def test_generation_pipeline_fixes_punctuation_locally_without_repair() -> None:
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
    async def keep_compiled_body(assembled, *_args, **_kwargs):
        return assembled, 0, []

    with patch("app.services.generation.get_llm_client", return_value=llm), \
         patch("app.services.generation._repair_resume_quality", AsyncMock()) as repair_mock, \
         patch("app.services.generation._compress_if_needed", side_effect=keep_compiled_body):
        result = await generation.generate_materials(db, "Software Engineer with Python", "sk-ant-test")

    repair_mock.assert_not_awaited()
    llm.call_tool.assert_awaited_once()
    assert result["generation_metadata"]["quality_repair_attempts"] == 0
    assert result["generation_metadata"]["local_editorial_rescue_actions"] == [
        "added_punctuation:1"
    ]
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 50
    assert generation._resume_quality_errors(result["resume_latex"], "") == []


async def test_generation_pipeline_applies_targeted_repair_without_rewriting_passing_bullets() -> None:
    passing_bullet = (
        "Modeled planned shifts separately from actual time entries in PostgreSQL, "
        "preserving corrections without rewriting the original schedule."
    )
    initial_body = (
        r"\section{Experience}"
        + _entry(
            "The platform was developed using Next.js, React, Node.js, PostgreSQL, and Docker infrastructure.",
            passing_bullet,
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
    replacement = (
        "Built a scheduling workflow for retail employees, replacing manual weekly "
        "coordination with mobile shift access and dependable attendance records."
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
        tool_input={"repairs": [{"bullet_index": 1, "replacement_latex": replacement}]},
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
    assert result["generation_metadata"]["quality_repair_attempts"] == 1
    assert replacement in result["resume_latex"]
    assert passing_bullet in result["resume_latex"]
    assert result["input_tokens"] == 120
    assert result["output_tokens"] == 60
