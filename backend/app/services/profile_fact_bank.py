"""Versioned, evidence-backed profile compression for generation v2."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation_audit import ProfileFactBank
from app.models.profile import Experience, Project, SkillCategory
from app.services.llm_client import LLMClient
from app.services.llm_cost import record_llm_call


FACT_BANK_VERSION = "1"
FACT_BANK_MODEL = "claude-haiku-4-5"

_FACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "source_key": {"type": "string"},
                    "summary": {"type": "string"},
                    "facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "statement": {"type": "string"},
                                "evidence": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "technologies": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["statement", "evidence", "tags", "technologies"],
                        },
                    },
                },
                "required": ["source_key", "summary", "facts"],
            },
        }
    },
    "required": ["sources"],
}

_SYSTEM = """Convert profile descriptions into a compact evidence index.
Every fact must be directly supported by one exact, contiguous quote copied into `evidence`.
Keep all numbers, named systems, technologies, architecture decisions, and measured outcomes.
Do not infer, improve, rename, or add anything. Use each supplied source_key unchanged.
Statements must be concise factual clauses, not resume bullets."""

logger = logging.getLogger(__name__)


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
        sources.append({
            "source_key": f"project:{item.id}",
            "type": "project",
            "name": item.name,
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

    try:
        call = await llm.call_structured(
            model=FACT_BANK_MODEL,
            max_tokens=3500,
            system=_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            schema=_FACT_SCHEMA,
            timeout=60.0,
        )
    except Exception:
        # Source descriptions themselves are safe evidence. Falling back to one
        # bounded fact per source preserves reliability without inventing facts;
        # the fallback is not cached, so the next generation retries compilation.
        logger.exception("Profile fact-bank compilation failed; using bounded source fallback")
        return _validate_bank({"sources": []}, payload), False, 0.0
    bank = _validate_bank(call.tool_input, payload)
    audit = record_llm_call(db, user_id=user_id, job_id=None, purpose="profile_fact_bank", model=FACT_BANK_MODEL, usage=call)
    if cached:
        cached.profile_hash = digest
        cached.schema_version = FACT_BANK_VERSION
        cached.fact_bank = bank
    else:
        db.add(ProfileFactBank(user_id=user_id, profile_hash=digest, schema_version=FACT_BANK_VERSION, fact_bank=bank))
    return bank, False, audit.cost_usd
