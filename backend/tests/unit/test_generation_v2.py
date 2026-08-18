from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.candidacy_insights import synthesize_insight
from app.services.generation_v2 import (
    _WRITER_SCHEMA,
    WriterValidationError,
    _availability_context,
    _bounded_complete_prose,
    _candidate_ids,
    _compact_profile_bank,
    _cover_story_errors,
    _eligible_experiences,
    _experience_display_role,
    _fallback_cover_letter,
    _locally_repair_bullets,
    _merge_repair,
    _metric_tier,
    _narrow_repair_payload,
    _normalize_generated_prose,
    _project_display_name,
    _project_capacity,
    _project_selection_card,
    _rank_project_ids,
    _recover_writer,
    _render_body,
    _validate_bullet,
    _validate_plan,
    _validated_cover,
    _validate_writer,
)
from app.services.llm_client import AnthropicAdapter, StructuredOutputTruncatedError, ToolCallResult
from app.services.llm_cost import calculate_llm_cost
from app.services.profile_fact_bank import FACT_BANK_VERSION, _evidence_fragments, _source_payload, _validate_bank, get_or_build_fact_bank, profile_hash


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def test_cost_ledger_prices_each_token_class_without_double_counting():
    usage = ToolCallResult(tool_input={}, input_tokens=1_000, output_tokens=1_000, cache_read_tokens=1_000, cache_write_tokens=1_000)
    assert calculate_llm_cost("claude-sonnet-4-6", usage) == pytest.approx(0.02205)
    assert calculate_llm_cost("claude-haiku-4-5", usage) == pytest.approx(0.00735)


def test_metric_tiers_prefer_legible_outcomes_over_vanity_counts():
    assert _metric_tier("Replaced spreadsheet scheduling for 15-30 employees.") == 1
    assert _metric_tier("Validated 123 tests through Testcontainers.") == 2
    assert _metric_tier("Implemented 29 endpoints, 47 migrations, and 4,083 lines of code.") == 3


def test_compact_profile_bank_keeps_source_context_without_duplicate_evidence_fields():
    bank = {"version": "3", "skills": {"Languages": ["Python"]}, "sources": [{
        "source_key": "project:1", "type": "project", "name": "CareerOS", "display_name": "CareerOS",
        "facts": [
            {"id": "project:1:0", "statement": "Application generator.", "evidence": "Application generator.", "technologies": []},
            {"id": "project:1:1", "statement": "Reduced feedback to 1 second.", "evidence": "Reduced feedback to 1 second.", "technologies": ["Python"]},
        ],
    }]}

    compact = _compact_profile_bank(bank)

    assert compact["sources"][0]["facts"][0]["text"] == "Application generator."
    assert "statement" not in compact["sources"][0]["facts"][0]
    assert "evidence" not in compact["sources"][0]["facts"][0]


def test_candidate_ranking_prefers_role_relevance_over_number_density():
    projects = [ns(id=1), ns(id=2)]
    skills = [ns(items=["Python", "FastAPI", "Java"])]
    bank = {"sources": [
        {"source_key": "project:1", "name": "Ledger", "facts": [
            {"id": "project:1:0", "evidence": "Implemented 29 endpoints, 47 migrations, and 4,083 lines of Java.", "technologies": ["Java"]},
        ]},
        {"source_key": "project:2", "name": "CareerOS", "facts": [
            {"id": "project:2:0", "evidence": "Built a Python FastAPI application generator replacing 30 minutes of manual tailoring.", "technologies": ["Python", "FastAPI"]},
        ]},
    ]}

    _, ranked = _candidate_ids(bank, [], projects, "Python and FastAPI platform engineering", skills)

    assert ranked[0] == 2


def test_project_selector_uses_role_weighted_canonical_ordering():
    skills = ["Python", "FastAPI", "PostgreSQL", "Java", "Spring Boot", "AWS", "Linux"]
    bank = {"sources": [
        {"source_key": "project:1", "name": "CareerOS", "facts": [
            {"id": "project:1:0", "evidence": "Built a Python FastAPI backend service and APIs that replaced a 30 minute manual application workflow for users.", "technologies": ["Python", "FastAPI"]},
            {"id": "project:1:1", "evidence": "Moved synchronous generation to async workers after 30 second timeouts, improving reliability and feedback latency.", "technologies": ["Python"]},
        ]},
        {"source_key": "project:2", "name": "Ledger", "facts": [
            {"id": "project:2:0", "evidence": "Designed Java Spring Boot REST APIs with PostgreSQL transactions and authentication for financial operations.", "technologies": ["Java", "Spring Boot", "PostgreSQL"]},
            {"id": "project:2:1", "evidence": "Validated backend correctness with 92 unit tests and 31 PostgreSQL integration tests.", "technologies": ["Java", "PostgreSQL"]},
        ]},
        {"source_key": "project:3", "name": "MarketMind", "facts": [
            {"id": "project:3:0", "evidence": "Built a Python FastAPI AI data pipeline ingesting filings for investment research users.", "technologies": ["Python", "FastAPI"]},
            {"id": "project:3:1", "evidence": "Orchestrated model pipelines with vector search and PostgreSQL.", "technologies": ["Python", "PostgreSQL"]},
        ]},
        {"source_key": "project:4", "name": "Relay", "facts": [
            {"id": "project:4:0", "evidence": "Built serverless AWS event-driven infrastructure with asynchronous queues and workers for three production applications.", "technologies": ["AWS"]},
            {"id": "project:4:1", "evidence": "Designed retries and dead-letter handling after synchronous timeouts failed.", "technologies": ["AWS"]},
        ]},
    ]}
    jd = (
        "Canonical seeks a Python backend engineer to build and maintain FastAPI REST APIs on Linux, "
        "design reliable services, test database integrations, and troubleshoot production operations."
    )

    ranked, scorecards = _rank_project_ids([1, 2, 3, 4], bank, jd, skills)

    assert ranked == [1, 2, 3, 4]
    assert scorecards[0]["role_relevance"] > scorecards[1]["role_relevance"]
    assert scorecards[1]["responsibility_proof"] > scorecards[2]["responsibility_proof"]


def test_project_score_total_uses_agreed_component_weights():
    source = {"source_key": "project:1", "name": "CareerOS", "facts": [{
        "id": "project:1:0",
        "evidence": "Built a Python FastAPI backend service that replaced manual work for users after synchronous timeouts failed.",
        "technologies": ["Python", "FastAPI"],
    }]}

    card = _project_selection_card(
        1,
        source,
        "Build reliable Python FastAPI backend APIs and troubleshoot production failures.",
        ["Python", "FastAPI"],
        [],
    )

    expected = (
        (0.35 * card["role_relevance"])
        + (0.25 * card["responsibility_proof"])
        + (0.20 * card["outcome_value"])
        + (0.15 * card["engineering_depth"])
        + (0.05 * card["distinctiveness"])
    )
    assert card["total"] == pytest.approx(expected, abs=0.01)


def test_project_selector_rewards_marginal_job_coverage_after_first_choice():
    bank = {"sources": [
        {"source_key": "project:1", "name": "Primary API", "facts": [{
            "id": "project:1:0", "evidence": "Built Python FastAPI backend APIs with PostgreSQL transactions for users, replacing manual processing.",
        }]},
        {"source_key": "project:2", "name": "Duplicate API", "facts": [{
            "id": "project:2:0", "evidence": "Built Python FastAPI backend APIs with PostgreSQL transactions for users, replacing manual processing.",
        }]},
        {"source_key": "project:3", "name": "Security API", "facts": [{
            "id": "project:3:0", "evidence": "Built Python FastAPI authentication and authorization controls with security tests for users.",
        }]},
    ]}
    jd = "Build Python FastAPI backend APIs with PostgreSQL, authentication, authorization, security, and automated testing."

    ranked, scorecards = _rank_project_ids(
        [1, 2, 3],
        bank,
        jd,
        ["Python", "FastAPI", "PostgreSQL"],
    )

    assert ranked[:2] == [1, 3]
    assert scorecards[1]["distinctiveness"] > scorecards[2]["distinctiveness"]


def test_anthropic_transforms_unsupported_writer_schema_constraints():
    """The raw schema keeps CareerOS's exact business rule, while the schema
    sent to Anthropic must use only constraints its grammar compiler accepts."""
    import anthropic

    raw = _WRITER_SCHEMA["properties"]["cover_letter_paragraphs"]
    provider = anthropic.transform_schema(_WRITER_SCHEMA)["properties"]["cover_letter_paragraphs"]

    assert raw["minItems"] == 3
    assert raw["maxItems"] == 3
    assert "minItems" not in provider
    assert "maxItems" not in provider
    assert "minItems: 3" in provider["description"]


@pytest.mark.asyncio
async def test_structured_call_sends_the_transformed_schema(monkeypatch):
    create = AsyncMock(return_value=ns(
        content=[ns(type="text", text='{"ok": true}')],
        usage=ns(
            input_tokens=1,
            output_tokens=1,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        ),
    ))
    client = ns(messages=ns(create=create))
    monkeypatch.setattr("app.services.llm_client.anthropic.AsyncAnthropic", lambda api_key: client)

    await AnthropicAdapter("test-key").call_structured(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system="Return JSON.",
        messages=[{"role": "user", "content": "test"}],
        schema=_WRITER_SCHEMA,
        timeout=1.0,
    )

    sent_schema = create.await_args.kwargs["output_config"]["format"]["schema"]
    paragraphs = sent_schema["properties"]["cover_letter_paragraphs"]
    assert "minItems" not in paragraphs
    assert "maxItems" not in paragraphs


@pytest.mark.asyncio
async def test_structured_call_reports_output_budget_exhaustion(monkeypatch):
    create = AsyncMock(return_value=ns(
        content=[ns(type="text", text='{"unfinished":')],
        stop_reason="max_tokens",
        usage=ns(input_tokens=1, output_tokens=100),
    ))
    client = ns(messages=ns(create=create))
    monkeypatch.setattr("app.services.llm_client.anthropic.AsyncAnthropic", lambda api_key: client)

    with pytest.raises(StructuredOutputTruncatedError, match="100-token") as exc:
        await AnthropicAdapter("test-key").call_structured(
            model="claude-sonnet-4-6",
            max_tokens=100,
            system="Return JSON.",
            messages=[{"role": "user", "content": "test"}],
            schema={"type": "object"},
            timeout=1.0,
        )

    assert exc.value.usage.output_tokens == 100


def test_profile_hash_is_stable_across_dictionary_order():
    assert profile_hash({"b": 2, "a": 1}) == profile_hash({"a": 1, "b": 2})


def test_fact_bank_drops_claim_without_verbatim_evidence():
    payload = {"sources": [{"source_key": "project:7", "type": "project", "name": "Relay", "description": "Built a Redis queue handling 500 jobs/day."}], "skills": {}}
    raw = {"sources": [{"source_key": "project:7", "summary": "Queue", "facts": [
        {"statement": "Handled one million jobs", "evidence": "one million jobs", "tags": [], "technologies": ["Redis"]},
        {"statement": "Redis queue handled 500 jobs/day", "evidence": "Redis queue handling 500 jobs/day", "tags": ["backend"], "technologies": ["Redis"]},
    ]}]}
    bank = _validate_bank(raw, payload)
    assert len(bank["sources"][0]["facts"]) == 1
    assert "500" in bank["sources"][0]["facts"][0]["evidence"]


def test_fact_bank_retains_late_high_signal_evidence_from_long_profiles():
    filler = [f"Documented routine implementation detail number {index}." for index in range(18)]
    description = " ".join(filler + ["Validated 123 automated tests and reduced queue latency by 40%."])

    fragments = _evidence_fragments(description)

    assert len(fragments) == 12
    assert any("123 automated tests" in fragment for fragment in fragments)


def test_plan_rejects_unknown_project_fact_and_skill_ids():
    projects = [ns(id=1), ns(id=2)]
    skills = [ns(items=["Python", "FastAPI"])]
    bank = {"sources": [
        {"source_key": "project:1", "facts": [{"id": "project:1:0"}]},
        {"source_key": "project:2", "facts": [{"id": "project:2:0"}]},
    ]}
    plan = _validate_plan({
        "selected_project_ids": [999, 1], "selected_fact_ids": ["made-up", "project:1:0"],
        "selected_skills": ["Rust", "python"], "gaps": [], "matches": [],
    }, bank, projects, skills)
    assert plan["selected_project_ids"] == [1, 2]
    assert plan["selected_fact_ids"] == ["project:1:0"]
    assert plan["selected_skills"] == ["Python"]


def test_plan_restores_three_project_density_and_ranks_missing_slot_by_jd():
    projects = [ns(id=1), ns(id=2), ns(id=3), ns(id=4)]
    skills = [ns(items=["Python", "FastAPI", "React"])]
    bank = {"sources": [
        {"source_key": "project:1", "name": "Relay", "facts": [{"id": "project:1:0", "evidence": "Built an AWS event queue."}]},
        {"source_key": "project:2", "name": "Portfolio", "facts": [{"id": "project:2:0", "evidence": "Built a React landing page."}]},
        {"source_key": "project:3", "name": "CareerOS", "facts": [{"id": "project:3:0", "evidence": "Built Python FastAPI APIs with PostgreSQL."}]},
        {"source_key": "project:4", "name": "Other", "facts": [{"id": "project:4:0", "evidence": "Created a visualization."}]},
    ]}

    plan = _validate_plan(
        {"selected_project_ids": [1], "selected_fact_ids": [], "selected_skills": [], "gaps": [], "matches": []},
        bank,
        projects,
        skills,
        "Python web APIs using FastAPI and PostgreSQL",
    )

    assert plan["selected_project_ids"] == [1, 3, 2]
    assert plan["selected_skills"] == ["Python", "FastAPI", "React"]


def test_plan_defaults_to_three_projects_even_when_writer_returns_four():
    projects = [ns(id=value) for value in (1, 2, 3, 4)]
    bank = {"sources": [
        {"source_key": f"project:{value}", "facts": [{"id": f"project:{value}:0", "evidence": f"Built project {value}."}]}
        for value in (1, 2, 3, 4)
    ]}

    plan = _validate_plan(
        {"selected_project_ids": [1, 2, 3, 4], "selected_skills": [], "matches": [], "gaps": []},
        bank,
        projects,
        [],
    )

    assert plan["selected_project_ids"] == [1, 2, 3]


def test_plan_preserves_fourth_project_only_when_capacity_allows_it():
    projects = [ns(id=value) for value in (1, 2, 3, 4)]
    bank = {"sources": [
        {"source_key": f"project:{value}", "facts": [{"id": f"project:{value}:0", "evidence": f"Built project {value}."}]}
        for value in (1, 2, 3, 4)
    ]}

    plan = _validate_plan(
        {"selected_project_ids": [1, 2, 3, 4], "selected_skills": [], "matches": [], "gaps": []},
        bank,
        projects,
        [],
        project_limit=4,
    )

    assert plan["selected_project_ids"] == [1, 2, 3, 4]


def test_plan_enforces_deterministic_project_recommendation_over_model_choice():
    projects = [ns(id=value) for value in (1, 2, 3, 4)]
    bank = {"sources": [
        {"source_key": f"project:{value}", "facts": [{
            "id": f"project:{value}:0",
            "evidence": f"Built project {value}.",
        }]}
        for value in (1, 2, 3, 4)
    ]}

    plan = _validate_plan(
        {"selected_project_ids": [4, 3, 2], "selected_skills": [], "matches": [], "gaps": []},
        bank,
        projects,
        [],
        project_limit=3,
        preferred_project_ids=[1, 2, 3],
    )

    assert plan["selected_project_ids"] == [1, 2, 3]


def test_project_capacity_keeps_two_experience_resume_at_three_projects():
    experiences = [ns(id=10), ns(id=11)]
    projects = [ns(id=value) for value in (1, 2, 3, 4)]
    bank = {"sources": [
        {"source_key": f"experience:{eid}", "facts": [
            {"id": f"experience:{eid}:0", "source_key": f"experience:{eid}"},
            {"id": f"experience:{eid}:1", "source_key": f"experience:{eid}"},
        ]}
        for eid in (10, 11)
    ]}

    assert _project_capacity(bank, experiences, projects) == 3


def test_project_capacity_allows_four_with_one_normal_experience():
    experiences = [ns(id=10)]
    projects = [ns(id=value) for value in (1, 2, 3, 4)]
    bank = {"sources": [{
        "source_key": "experience:10",
        "facts": [
            {"id": "experience:10:0", "source_key": "experience:10"},
            {"id": "experience:10:1", "source_key": "experience:10"},
        ],
    }]}

    assert _project_capacity(bank, experiences, projects) == 4
    assert _project_capacity(bank, experiences, projects, "custom") == 3


def test_plan_does_not_select_one_letter_skill_from_incidental_text():
    skills = [ns(items=["R", "Python"])]

    plan = _validate_plan(
        {"selected_project_ids": [], "selected_skills": [], "matches": [], "gaps": []},
        {"sources": [], "skills": {"Languages": ["R", "Python"]}},
        [],
        skills,
        "Build reliable Python services for our recruiting platform.",
    )

    assert plan["selected_skills"] == ["Python"]


def test_plan_keeps_compound_framework_gap_and_replaces_resume_spin_with_real_action():
    bank = {"sources": [], "skills": {"Languages": ["Python"]}}
    plan = _validate_plan({
        "selected_project_ids": [],
        "selected_fact_ids": [],
        "selected_skills": ["Python"],
        "matches": [],
        "gaps": [{
            "key": "flask-django",
            "label": "Flask or Django experience",
            "action": "Highlight Python patterns to signal readiness for Flask.",
        }],
    }, bank, [], [ns(items=["Python"])])

    assert plan["gaps"][0]["label"] == "Flask or Django experience"
    assert plan["gaps"][0]["action"] == (
        "Build and deploy a Flask or Django REST service with PostgreSQL, authentication, and automated tests."
    )


def test_generated_prose_repairs_em_dash_spacing_without_damaging_numeric_commas():
    text = "Three applications—CareerOS, TimeKeep, and MarketMind—orchestrate 4,083 records."

    assert _normalize_generated_prose(text) == (
        "Three applications, CareerOS, TimeKeep, and MarketMind, orchestrate 4,083 records."
    )


def test_cover_validation_applies_the_same_punctuation_normalization():
    facts = {"project:1:0": {
        "evidence": "Built CareerOS as an application platform.",
        "source_name": "CareerOS",
        "source_display_name": "CareerOS",
        "source_brand_name": "CareerOS",
        "source_type": "project",
    }}
    raw = {
        "cover_letter_paragraphs": [
            "Building fleet tooling—spanning security and automation—requires backend discipline.",
            "I built CareerOS—an application platform—and made failures visible.",
            "I am available now.",
        ],
        "cover_letter_fact_ids": ["project:1:0"],
    }

    paragraphs, _, errors = _validated_cover(raw, facts, "", enforce_style=False)

    assert errors == []
    assert paragraphs[0] == "Building fleet tooling, spanning security and automation, requires backend discipline."
    assert paragraphs[1] == "I built CareerOS, an application platform, and made failures visible."


def test_cover_story_accepts_one_problem_decision_and_result_with_two_metrics():
    paragraph = (
        "In CareerOS, synchronous generation failed at 30 seconds. I moved document work to "
        "background workers, which reduced time-to-first-feedback to under 1 second."
    )

    assert _cover_story_errors(paragraph) == []


def test_cover_story_rejects_more_than_two_metrics():
    paragraph = (
        "In CareerOS, synchronous generation failed at 30 seconds. I moved document work to "
        "4 background workers, which reduced time-to-first-feedback to under 1 second."
    )

    assert "cover letter second paragraph contains more than 2 numeric metrics" in _cover_story_errors(paragraph)


def test_cover_story_rejects_test_suite_inventory():
    paragraph = (
        "In CareerOS, unreliable releases created a testing constraint. I introduced 269 backend "
        "tests and 43 frontend unit tests, which prevented regressions."
    )

    assert "cover letter second paragraph enumerates test suites" in _cover_story_errors(paragraph)


def test_cover_rejects_a_second_named_and_cited_project():
    facts = {
        "project:1:0": {
            "evidence": "Moved synchronous generation to workers after timeouts failed.",
            "source_key": "project:1",
            "source_name": "CareerOS",
            "source_display_name": "CareerOS",
            "source_brand_name": "CareerOS",
            "source_type": "project",
        },
        "project:2:0": {
            "evidence": "Reduced manual financial reconciliation in Ledger.",
            "source_key": "project:2",
            "source_name": "Ledger",
            "source_display_name": "Ledger",
            "source_brand_name": "Ledger",
            "source_type": "project",
        },
    }
    raw = {
        "cover_letter_paragraphs": [
            "The backend role centers on reliable asynchronous processing and practical systems judgment.",
            (
                "In CareerOS, synchronous generation failed under timeouts, so I moved document work to "
                "background workers and preserved a responsive request path. I also reduced manual financial "
                "reconciliation in Ledger, demonstrating a second product context."
            ),
            "My degree is complete, and I am available now to discuss the role.",
        ],
        "cover_letter_fact_ids": ["project:1:0", "project:2:0"],
    }

    _, _, errors = _validated_cover(raw, facts, "")

    assert "cover letter cites more than one profile source" in errors
    assert "cover letter second paragraph names more than one project" in errors


def test_fallback_cover_avoids_metric_and_test_suite_inventory():
    bank = {"sources": [{
        "source_key": "project:1",
        "name": "CareerOS",
        "display_name": "CareerOS",
        "facts": [
            {
                "id": "project:1:0",
                "evidence": "Synchronous generation failed at 30 seconds, so workers reduced feedback to under 1 second.",
            },
            {
                "id": "project:1:1",
                "evidence": "Validated releases with 269 backend tests and 43 frontend unit tests.",
            },
        ],
    }]}

    paragraphs, fact_ids = _fallback_cover_letter(
        {"company": "Acme", "job_title": "Backend Engineer"},
        bank,
        [1],
    )

    assert fact_ids == ["project:1:0"]
    assert "269" not in paragraphs[1]
    assert "frontend unit tests" not in paragraphs[1]


def test_complete_prose_uses_a_real_clause_boundary_instead_of_slicing_words():
    action = (
        "Build a Flask service and publish it; extend an existing backend using the framework "
        "to produce citable evidence for future applications"
    )

    assert _bounded_complete_prose(action, 12) == "Build a Flask service and publish it."
    assert _bounded_complete_prose("Build a service using the", 12) == ""


def test_plan_replaces_canonical_gap_failures_with_complete_deliverables():
    bank = {"sources": [], "skills": {}}
    plan = _validate_plan({
        "selected_project_ids": [],
        "selected_skills": [],
        "matches": [],
        "gaps": [
            {
                "key": "python-web-frameworks",
                "label": "No demonstrated experience with Python web frameworks (Flask or Django)",
                "action": "Build a small Flask or Django REST service and publish it; extend an existing project's backend using one of these frameworks to produce citable",
            },
            {
                "key": "linux-ubuntu-platform",
                "label": "No explicit Ubuntu or Linux development and deployment experience cited",
                "action": "Develop and document a project using Ubuntu as the primary development platform; deploy a service to an Ubuntu server and include it in the",
            },
            {
                "key": "open-source-contribution",
                "label": "No open source contribution history referenced",
                "action": "Build a small, demonstrable project using No open source contribution history referenced, then document its architecture, tests, and result.",
            },
        ],
    }, bank, [], [])

    actions = [gap["action"] for gap in plan["gaps"]]
    assert actions == [
        "Build a small Flask or Django REST service and publish it.",
        "Develop and document a project using Ubuntu as the primary development platform.",
        "Contribute a tested fix or documentation improvement to a public repository and link the accepted pull request.",
    ]
    assert all(action.endswith(".") for action in actions)
    assert all("using No" not in action for action in actions)


def test_plan_recovers_single_source_positive_match_when_model_matches_are_rejected():
    projects = [ns(id=15)]
    skills = [ns(items=["Python", "FastAPI", "PostgreSQL"])]
    bank = {"sources": [{
        "source_key": "project:15",
        "type": "project",
        "name": "CareerOS",
        "display_name": "CareerOS | Application Intelligence Platform",
        "facts": [{
            "id": "project:15:0",
            "statement": "Built a Python FastAPI service with PostgreSQL.",
            "evidence": "Built a Python FastAPI service with PostgreSQL.",
            "technologies": ["Python", "FastAPI", "PostgreSQL"],
        }],
    }], "skills": {"Languages": ["Python"], "Frameworks": ["FastAPI"], "Databases": ["PostgreSQL"]}}

    plan = _validate_plan({
        "selected_project_ids": [15],
        "selected_skills": ["Python", "FastAPI", "PostgreSQL"],
        "matches": [],
        "gaps": [],
    }, bank, projects, skills, "Build Python backend services with PostgreSQL and REST APIs")

    assert plan["matches"] == [{
        "text": "CareerOS | Application Intelligence Platform: Built a Python FastAPI service with PostgreSQL.",
        "fact_ids": ["project:15:0"],
    }]


def test_bullet_rejects_number_not_present_in_cited_evidence():
    facts = {"project:1:0": {"evidence": "Processed 100 records", "statement": "Processed 100 records"}}
    assert _validate_bullet({"text": "Processed 10,000 records using Python", "fact_ids": ["project:1:0"]}, facts, "project:1:") is None


def test_writer_error_explains_exact_rejections_for_repair():
    bank = {"skills": {}, "sources": [{
        "source_key": "project:1", "name": "Relay", "type": "project",
        "facts": [
            {"id": "project:1:0", "statement": "Processed 100 records with Redis.", "evidence": "Processed 100 records with Redis."},
            {"id": "project:1:1", "statement": "Built a durable background queue.", "evidence": "Built a durable background queue."},
        ],
    }]}
    raw = {
        "experience_entries": [],
        "project_entries": [{"project_id": 1, "bullets": [
            {"text": "Processed 999 records with Redis in a durable production queue", "fact_ids": ["project:1:0"]},
            {"text": "Built queue", "fact_ids": ["project:1:1"]},
        ]}],
        "cover_letter_paragraphs": ["I am excited about this role.", "Relevant work.", "Thank you."],
        "cover_letter_fact_ids": [],
        "fit_score": 80,
    }

    with pytest.raises(WriterValidationError) as exc:
        _validate_writer(raw, {"selected_project_ids": [1], "selected_experience_ids": [], "gaps": []}, bank, [])

    message = str(exc.value)
    assert "numbers absent from cited evidence: 999" in message
    assert "2 words (accepted range is 6-32)" in message
    assert "first paragraph starts with first person" in message


def test_narrow_repair_sends_only_rejected_source_and_merges_only_that_entry():
    bank = {"version": "3", "skills": {}, "sources": [
        {"source_key": "project:1", "type": "project", "name": "Relay", "facts": [
            {"id": "project:1:0", "statement": "Built a durable queue.", "evidence": "Built a durable queue.", "technologies": []},
        ]},
        {"source_key": "project:2", "type": "project", "name": "CareerOS", "facts": [
            {"id": "project:2:0", "statement": "Built an application generator.", "evidence": "Built an application generator.", "technologies": []},
        ]},
    ]}
    raw = {
        "selected_project_ids": [1, 2],
        "experience_entries": [],
        "project_entries": [
            {"project_id": 1, "bullets": [{"text": "bad", "fact_ids": []}]},
            {"project_id": 2, "bullets": [{"text": "Keep this valid bullet unchanged.", "fact_ids": ["project:2:0"]}]},
        ],
        "cover_letter_paragraphs": ["One", "Two", "Three"],
        "cover_letter_fact_ids": ["project:2:0"],
    }

    payload = _narrow_repair_payload(raw, ["project 1 has 0/2 accepted bullets"], bank, "job context")
    repaired = _merge_repair(raw, {
        "experience_entries": [],
        "project_entries": [{"project_id": 1, "bullets": [{"text": "Built a durable queue for background work.", "fact_ids": ["project:1:0"]}]}],
        "cover_letter_paragraphs": [],
        "cover_letter_fact_ids": [],
    })

    assert [source["id"] for source in payload["evidence"]] == ["project:1"]
    assert payload["rejected"]["cover_letter_paragraphs"] == []
    assert repaired["project_entries"][1] == raw["project_entries"][1]


def test_writer_recovery_uses_literal_source_facts_instead_of_failing_job():
    bank = {"skills": {}, "sources": [{
        "source_key": "project:1", "name": "Relay", "type": "project",
        "facts": [
            {"id": "project:1:0", "statement": "Processed 100 records through a Redis queue.", "evidence": "Processed 100 records through a Redis queue."},
            {"id": "project:1:1", "statement": "Built durable retries for failed background tasks.", "evidence": "Built durable retries for failed background tasks."},
        ],
    }]}
    rejected = {
        "experience_entries": [],
        "project_entries": [{"project_id": 1, "bullets": [
            {"text": "Processed 999 records with imaginary infrastructure", "fact_ids": ["project:1:0"]},
        ]}],
        "cover_letter_paragraphs": ["I am excited about this role."],
        "cover_letter_fact_ids": [],
        "fit_score": 75,
    }

    writer = _recover_writer([rejected], {"job_title": "Engineer", "company": "Acme", "selected_project_ids": [1], "selected_experience_ids": []}, bank, "")

    assert [bullet["text"] for bullet in writer["project_entries"][0]["bullets"]] == [
        "Processed 100 records through a Redis queue.",
        "Built durable retries for failed background tasks.",
    ]
    assert len(writer["cover_letter"].split("\n\n")) == 3
    assert writer["fit_score"] == 10


def test_invalid_optional_fourth_project_is_dropped_without_validation_error():
    bank = {"skills": {}, "sources": [{
        "source_key": "project:4",
        "name": "Relay",
        "brand_name": "Relay",
        "type": "project",
        "facts": [
            {"id": "project:4:0", "statement": "Built a durable background queue.", "evidence": "Built a durable background queue."},
            {"id": "project:4:1", "statement": "Retried failed background tasks.", "evidence": "Retried failed background tasks."},
        ],
    }]}
    raw = {
        "experience_entries": [],
        "project_entries": [{"project_id": 4, "bullets": [
            {"text": "Processed 999 unsupported tasks through Relay.", "fact_ids": ["project:4:0"]},
        ]}],
        "cover_letter_paragraphs": [
            "The backend engineering role centers on reliable asynchronous processing, clear ownership, and practical systems judgment. Those responsibilities align directly with the queueing and recovery work represented throughout my technical project background.",
            "In Relay, I built a durable background queue around explicit retry boundaries. I focused on preserving failed tasks, keeping processing behavior observable, and making the execution path understandable enough to debug under pressure. That work taught me to connect architecture choices to operational consequences instead of treating infrastructure as an isolated implementation detail, while maintaining a clear product purpose for every technical decision.",
            "My degree is complete, and I am available now to discuss how this evidence applies to the team's current engineering priorities, operating constraints, and product goals.",
        ],
        "cover_letter_fact_ids": ["project:4:0"],
        "fit_score": 7,
    }

    writer = _validate_writer(
        raw,
        {"selected_project_ids": [4], "selected_experience_ids": [], "gaps": []},
        bank,
        [],
        optional_project_ids={4},
    )

    assert writer["project_entries"] == []


def test_local_bullet_recovery_uses_free_literal_evidence_before_model_repair():
    bank = {"skills": {}, "sources": [{
        "source_key": "project:1",
        "name": "Relay",
        "type": "project",
        "facts": [
            {"id": "project:1:0", "statement": "Processed 100 records through Redis.", "evidence": "Processed 100 records through Redis."},
            {"id": "project:1:1", "statement": "Built durable retries.", "evidence": "Built durable retries."},
        ],
    }]}
    raw = {
        "experience_entries": [],
        "project_entries": [{"project_id": 1, "bullets": [
            {"text": "Processed 999 records through imaginary infrastructure.", "fact_ids": ["project:1:0"]},
        ]}],
    }

    repaired, changed_sources = _locally_repair_bullets(
        raw,
        {"selected_project_ids": [1], "selected_experience_ids": []},
        bank,
    )

    assert changed_sources == ["project:1"]
    assert [bullet["text"] for bullet in repaired["project_entries"][0]["bullets"]] == [
        "Processed 100 records through Redis.",
        "Built durable retries.",
    ]
    assert _validate_bullet(
        repaired["project_entries"][0]["bullets"][1],
        {"project:1:1": {
            "evidence": "Built durable retries.",
            "statement": "Built durable retries.",
        }},
        "project:1:",
    ) is not None


def test_local_recovery_does_not_resurrect_invalid_optional_project():
    bank = {"skills": {}, "sources": [{
        "source_key": "project:4",
        "name": "Relay",
        "type": "project",
        "facts": [
            {"id": "project:4:0", "statement": "Built a durable queue.", "evidence": "Built a durable queue."},
            {"id": "project:4:1", "statement": "Retried failed tasks.", "evidence": "Retried failed tasks."},
        ],
    }]}
    raw = {"experience_entries": [], "project_entries": [{
        "project_id": 4,
        "bullets": [{"text": "Invented 999 results.", "fact_ids": ["project:4:0"]}],
    }]}

    repaired, changed_sources = _locally_repair_bullets(
        raw,
        {"selected_project_ids": [4], "selected_experience_ids": []},
        bank,
        {4},
    )

    assert repaired["project_entries"] == []
    assert changed_sources == ["project:4"]


def test_writer_requires_two_experience_bullets_when_two_facts_exist():
    bank = {"skills": {}, "sources": [{
        "source_key": "experience:2", "name": "Developer", "type": "experience", "organization": "UBC",
        "facts": [
            {"id": "experience:2:0", "statement": "Built an allocation service for faculty teams.", "evidence": "Built an allocation service for faculty teams."},
            {"id": "experience:2:1", "statement": "Automated validation across multiple departments.", "evidence": "Automated validation across multiple departments."},
        ],
    }]}
    raw = {
        "experience_entries": [{"experience_id": 2, "bullets": [
            {"text": "Built an allocation service for faculty teams.", "fact_ids": ["experience:2:0"]},
        ]}],
        "project_entries": [],
        "cover_letter_paragraphs": [],
        "cover_letter_fact_ids": [],
        "fit_score": 8,
    }

    with pytest.raises(WriterValidationError, match=r"experience 2 has 1/2 accepted bullets"):
        _validate_writer(raw, {"selected_project_ids": [], "selected_experience_ids": [2], "gaps": []}, bank, [])


def test_cover_rejects_anonymous_passive_and_self_undermining_prose():
    facts = {"project:1:0": {
        "evidence": "Built 29 REST endpoints for Ledger.",
        "source_name": "Transactional Backend Infrastructure",
        "source_display_name": "Ledger | Transactional Backend Infrastructure",
        "source_brand_name": "Ledger",
        "source_type": "project",
    }}
    raw = {
        "cover_letter_paragraphs": [
            "The backend role matches my interests.",
            "For a transactional backend project, 29 REST endpoints were built with active Python proficiency development.",
            "My degree completes in June 2026, at which point availability begins.",
        ],
        "cover_letter_fact_ids": ["project:1:0"],
    }

    _, _, errors = _validated_cover(raw, facts, "Education completion is in the past (June 2026).")

    assert any("banned phrasing" in error for error in errors)
    assert "cover letter second paragraph does not name its cited project" in errors
    assert "cover letter second paragraph is not written in first person" in errors
    assert "cover letter describes a past graduation or availability date as future" in errors


def test_renderer_uses_canonical_project_name_not_model_supplied_heading():
    writer = {
        "experience_entries": [],
        "project_entries": [{"project_id": 1, "bullets": [{"text": "Built queue", "fact_ids": []}, {"text": "Reduced latency", "fact_ids": []}]}],
    }
    project = ns(id=1, name="Canonical Relay", start_date="Jan 2025", end_date=None, github_url="", description="Python Redis")
    body = _render_body(writer, [1], [], [project], [ns(category="Languages", items=["Python"], sort_order=0)], ["Python"])
    assert "Canonical Relay" in body


def test_project_brand_and_project_like_experience_role_are_restored_honestly():
    project = ns(name="Serverless Event Processing Platform", github_url="https://github.com/karansidhu3/Relay")
    experience = ns(role="Workforce Scheduling Platform")

    assert _project_display_name(project) == "Relay | Serverless Event Processing Platform"
    assert _experience_display_role(experience) == "Software Developer — Workforce Scheduling Platform"


def test_availability_context_does_not_put_past_graduation_in_the_future():
    context = _availability_context([ns(end_date="Jun 2026")], today=date(2026, 8, 10))

    assert "Education completion is in the past" in context
    assert "available for full-time work now" in context


def test_old_navy_and_sales_associate_are_excluded_in_code():
    items = [
        ns(company="Old Navy", role="Sales Associate", description="Helped customers"),
        ns(company="UBC", role="Developer", description="Built matching platform"),
    ]
    assert [item.company for item in _eligible_experiences(items)] == ["UBC"]


def test_insights_are_free_deterministic_and_require_repetition():
    jobs = [
        ns(generation_metadata={"gaps": [{"key": "kubernetes", "label": "Kubernetes", "action": "Deploy MarketMind on Kubernetes."}]}, strategic_note=None),
        ns(generation_metadata={"gaps": [{"key": "kubernetes", "label": "Kubernetes", "action": "Deploy MarketMind on Kubernetes."}]}, strategic_note=None),
        ns(generation_metadata={"gaps": [{"key": "go", "label": "Go", "action": "Build one Go service."}]}, strategic_note=None),
    ]
    result = synthesize_insight(jobs, 3)
    assert result["headline"] == "Kubernetes Repeats Across Roles"
    assert "2 of your 3" in result["observed"]


@pytest.mark.asyncio
async def test_fact_bank_cache_hit_makes_no_ai_call():
    experiences = [ns(id=1, role="Developer", company="UBC", description="Built a FastAPI service.")]
    payload = _source_payload(experiences, [], [])
    cached = ns(profile_hash=profile_hash(payload), schema_version=FACT_BANK_VERSION, fact_bank={"version": FACT_BANK_VERSION, "sources": [], "skills": {}})
    result = MagicMock()
    result.scalar_one_or_none.return_value = cached
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    llm = MagicMock()

    bank, cache_hit, cost = await get_or_build_fact_bank(db, user_id=uuid4(), llm=llm, experiences=experiences, projects=[], skills=[])

    assert bank == cached.fact_bank
    assert cache_hit is True
    assert cost == 0
    llm.call_structured.assert_not_called()


@pytest.mark.asyncio
async def test_fact_bank_build_is_local_bounded_and_cached():
    experiences = [ns(id=1, role="Developer", company="UBC", description="Built a FastAPI service processing 120 records. Added durable retries for failed jobs.")]
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    llm = MagicMock()
    llm.call_structured = AsyncMock(side_effect=AssertionError("fact-bank build must not call AI"))

    bank, cache_hit, cost = await get_or_build_fact_bank(db, user_id=uuid4(), llm=llm, experiences=experiences, projects=[], skills=[])

    assert cache_hit is False
    assert cost == 0
    assert "120 records" in bank["sources"][0]["facts"][0]["evidence"]
    assert len(bank["sources"][0]["facts"]) == 2
    llm.call_structured.assert_not_called()
    db.add.assert_called_once()
