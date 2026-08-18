"""Deterministic quality and cost evaluation for generated applications.

The benchmark never calls an LLM. Generation artifacts contain the exact facts
and citations needed to score grounding, writing quality, layout, cost, and
repair use offline. Human review remains valuable, but prompt changes now have a
repeatable regression gate instead of relying on memory or one favorite resume.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

from app.services.generation_v2 import (
    GENERATION_VERSION,
    _REPAIR_SYSTEM,
    _WRITER_SCHEMA,
    _WRITE_SYSTEM,
    _cover_story_errors,
    _has_incomplete_ending,
    _mentions_term,
    _metric_tier,
    _numbers,
)


SCHEMA_VERSION = 1
QUALITY_DIMENSIONS = (
    "factual_grounding",
    "job_relevance",
    "recruiter_clarity",
    "technical_depth",
    "ownership_accuracy",
    "metric_quality",
    "cover_letter_focus",
    "one_page_density",
    "grammar",
)
MEANINGFUL_QUALITY_GAIN = 0.25
QUALITY_TOLERANCE = 0.05
COST_TOLERANCE_USD = 0.001

_VAGUE_OPENERS = re.compile(
    r"^(?:worked on|helped|assisted|participated in|was responsible for|contributed to|supported)\b",
    re.IGNORECASE,
)
_OWNERSHIP_CLAIMS = re.compile(r"\b(?:directed|led|managed|owned|spearheaded)\b", re.IGNORECASE)
_TECHNICAL_SIGNALS = re.compile(
    r"\b(?:api|architecture|async|cache|database|deployment|event|index|latency|migration|"
    r"pipeline|queue|retry|schema|service|state machine|transaction|worker)\b",
    re.IGNORECASE,
)
_DECISION_SIGNALS = re.compile(
    r"\b(?:after|because|chose|constraint|failed|instead|migrated|moved|replaced|timeout|tradeoff)\b",
    re.IGNORECASE,
)
_RESULT_SIGNALS = re.compile(
    r"\b(?:automated|cut|eliminated|enabled|improved|increased|prevented|reduced|saved)\b",
    re.IGNORECASE,
)


def generation_contract_hash() -> str:
    payload = json.dumps({
        "generation_version": GENERATION_VERSION,
        "writer_system": _WRITE_SYSTEM,
        "repair_system": _REPAIR_SYSTEM,
        "writer_schema": _WRITER_SCHEMA,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _clamp(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 2)


def _ratio_score(passed: int, total: int, *, empty: float = 0.0) -> float:
    return _clamp(10 * passed / total) if total else empty


def _bullets(artifact: dict) -> list[tuple[dict, int, dict]]:
    return [
        (entry, index, bullet)
        for entry in artifact.get("resume_entries", [])
        for index, bullet in enumerate(entry.get("bullets", []))
    ]


def _cited_evidence(bullet: dict, facts: dict[str, dict]) -> tuple[list[str], str]:
    cited = [fact_id for fact_id in bullet.get("fact_ids", []) if fact_id in facts]
    evidence = " ".join(
        f"{facts[fact_id].get('evidence', '')} {facts[fact_id].get('statement', '')}"
        for fact_id in cited
    )
    return cited, evidence


def _known_technologies(artifact: dict, facts: dict[str, dict]) -> list[str]:
    return sorted({
        str(technology)
        for fact in facts.values()
        for technology in fact.get("technologies", [])
        if str(technology).strip()
    } | {
        str(skill)
        for skill in artifact.get("known_skills", [])
        if str(skill).strip()
    }, key=len, reverse=True)


def _grounding_score(artifact: dict, issues: list[str]) -> float:
    facts = artifact.get("facts", {})
    technologies = _known_technologies(artifact, facts)
    valid = 0
    bullets = _bullets(artifact)
    for entry, _, bullet in bullets:
        text = str(bullet.get("text") or "")
        cited, evidence = _cited_evidence(bullet, facts)
        source_key = str(entry.get("source_key") or "")
        grounded = bool(cited) and all(
            str(facts[fact_id].get("source_key") or fact_id.rsplit(":", 1)[0]) == source_key
            for fact_id in cited
        )
        grounded = grounded and _numbers(text).issubset(_numbers(evidence))
        grounded = grounded and all(
            not _mentions_term(text, technology) or _mentions_term(evidence, technology)
            for technology in technologies
        )
        if grounded:
            valid += 1
        else:
            issues.append(f"Ungrounded resume bullet in {source_key or 'unknown source'}: {text[:90]}")
    cover_ids = [fact_id for fact_id in artifact.get("cover_letter_fact_ids", []) if fact_id in facts]
    cover_evidence = " ".join(str(facts[fact_id].get("evidence") or "") for fact_id in cover_ids)
    cover_grounded = bool(cover_ids) and _numbers(str(artifact.get("cover_letter") or "")).issubset(
        _numbers(cover_evidence + " " + str(artifact.get("job_description") or ""))
    )
    total = len(bullets) + 1
    return _ratio_score(valid + int(cover_grounded), total)


def _relevance_score(case: dict, artifact: dict, issues: list[str]) -> float:
    text = " ".join(
        [str(bullet.get("text") or "") for _, _, bullet in _bullets(artifact)]
        + [str(value) for value in artifact.get("selected_skills", [])]
        + [str(value) for value in artifact.get("selected_projects", [])]
    )
    earned = 0.0
    total = 0.0
    missing = []
    for requirement in case.get("requirements", []):
        weight = float(requirement.get("weight", 1))
        aliases = [str(value) for value in requirement.get("aliases", [])]
        total += weight
        if any(_mentions_term(text, alias) for alias in aliases):
            earned += weight
        else:
            missing.append(str(requirement.get("name") or (aliases[0] if aliases else "requirement")))
    if missing:
        issues.append(f"Missing benchmark evidence for: {', '.join(missing)}")
    return _clamp(10 * earned / total) if total else 0.0


def _clarity_score(artifact: dict, issues: list[str]) -> float:
    passed = 0
    bullets = _bullets(artifact)
    seen: set[str] = set()
    for _, _, bullet in bullets:
        text = str(bullet.get("text") or "").strip()
        words = len(text.split())
        clear = 12 <= words <= 32 and not _VAGUE_OPENERS.search(text) and text.casefold() not in seen
        seen.add(text.casefold())
        if clear:
            passed += 1
        else:
            issues.append(f"Low-clarity bullet ({words} words): {text[:90]}")
    return _ratio_score(passed, len(bullets))


def _technical_depth_score(artifact: dict, issues: list[str]) -> float:
    engineering_bullets = [bullet for _, index, bullet in _bullets(artifact) if index == 1]
    points = 0
    for bullet in engineering_bullets:
        text = str(bullet.get("text") or "")
        signals = sum(bool(pattern.search(text)) for pattern in (_TECHNICAL_SIGNALS, _DECISION_SIGNALS, _RESULT_SIGNALS))
        points += signals
        if signals < 2:
            issues.append(f"Engineering proof lacks decision depth: {text[:90]}")
    return _clamp(10 * points / (3 * len(engineering_bullets))) if engineering_bullets else 0.0


def _ownership_score(artifact: dict, issues: list[str]) -> float:
    facts = artifact.get("facts", {})
    valid = 0
    bullets = _bullets(artifact)
    for entry, _, bullet in bullets:
        text = str(bullet.get("text") or "")
        cited, evidence = _cited_evidence(bullet, facts)
        inflated = bool(_OWNERSHIP_CLAIMS.search(text)) and not _OWNERSHIP_CLAIMS.search(evidence)
        weak = bool(_VAGUE_OPENERS.search(text))
        if cited and not inflated and not weak:
            valid += 1
        else:
            issues.append(f"Ownership language is weak or unsupported in {entry.get('source_key')}: {text[:90]}")
    return _ratio_score(valid, len(bullets))


def _metric_score(artifact: dict, issues: list[str]) -> float:
    facts = artifact.get("facts", {})
    metric_bullets = []
    supported = 0
    tier_points = 0
    for _, _, bullet in _bullets(artifact):
        text = str(bullet.get("text") or "")
        if not _numbers(text):
            continue
        metric_bullets.append(bullet)
        _, evidence = _cited_evidence(bullet, facts)
        if _numbers(text).issubset(_numbers(evidence)):
            supported += 1
        tier = _metric_tier(text)
        tier_points += {1: 3, 2: 2, 3: 0}.get(tier, 1)
    if not metric_bullets:
        issues.append("Resume contains no concrete metric.")
        return 2.0
    if supported != len(metric_bullets):
        issues.append("At least one resume metric is absent from its cited evidence.")
    support_score = 5 * supported / len(metric_bullets)
    quality_score = 5 * tier_points / (3 * len(metric_bullets))
    return _clamp(support_score + quality_score)


def _cover_score(artifact: dict, issues: list[str]) -> float:
    cover = str(artifact.get("cover_letter") or "")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cover) if part.strip()]
    checks = [len(paragraphs) == 3]
    if len(paragraphs) == 3:
        second = paragraphs[1]
        checks.extend([
            not _cover_story_errors(second),
            len(re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)?%?\+?", second)) <= 2,
            len({name for name in artifact.get("selected_projects", []) if _mentions_term(second, str(name).split(" | ")[0])}) == 1,
            110 <= len(cover.split()) <= 300,
        ])
    else:
        checks.extend([False, False, False, False])
    if not all(checks):
        issues.append("Cover letter fails paragraph, focus, story, metric, or length constraints.")
    return _ratio_score(sum(checks), len(checks))


def _density_score(artifact: dict, issues: list[str]) -> float:
    entries = artifact.get("resume_entries", [])
    projects = [entry for entry in entries if entry.get("source_type") == "project"]
    experiences = [entry for entry in entries if entry.get("source_type") == "experience"]
    checks = [
        artifact.get("page_count") == 1,
        3 <= len(projects) <= 4,
        all(len(entry.get("bullets", [])) == 2 for entry in projects),
        1 <= len(experiences) <= 2,
        all(1 <= len(entry.get("bullets", [])) <= 2 for entry in experiences),
    ]
    if not all(checks):
        issues.append("Resume misses the one-page density or section-count target.")
    return _ratio_score(sum(checks), len(checks))


def _grammar_score(artifact: dict, issues: list[str]) -> float:
    bullet_texts = [str(bullet.get("text") or "") for _, _, bullet in _bullets(artifact)]
    cover_texts = [part.strip() for part in re.split(r"\n\s*\n", str(artifact.get("cover_letter") or "")) if part.strip()]
    texts = bullet_texts + cover_texts
    defects = 0
    for index, text in enumerate(texts):
        broken = (
            "—" in text
            or bool(re.search(r"[,;:](?=[A-Za-z])|\.(?=[A-Z])", text))
            or _has_incomplete_ending(text)
            or (index >= len(bullet_texts) and not bool(re.search(r"[.!?]$", text)))
        )
        if broken:
            defects += 1
            issues.append(f"Grammar or punctuation defect: {text[:90]}")
    return _ratio_score(len(texts) - defects, len(texts), empty=0.0)


def evaluate_case(case: dict, artifact: dict) -> dict[str, Any]:
    """Score one saved generation artifact on the agreed Phase 6 rubric."""
    artifact = {**artifact, "job_description": case.get("job_description", "")}
    issues: list[str] = []
    dimensions = {
        "factual_grounding": _grounding_score(artifact, issues),
        "job_relevance": _relevance_score(case, artifact, issues),
        "recruiter_clarity": _clarity_score(artifact, issues),
        "technical_depth": _technical_depth_score(artifact, issues),
        "ownership_accuracy": _ownership_score(artifact, issues),
        "metric_quality": _metric_score(artifact, issues),
        "cover_letter_focus": _cover_score(artifact, issues),
        "one_page_density": _density_score(artifact, issues),
        "grammar": _grammar_score(artifact, issues),
    }
    return {
        "case_id": case["id"],
        "company": case["company"],
        "role": case["role"],
        "dimensions": dimensions,
        "quality_score": round(statistics.fmean(dimensions.values()), 2),
        "total_cost_usd": round(float(artifact.get("total_cost_usd") or 0), 6),
        "repair_used": bool(artifact.get("repair_used")),
        "issues": issues,
    }


def evaluate_suite(cases: list[dict], artifacts: dict[str, dict]) -> dict[str, Any]:
    reports = {
        case["id"]: evaluate_case(case, artifacts[case["id"]])
        for case in cases
        if case["id"] in artifacts
    }
    missing = [case["id"] for case in cases if case["id"] not in artifacts]
    qualities = [report["quality_score"] for report in reports.values()]
    costs = [report["total_cost_usd"] for report in reports.values()]
    repairs = [report["repair_used"] for report in reports.values()]
    return {
        "schema_version": SCHEMA_VERSION,
        "cases": reports,
        "missing_cases": missing,
        "summary": {
            "case_count": len(reports),
            "median_quality": round(statistics.median(qualities), 2) if qualities else 0.0,
            "median_cost_usd": round(statistics.median(costs), 6) if costs else 0.0,
            "repair_rate": round(sum(repairs) / len(repairs), 4) if repairs else 0.0,
        },
    }


def compare_reports(baseline: dict, candidate: dict) -> dict[str, Any]:
    """Apply the no-quality-regression / cost-for-real-gain policy."""
    failures = []
    if candidate.get("missing_cases"):
        failures.append(f"Missing benchmark cases: {', '.join(candidate['missing_cases'])}")
    for case_id, baseline_case in baseline.get("cases", {}).items():
        candidate_case = candidate.get("cases", {}).get(case_id)
        if not candidate_case:
            failures.append(f"Missing candidate result for {case_id}")
            continue
        for dimension in QUALITY_DIMENSIONS:
            before = float(baseline_case["dimensions"][dimension])
            after = float(candidate_case["dimensions"][dimension])
            if after + QUALITY_TOLERANCE < before:
                failures.append(f"{case_id} regressed on {dimension}: {before:.2f} -> {after:.2f}")
        if candidate_case["quality_score"] + QUALITY_TOLERANCE < baseline_case["quality_score"]:
            failures.append(
                f"{case_id} overall quality regressed: {baseline_case['quality_score']:.2f} -> "
                f"{candidate_case['quality_score']:.2f}"
            )
    base_summary = baseline.get("summary", {})
    candidate_summary = candidate.get("summary", {})
    quality_gain = float(candidate_summary.get("median_quality", 0)) - float(base_summary.get("median_quality", 0))
    cost_increase = float(candidate_summary.get("median_cost_usd", 0)) - float(base_summary.get("median_cost_usd", 0))
    if cost_increase > COST_TOLERANCE_USD and quality_gain < MEANINGFUL_QUALITY_GAIN:
        failures.append(
            f"Median cost increased by ${cost_increase:.4f} without a meaningful quality gain "
            f"({quality_gain:+.2f}; required +{MEANINGFUL_QUALITY_GAIN:.2f})."
        )
    repair_increase = float(candidate_summary.get("repair_rate", 0)) - float(base_summary.get("repair_rate", 0))
    if repair_increase > 0 and quality_gain < MEANINGFUL_QUALITY_GAIN:
        failures.append(
            f"Repair rate increased by {repair_increase:.1%} without a meaningful quality gain."
        )
    return {"passed": not failures, "failures": failures}


def load_cases(path: Path) -> list[dict]:
    manifest = json.loads(path.read_text())
    cases = manifest["cases"]
    for case in cases:
        description_path = path.parent / case.pop("job_description_file")
        case["job_description"] = description_path.read_text()
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Score CareerOS resume benchmark artifacts.")
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate_suite(load_cases(args.cases), json.loads(args.artifacts.read_text()))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    else:
        print(json.dumps(report, indent=2))
    if not args.baseline:
        return 0
    comparison = compare_reports(json.loads(args.baseline.read_text()), report)
    if not comparison["passed"]:
        for failure in comparison["failures"]:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: benchmark quality and cost policy satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
