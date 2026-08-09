from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.candidacy_insights import synthesize_insight
from app.services.generation_v2 import _eligible_experiences, _render_body, _validate_bullet, _validate_plan
from app.services.llm_client import ToolCallResult
from app.services.llm_cost import calculate_llm_cost
from app.services.profile_fact_bank import _source_payload, _validate_bank, get_or_build_fact_bank, profile_hash


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def test_cost_ledger_prices_each_token_class_without_double_counting():
    usage = ToolCallResult(tool_input={}, input_tokens=1_000, output_tokens=1_000, cache_read_tokens=1_000, cache_write_tokens=1_000)
    assert calculate_llm_cost("claude-sonnet-4-6", usage) == pytest.approx(0.02205)
    assert calculate_llm_cost("claude-haiku-4-5", usage) == pytest.approx(0.00735)


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
    cached = ns(profile_hash=profile_hash(payload), schema_version="1", fact_bank={"version": "1", "sources": [], "skills": {}})
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
async def test_fact_bank_ai_failure_falls_back_to_source_evidence():
    experiences = [ns(id=1, role="Developer", company="UBC", description="Built a FastAPI service processing 120 records.")]
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    llm = MagicMock()
    llm.call_structured = AsyncMock(side_effect=RuntimeError("provider unavailable"))

    bank, cache_hit, cost = await get_or_build_fact_bank(db, user_id=uuid4(), llm=llm, experiences=experiences, projects=[], skills=[])

    assert cache_hit is False
    assert cost == 0
    assert "120 records" in bank["sources"][0]["facts"][0]["evidence"]
    db.add.assert_not_called()
