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
    assert generation.GENERATION_VERSION == "ultimate-prompt-v1"


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
