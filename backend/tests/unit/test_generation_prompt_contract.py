"""Contract tests for the restored original Claude generation prompt."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import worker
from app.services import generation
from app.services.llm_client import ToolCallResult


def test_worker_uses_full_context_generator() -> None:
    assert worker.generate_materials is generation.generate_materials
    assert (
        generation.GENERATION_VERSION
        == "original-v1-evidence-refined"
    )


def test_prompt_contains_the_approved_editorial_system() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "STEP 0 — Rank supported evidence before writing" in prompt
    assert "Time, work, or operational effort meaningfully reduced" in prompt
    assert "STEP 1 — Classify the JD internally" in prompt
    assert "BULLET 1 — PROJECT SALE" in prompt
    assert "BULLET 2 — ENGINEERING PROOF" in prompt
    assert "targeting 20-28 words" in prompt
    assert "Allow up to 32" in prompt
    assert "Six is a hard maximum" in prompt
    assert "Place the project with the strongest direct evidence" in prompt
    assert "Skills are not a substitute for concrete evidence" in prompt
    assert "exactly one project, named once" in prompt
    assert "Exactly 2 sentences" in prompt
    assert "Exactly 5 sentences" in prompt
    assert "Exactly 1 sentence" in prompt
    assert "name only the missing members" in prompt
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

    assert "Target 20-28 words" in prompt
    assert "32 words or fewer" in prompt
    assert "emergency acceptance margin" in prompt


def test_project_technology_lines_are_trimmed_to_six_ranked_items() -> None:
    body = (
        r"\section{Projects}"
        r"\projectSubheading{Ledger | Backend}{Jun 2026 -- Present}"
        r"{Java \textperiodcentered{} Spring Boot \textperiodcentered{} PostgreSQL "
        r"\textperiodcentered{} Spring Security \textperiodcentered{} Testcontainers "
        r"\textperiodcentered{} Docker \textperiodcentered{} Flyway \textperiodcentered{} Maven}"
        r"{}{https://example.com}"
    )

    trimmed, actions = generation._limit_project_technology_lines(body)

    assert actions == ["trimmed_project_technologies:1:8->6"]
    assert "Docker" in trimmed
    assert "Flyway" not in trimmed
    assert "Maven" not in trimmed
    arguments = generation._project_subheading_argument_spans(trimmed)
    technologies = trimmed[arguments[0][2][0]:arguments[0][2][1]]
    items, _ = generation._split_project_technologies(technologies)
    assert len(items) == 6


def test_prompt_does_not_restore_the_discarded_ultimate_prompt() -> None:
    prompt = generation.SYSTEM_PROMPT

    assert "MAXIMUM DEFENSIBLE LEVERAGE" not in prompt
    assert "POSITIONING THESIS" not in prompt
    assert "PORTFOLIO COVERAGE" not in prompt


def test_generation_tool_requires_three_projects_when_profile_supports_them() -> None:
    selected = generation._generation_tool_for_project_count(4)["input_schema"]["properties"]["selected_projects"]
    assert selected["minItems"] == 3
    assert selected["maxItems"] == 3

    selected_for_two = generation._generation_tool_for_project_count(2)["input_schema"]["properties"]["selected_projects"]
    assert selected_for_two["minItems"] == 2
    assert selected_for_two["maxItems"] == 2


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


def test_editorial_gate_accepts_complete_31_to_40_word_near_miss() -> None:
    long_but_complete = (
        "Built a scheduling and attendance workflow for retail employees and administrators, "
        "replacing weekly spreadsheet coordination with mobile shift access while preserving "
        "planned schedules separately from corrected time records in PostgreSQL for daily "
        "operational use across recurring employee workflows."
    )
    assert generation._bullet_word_count(long_but_complete) == 38

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


def test_editorial_gate_rejects_bullets_over_emergency_40_word_limit() -> None:
    excessive = (
        "Built a scheduling and attendance workflow for retail employees and administrators, "
        "replacing weekly spreadsheet coordination with mobile shift access while preserving "
        "planned schedules separately from corrected time records in PostgreSQL for daily "
        "operational use across several recurring administrative and employee workflows with "
        "documented correction history for managers."
    )
    assert generation._bullet_word_count(excessive) > 40

    body = (
        r"\section{Experience}"
        + _entry(
            excessive,
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

    errors = generation._resume_quality_errors(body, "PostgreSQL")
    assert any("expected 8-40" in error for error in errors)


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
    assert generation._bullet_word_count(shortened) <= 30


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
            "selected_projects": ["Project One", "Project Two"],
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
            "selected_projects": ["Project One", "Project Two"],
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
        tool_input={"repairs": [{"bullet_index": 1, "replacement_text": replacement}]},
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


def test_targeted_repair_escapes_latex_sensitive_characters_without_touching_list_structure() -> None:
    body = (
        r"\section{Experience}"
        + _entry(
            "Completed 100% of scheduled data exports for engineering teams during controlled validation.",
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

    repaired = generation._apply_targeted_bullet_repairs(
        body,
        [{"bullet_index": 1, "replacement_text": "Completed 100% of scheduled data exports for R&D teams."}],
    )

    assert r"100\%" in repaired
    assert r"R\&D" in repaired
    assert repaired.count(r"\resumeItemListStart") == body.count(r"\resumeItemListStart")
    assert repaired.count(r"\resumeItemListEnd") == body.count(r"\resumeItemListEnd")


def test_targeted_repair_cannot_introduce_a_new_numeric_claim() -> None:
    body = (
        r"\section{Experience}"
        + _entry(
            "Built a scheduling workflow for employees, replacing manual coordination with mobile shift access and dependable attendance records.",
            "Modeled planned shifts separately from actual time entries in PostgreSQL, preserving corrections without rewriting the original schedule.",
        )
        + r"\section{Projects}"
        + _project(
            "Built a transactional records service that centralizes approvals, audit history, and controlled state changes for business applications.",
            "Enforced mutations and audit writes inside one transaction boundary, preventing partial records during concurrent workflow updates.",
        )
        + _project(
            "Developed a document-generation product that converts candidate evidence into tailored resumes and focused cover letters.",
            "Moved long-running generation behind background workers, making interrupted jobs recoverable after infrastructure failures.",
        )
        + r"\section{Skills}\begin{itemize}\item \textbf{Languages:} Python\end{itemize}"
    )

    with pytest.raises(ValueError, match="introduced new numeric claims"):
        generation._apply_targeted_bullet_repairs(
            body,
            [{"bullet_index": 1, "replacement_text": "Completed 50 workflows at 10-way concurrency during a controlled benchmark."}],
        )


def test_editorial_gate_rejects_metrics_borrowed_from_another_project() -> None:
    body = (
        r"\section{Experience}"
        + _entry(
            "Built a scheduling workflow for employees, replacing manual coordination with mobile shift access and dependable attendance records.",
            "Modeled planned shifts separately from actual time entries in PostgreSQL, preserving corrections without rewriting the original schedule.",
        )
        + r"\section{Projects}"
        + r"\projectSubheading{Relay | Event Platform}{2026}{TypeScript}{}{https://example.com/relay}"
        + r"\resumeItemListStart"
        + r"\item \small{Built an event platform that authenticates ingestion and dispatches asynchronous work through queued serverless workers.}"
        + r"\item \small{Completed 50 workflows at 10-way concurrency during a controlled benchmark with measured end-to-end latency.}"
        + r"\resumeItemListEnd"
        + r"\projectSubheading{Ledger | Transactional Backend}{2026}{Java}{}{https://example.com/ledger}"
        + r"\resumeItemListStart"
        + r"\item \small{Built a transactional records service that centralizes approvals, audit history, and controlled state changes.}"
        + r"\item \small{Completed 50 workflows at 10-way concurrency while preserving atomic audit history during storage failures.}"
        + r"\resumeItemListEnd"
        + r"\section{Skills}\begin{itemize}\item \textbf{Languages:} Java\end{itemize}"
    )
    profile = """PROJECTS
[1] Serverless Event Platform (2026 – Present) — GitHub: https://example.com/relay
  REQUIRED RESUME HEADING — copy exactly: Relay | Event Platform
  SOURCE MATERIAL — factual evidence, not copy-ready résumé prose:
  Completed 50 workflows at 10-way concurrency during a controlled benchmark.
[2] Transactional Backend (2026 – Present) — GitHub: https://example.com/ledger
  REQUIRED RESUME HEADING — copy exactly: Ledger | Transactional Backend
  SOURCE MATERIAL — factual evidence, not copy-ready résumé prose:
  Validated atomic audit rollback across 20 contention trials.

SKILLS
Languages: Java, TypeScript"""

    errors = generation._resume_quality_errors(body, profile)

    assert any(
        "bullet 6 contains numbers absent from its project source: 10, 50" in error
        for error in errors
    )
