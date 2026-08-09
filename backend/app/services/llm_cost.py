from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation_audit import LLMCall
from app.services.llm_client import ToolCallResult


# First-party global Claude API list prices in USD per million tokens.
# Keep pricing here, not scattered through API schemas, so accounting remains
# correct when a planner/writer model changes.
MODEL_RATES: dict[str, dict[str, Decimal]] = {
    "claude-sonnet-4-6": {
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cache_read": Decimal("0.30"),
        "cache_write": Decimal("3.75"),
    },
    "claude-haiku-4-5": {
        "input": Decimal("1.00"),
        "output": Decimal("5.00"),
        "cache_read": Decimal("0.10"),
        "cache_write": Decimal("1.25"),
    },
    # Standard post-introductory pricing. We deliberately do not build unit
    # economics around a temporary promotional rate.
    "claude-sonnet-5": {
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cache_read": Decimal("0.30"),
        "cache_write": Decimal("3.75"),
    },
}


def calculate_llm_cost(model: str, usage: ToolCallResult) -> float:
    rates = MODEL_RATES.get(model, MODEL_RATES["claude-sonnet-4-6"])
    million = Decimal("1000000")
    cost = (
        Decimal(usage.input_tokens or 0) * rates["input"]
        + Decimal(usage.output_tokens or 0) * rates["output"]
        + Decimal(usage.cache_read_tokens or 0) * rates["cache_read"]
        + Decimal(usage.cache_write_tokens or 0) * rates["cache_write"]
    ) / million
    return float(cost)


def record_llm_call(
    db: AsyncSession,
    *,
    user_id: UUID,
    job_id: int | None,
    purpose: str,
    model: str,
    usage: ToolCallResult,
) -> LLMCall:
    row = LLMCall(
        user_id=user_id,
        job_id=job_id,
        purpose=purpose,
        model=model,
        input_tokens=usage.input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
        cache_read_tokens=usage.cache_read_tokens or 0,
        cache_write_tokens=usage.cache_write_tokens or 0,
        latency_ms=usage.latency_ms or None,
        cost_usd=calculate_llm_cost(model, usage),
    )
    db.add(row)
    return row
