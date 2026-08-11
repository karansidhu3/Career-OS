"""Versioned, deterministic evidence indexing for generation v2.

The source descriptions are already the authority. Splitting them locally is safer,
cheaper, and more reliable than paying a model to copy the same text into JSON.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation_audit import ProfileFactBank
from app.models.profile import Experience, Project, SkillCategory
from app.services.llm_client import LLMClient


FACT_BANK_VERSION = "3"
MAX_FACTS_PER_SOURCE = 12
MAX_FACT_CHARS = 360

_HIGH_SIGNAL_TERMS = re.compile(
    r"\b(?:architect|built|designed|developed|implemented|integrated|migrated|optimized|"
    r"reduced|improved|increased|automated|deployed|tested|validated|scaled|processed|"
    r"api|database|queue|worker|pipeline|authentication|authorization|ci/cd|latency|"
    r"throughput|reliability|transaction|schema|architecture)\b",
    re.IGNORECASE,
)


def project_brand_from_url(url: str | None) -> str:
    """Return the repository name when a project has a GitHub URL."""
    match = re.search(r"github\.com/[^/]+/([^/?#]+)", url or "", re.IGNORECASE)
    return (match.group(1).removesuffix(".git") if match else "").strip()


def _source_payload(experiences: list[Experience], projects: list[Project], skills: list[SkillCategory]) -> dict[str, Any]:
    sources = []
    for item in experiences:
        sources.append({
            "source_key": f"experience:{item.id}",
            "type": "experience",
            "name": item.role,
            "organization": item.company,
            "description": item.description or "",
        })
    for item in projects:
        brand_name = project_brand_from_url(getattr(item, "github_url", None))
        sources.append({
            "source_key": f"project:{item.id}",
            "type": "project",
            "name": item.name,
            "brand_name": brand_name,
            "display_name": (
                item.name
                if not brand_name or brand_name.casefold() in item.name.casefold()
                else f"{brand_name} | {item.name}"
            ),
            "description": item.description or "",
        })
    return {
        "sources": sources,
        "skills": {item.category: list(item.items or []) for item in skills},
    }


def profile_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _evidence_fragments(description: str) -> list[str]:
    """Split source prose and keep its most probative verbatim facts.

    Long profile entries often put metrics, tests, and architecture decisions after
    introductory prose. Ranking the complete entry prevents those facts from being
    discarded merely because they appeared after the first eight sentences.
    """
    pieces = re.split(r"(?:\r?\n)+|(?<=[.!?;])\s+(?=[A-Z0-9])", description)
    fragments: list[str] = []
    for piece in pieces:
        piece = re.sub(r"^\s*[-*•]+\s*", "", piece).strip()
        while len(piece) > MAX_FACT_CHARS:
            boundary = piece.rfind(" ", 0, MAX_FACT_CHARS + 1)
            if boundary < MAX_FACT_CHARS // 2:
                boundary = MAX_FACT_CHARS
            fragments.append(piece[:boundary].strip())
            piece = piece[boundary:].strip()
        if piece:
            fragments.append(piece)
    if len(fragments) <= MAX_FACTS_PER_SOURCE:
        return fragments

    def signal(item: tuple[int, str]) -> tuple[int, int]:
        index, fragment = item
        score = 0
        if index == 0:
            score += 3
        if _numbers_in(fragment):
            score += 7
        score += min(6, len(_HIGH_SIGNAL_TERMS.findall(fragment)))
        if re.search(r"\b(?:because|instead of|replaced|resulting|so that|while|without)\b", fragment, re.IGNORECASE):
            score += 3
        if re.search(r"\b[A-Z][A-Za-z0-9.+#/-]{1,}\b", fragment):
            score += 1
        return score, -index

    ranked = sorted(enumerate(fragments), key=signal, reverse=True)[:MAX_FACTS_PER_SOURCE]
    return [fragment for _, fragment in sorted(ranked)]


def _numbers_in(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z])\d+(?:[.,]\d+)?%?\+?", text))


def _deterministic_raw_bank(payload: dict[str, Any]) -> dict[str, Any]:
    known_skills = [str(skill) for values in payload["skills"].values() for skill in values]
    sources = []
    for source in payload["sources"]:
        facts = []
        for fragment in _evidence_fragments(source["description"]):
            technologies = [
                skill for skill in known_skills
                if re.search(rf"(?<![A-Za-z0-9]){re.escape(skill)}(?![A-Za-z0-9])", fragment, re.IGNORECASE)
            ]
            facts.append({
                "statement": fragment,
                "evidence": fragment,
                "tags": [],
                "technologies": technologies[:12],
            })
        sources.append({"source_key": source["source_key"], "summary": source["name"], "facts": facts})
    return {"sources": sources}


def _validate_bank(raw: dict, payload: dict[str, Any]) -> dict[str, Any]:
    source_map = {item["source_key"]: item for item in payload["sources"]}
    result: list[dict[str, Any]] = []
    for source in raw.get("sources", []):
        key = source.get("source_key")
        canonical = source_map.get(key)
        if not canonical:
            continue
        description = canonical["description"]
        facts = []
        for index, fact in enumerate(source.get("facts") or []):
            evidence = str(fact.get("evidence") or "").strip()
            statement = str(fact.get("statement") or "").strip()
            if not statement or len(evidence) < 4 or _normal(evidence) not in _normal(description):
                continue
            facts.append({
                "id": f"{key}:{index}",
                # Evidence is the authority. Keeping the display statement equal
                # to the verified quote prevents a plausible-sounding compiler
                # paraphrase from becoming a new fact downstream.
                "statement": evidence[:500],
                "evidence": evidence[:500],
                "tags": [str(x)[:50] for x in (fact.get("tags") or [])[:8]],
                "technologies": [
                    str(x)[:50]
                    for x in (fact.get("technologies") or [])[:12]
                    if re.search(rf"(?<![A-Za-z0-9]){re.escape(str(x))}(?![A-Za-z0-9])", description, re.IGNORECASE)
                ],
            })
        # A model-formatting failure must not make real profile material disappear.
        if not facts and description.strip():
            facts = [{
                "id": f"{key}:0",
                "statement": re.sub(r"\s+", " ", description).strip()[:700],
                "evidence": re.sub(r"\s+", " ", description).strip()[:700],
                "tags": [],
                "technologies": [],
            }]
        result.append({
            **{k: v for k, v in canonical.items() if k != "description"},
            "summary": canonical["name"],
            "facts": facts,
        })

    # Include any source the compiler omitted.
    present = {item["source_key"] for item in result}
    for key, canonical in source_map.items():
        if key not in present:
            description = re.sub(r"\s+", " ", canonical["description"]).strip()
            result.append({
                **{k: v for k, v in canonical.items() if k != "description"},
                "summary": canonical["name"],
                "facts": ([{"id": f"{key}:0", "statement": description[:700], "evidence": description[:700], "tags": [], "technologies": []}] if description else []),
            })
    return {"version": FACT_BANK_VERSION, "sources": result, "skills": payload["skills"]}


async def get_or_build_fact_bank(
    db: AsyncSession,
    *,
    user_id: UUID,
    llm: LLMClient,
    experiences: list[Experience],
    projects: list[Project],
    skills: list[SkillCategory],
) -> tuple[dict[str, Any], bool, float]:
    """Return (fact bank, cache_hit, build_cost)."""
    payload = _source_payload(experiences, projects, skills)
    digest = profile_hash(payload)
    cached = (await db.execute(select(ProfileFactBank).where(ProfileFactBank.user_id == user_id))).scalar_one_or_none()
    if cached and cached.profile_hash == digest and cached.schema_version == FACT_BANK_VERSION:
        return cached.fact_bank, True, 0.0

    # `llm` remains in the public signature for compatibility with callers, but
    # building the evidence index is intentionally local and incurs no AI call.
    del llm
    bank = _validate_bank(_deterministic_raw_bank(payload), payload)
    if cached:
        cached.profile_hash = digest
        cached.schema_version = FACT_BANK_VERSION
        cached.fact_bank = bank
    else:
        db.add(ProfileFactBank(user_id=user_id, profile_hash=digest, schema_version=FACT_BANK_VERSION, fact_bank=bank))
    return bank, False, 0.0
