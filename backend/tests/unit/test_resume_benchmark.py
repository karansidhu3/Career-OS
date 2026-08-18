import copy
import json
from pathlib import Path

from app.services.resume_benchmark import (
    QUALITY_DIMENSIONS,
    compare_reports,
    evaluate_case,
    evaluate_suite,
    generation_contract_hash,
    load_cases,
)


BENCHMARK_DIR = Path(__file__).parents[2] / "benchmarks"


def _fact(source_key: str, index: int, evidence: str, technologies: list[str]) -> tuple[str, dict]:
    fact_id = f"{source_key}:{index}"
    return fact_id, {
        "id": fact_id,
        "source_key": source_key,
        "source_type": source_key.split(":", 1)[0],
        "source_name": source_key,
        "evidence": evidence,
        "statement": evidence,
        "technologies": technologies,
    }


def _good_artifact() -> dict:
    evidence = [
        _fact("experience:1", 0, "Built a React and Next.js allocation interface that replaced 120 hours of manual work each term.", ["React", "Next.js"]),
        _fact("experience:1", 1, "Designed a PostgreSQL schema and server-side allocation engine with explicit validation constraints.", ["PostgreSQL"]),
        _fact("project:1", 0, "Built CareerOS as a Python FastAPI document service that replaced 30 minutes of manual tailoring.", ["Python", "FastAPI"]),
        _fact("project:1", 1, "Moved synchronous document generation to background workers after 30 second timeouts, reducing feedback to under 1 second.", ["Python"]),
        _fact("project:2", 0, "Built MarketMind as a Python data pipeline that ingests filings daily for investment research.", ["Python", "FastAPI", "PostgreSQL"]),
        _fact("project:2", 1, "Designed a temporal signal pipeline with PostgreSQL state and Redis caching to preserve thesis changes.", ["PostgreSQL", "Redis"]),
        _fact("project:3", 0, "Built a Python multi-agent research service that reduced manual stock research time by 70%.", ["Python", "FastAPI"]),
        _fact("project:3", 1, "Orchestrated parallel market, news, and sentiment agents through a FastAPI coordination layer.", ["Python", "FastAPI"]),
    ]
    facts = dict(evidence)
    entries = [
        {"source_key": "experience:1", "source_type": "experience", "bullets": [
            {"text": facts["experience:1:0"]["evidence"], "fact_ids": ["experience:1:0"]},
            {"text": facts["experience:1:1"]["evidence"], "fact_ids": ["experience:1:1"]},
        ]},
        {"source_key": "project:1", "source_type": "project", "bullets": [
            {"text": facts["project:1:0"]["evidence"], "fact_ids": ["project:1:0"]},
            {"text": facts["project:1:1"]["evidence"], "fact_ids": ["project:1:1"]},
        ]},
        {"source_key": "project:2", "source_type": "project", "bullets": [
            {"text": facts["project:2:0"]["evidence"], "fact_ids": ["project:2:0"]},
            {"text": facts["project:2:1"]["evidence"], "fact_ids": ["project:2:1"]},
        ]},
        {"source_key": "project:3", "source_type": "project", "bullets": [
            {"text": facts["project:3:0"]["evidence"], "fact_ids": ["project:3:0"]},
            {"text": facts["project:3:1"]["evidence"], "fact_ids": ["project:3:1"]},
        ]},
    ]
    cover = (
        "Reliable backend document systems require clear request boundaries, observable failures, and practical ownership of the entire delivery path. "
        "This role's emphasis on Python services and production reliability maps directly to the work represented in my recent engineering projects.\n\n"
        "In CareerOS, synchronous generation failed at 30 seconds and left the request path unable to provide useful feedback. "
        "I moved document compilation into background workers behind the FastAPI service, which reduced time-to-first-feedback to under 1 second. "
        "That decision separated user-facing responsiveness from long-running document work while preserving a traceable failure path and a clear operational boundary.\n\n"
        "My degree is complete, and I am available now to discuss how this evidence applies to the team's backend engineering priorities and reliability goals."
    )
    return {
        "resume_entries": entries,
        "facts": facts,
        "selected_skills": ["Python", "FastAPI", "PostgreSQL", "React", "Next.js", "Redis"],
        "selected_projects": ["CareerOS", "MarketMind", "Agentic Market Sentiment"],
        "cover_letter": cover,
        "cover_letter_fact_ids": ["project:1:0", "project:1:1"],
        "page_count": 1,
        "total_cost_usd": 0.04,
        "repair_used": False,
    }


def _case() -> dict:
    return {
        "id": "python_backend",
        "company": "Example",
        "role": "Backend Engineer",
        "job_description": "Build reliable Python FastAPI services with PostgreSQL, Redis, testing, and deployment automation.",
        "requirements": [
            {"name": "Python", "aliases": ["Python"], "weight": 3},
            {"name": "FastAPI", "aliases": ["FastAPI"], "weight": 2},
            {"name": "PostgreSQL", "aliases": ["PostgreSQL"], "weight": 2},
            {"name": "Redis", "aliases": ["Redis"], "weight": 1},
        ],
    }


def test_good_artifact_scores_grounding_focus_density_and_grammar_at_full_marks():
    report = evaluate_case(_case(), _good_artifact())

    assert report["dimensions"]["factual_grounding"] == 10
    assert report["dimensions"]["job_relevance"] == 10
    assert report["dimensions"]["cover_letter_focus"] == 10
    assert report["dimensions"]["one_page_density"] == 10
    assert report["dimensions"]["grammar"] == 10
    assert report["total_cost_usd"] == 0.04
    assert report["repair_used"] is False


def test_unsupported_metric_reduces_grounding_and_metric_scores():
    artifact = _good_artifact()
    artifact["resume_entries"][1]["bullets"][0]["text"] = "Built CareerOS for 50,000 users with Python and FastAPI."

    report = evaluate_case(_case(), artifact)

    assert report["dimensions"]["factual_grounding"] < 10
    assert report["dimensions"]["metric_quality"] < 10
    assert any("Ungrounded resume bullet" in issue for issue in report["issues"])


def test_suite_reports_missing_cases_and_median_cost():
    cases = [_case(), {**_case(), "id": "missing"}]
    report = evaluate_suite(cases, {"python_backend": _good_artifact()})

    assert report["missing_cases"] == ["missing"]
    assert report["summary"]["case_count"] == 1
    assert report["summary"]["median_cost_usd"] == 0.04


def test_acceptance_gate_rejects_any_quality_dimension_regression():
    baseline = evaluate_suite([_case()], {"python_backend": _good_artifact()})
    candidate = copy.deepcopy(baseline)
    candidate["cases"]["python_backend"]["dimensions"]["grammar"] -= 1

    comparison = compare_reports(baseline, candidate)

    assert comparison["passed"] is False
    assert any("regressed on grammar" in failure for failure in comparison["failures"])


def test_acceptance_gate_rejects_cost_or_repair_growth_without_real_quality_gain():
    baseline = evaluate_suite([_case()], {"python_backend": _good_artifact()})
    candidate = copy.deepcopy(baseline)
    candidate["summary"]["median_cost_usd"] += 0.01
    candidate["summary"]["repair_rate"] = 1.0

    comparison = compare_reports(baseline, candidate)

    assert comparison["passed"] is False
    assert any("Median cost increased" in failure for failure in comparison["failures"])
    assert any("Repair rate increased" in failure for failure in comparison["failures"])


def test_benchmark_manifest_preserves_all_six_agreed_roles_and_baseline_dimensions():
    cases = load_cases(BENCHMARK_DIR / "cases.json")
    baseline = json.loads((BENCHMARK_DIR / "baseline.json").read_text())
    expected = {
        "canonical_python_linux_backend",
        "solace_java_event_fullstack",
        "microsoft_general_software_engineering",
        "fgf_ai_engineering",
        "draftkings_frontend",
        "rbc_quantitative_data",
    }

    assert {case["id"] for case in cases} == expected
    assert set(baseline["cases"]) == expected
    assert baseline["generation_version"] == "3.6"
    assert baseline["generation_contract_hash"] == generation_contract_hash()
    assert all(set(item["dimensions"]) == set(QUALITY_DIMENSIONS) for item in baseline["cases"].values())
    assert all(case["job_description"].strip() for case in cases)
