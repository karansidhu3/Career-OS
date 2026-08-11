from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.candidacy_insights import synthesize_insight
from app.services.generation_v2 import (
    _WRITER_SCHEMA,
    WriterValidationError,
    _eligible_experiences,
    _recover_writer,
    _render_body,
    _validate_bullet,
    _validate_plan,
    _validate_writer,
)
from app.services.llm_client import AnthropicAdapter, StructuredOutputTruncatedError, ToolCallResult
from app.services.llm_cost import calculate_llm_cost
from app.services.profile_fact_bank import FACT_BANK_VERSION, _source_payload, _validate_bank, get_or_build_fact_bank, profile_hash


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def test_cost_ledger_prices_each_token_class_without_double_counting():
    usage = ToolCallResult(tool_input={}, input_tokens=1_000, output_tokens=1_000, cache_read_tokens=1_000, cache_write_tokens=1_000)
    assert calculate_llm_cost("claude-sonnet-4-6", usage) == pytest.approx(0.02205)
    assert calculate_llm_cost("claude-haiku-4-5", usage) == pytest.approx(0.00735)


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

    with pytest.raises(StructuredOutputTruncatedError, match="100-token"):
        await AnthropicAdapter("test-key").call_structured(
            model="claude-sonnet-4-6",
            max_tokens=100,
            system="Return JSON.",
            messages=[{"role": "user", "content": "test"}],
            schema={"type": "object"},
            timeout=1.0,
        )


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


def test_renderer_uses_canonical_project_name_not_model_supplied_heading():
    writer = {
        "experience_entries": [],
        "project_entries": [{"project_id": 1, "bullets": [{"text": "Built queue", "fact_ids": []}, {"text": "Reduced latency", "fact_ids": []}]}],
    }
    project = ns(id=1, name="Canonical Relay", start_date="Jan 2025", end_date=None, github_url="", description="Python Redis")
    body = _render_body(writer, [1], [], [project], [ns(category="Languages", items=["Python"], sort_order=0)], ["Python"])
    assert "Canonical Relay" in body


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
