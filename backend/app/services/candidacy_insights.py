"""Free, deterministic candidacy patterns from stored generation metadata."""

from __future__ import annotations

import re
from collections import Counter


def _legacy_gaps(note: str | None) -> list[dict[str, str]]:
    if not note:
        return []
    match = re.search(r"GAPS\s*\n([\s\S]*?)(?=\n\s*\n?IMPROVEMENT PLAN|$)", note, re.IGNORECASE)
    if not match:
        return []
    return [
        {"key": re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")[:80], "label": label[:100], "action": "Add one verifiable example to your profile before targeting more roles requiring it."}
        for line in match.group(1).splitlines()
        if (label := re.sub(r"^[•*\-]\s*", "", line).strip())
        and "no material" not in label.casefold()
    ]


def synthesize_insight(jobs: list, total_count: int) -> dict[str, str | None]:
    occurrences: Counter[str] = Counter()
    examples: dict[str, dict[str, str]] = {}
    for job in jobs:
        metadata = job.generation_metadata or {}
        gaps = metadata.get("gaps") if isinstance(metadata, dict) else None
        for gap in (gaps or _legacy_gaps(job.strategic_note)):
            key = str(gap.get("key") or "").strip()
            label = str(gap.get("requirement") or gap.get("label") or "").strip()
            if not key or not label:
                continue
            occurrences[key] += 1
            examples.setdefault(key, {
                "label": label,
                "action": str(gap.get("deliverable") or gap.get("action") or ""),
            })
    repeated = [(count, key) for key, count in occurrences.items() if count >= 2]
    if not repeated:
        return {"headline": None, "observed": None, "gap": None, "action": None}
    count, key = max(repeated, key=lambda pair: (pair[0], -list(occurrences).index(pair[1])))
    example = examples[key]
    label = example["label"]
    return {
        "headline": f"{label} Repeats Across Roles"[:100],
        "observed": f"{label} appeared as a gap in {count} of your {len(jobs)} most recent applications.",
        "gap": f"Your current evidence does not yet prove {label} at the level these roles request.",
        "action": example["action"] or f"Add one verifiable {label} example to the most relevant project.",
    }
