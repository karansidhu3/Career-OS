# CareerOS résumé benchmark

This suite freezes six materially different roles so prompt and generation changes are evaluated across the product, not against one convenient résumé:

1. Canonical — Python/Linux backend
2. Solace — Java/full-stack/event systems
3. Microsoft — general software engineering
4. FGF Brands — AI engineering
5. DraftKings — frontend
6. RBC — quantitative/data engineering

The job descriptions are concise preserved summaries of the real applications stored in CareerOS (job IDs are recorded in `cases.json`). They deliberately cover different evidence and different genuine gaps.

## What is scored

Every case receives deterministic 0–10 scores for factual grounding, job relevance, recruiter clarity, technical depth, ownership accuracy, metric quality, cover-letter focus, one-page density, and grammar. Cost and repair use are recorded separately.

New generations store a self-contained `generation_metadata.evaluation_artifact` with the exact bullet citations and evidence needed for offline scoring. The evaluator never calls an LLM.

## Running the suite

Collect the six `evaluation_artifact` objects from regenerated benchmark jobs into one JSON object keyed by case ID, then run from `backend/`:

```bash
python -m app.services.resume_benchmark \
  --cases benchmarks/cases.json \
  --artifacts /path/to/candidate-artifacts.json \
  --baseline benchmarks/baseline.json \
  --output /path/to/candidate-report.json
```

Exit code `1` means the change must not ship. A candidate fails when any quality dimension regresses, overall case quality regresses, median cost rises by more than $0.001 without at least a 0.25 quality-point gain, repair rate rises without that quality gain, or any case is missing.

`baseline.json` begins as the agreed minimum quality floor. Once all six roles have been regenerated on generation v3.6 or later, replace it with that measured report; future prompt changes then compare directly against the last accepted production-quality generation.

CI runs the evaluator's unit and policy tests without Anthropic credentials or network access. Regenerating benchmark artifacts is an explicit pre-merge step for any prompt/model/selection change because doing so spends the user's API credits.

The baseline also stores a hash of the live writer prompt, repair prompt, output schema, and generation version. CI fails when that contract changes without a corresponding benchmark-baseline refresh.
