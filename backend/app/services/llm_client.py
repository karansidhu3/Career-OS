"""Provider-agnostic seam for the forced-tool-call completions generation.py needs.

Every call site in generation.py sends a system prompt + messages and forces a single
tool call, then reads the tool's input and token usage. LLMClient captures exactly that
shape. AnthropicAdapter is the only implementation, constructed with the requesting
user's own decrypted API key (see app.services.credentials) — there is no shared
fallback key, so every provider call is billed to the user who ran it.
"""
import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import anthropic


@dataclass
class ToolCallResult:
    tool_input: dict
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: int = 0


class LLMClient(ABC):
    @abstractmethod
    async def call_tool(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str | list[dict],
        messages: list[dict],
        tool: dict,
        timeout: float,
    ) -> ToolCallResult:
        """Send messages, forcing the given tool, and return its parsed input + usage."""

    async def call_structured(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str | list[dict],
        messages: list[dict],
        schema: dict,
        timeout: float,
    ) -> ToolCallResult:
        """Return schema-constrained JSON without tool-call prompt overhead."""
        raise NotImplementedError


class AnthropicAdapter(LLMClient):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def call_tool(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str | list[dict],
        messages: list[dict],
        tool: dict,
        timeout: float,
    ) -> ToolCallResult:
        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        started = time.perf_counter()
        response = await asyncio.wait_for(
            client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
            ),
            timeout=timeout,
        )
        tool_use = next(b for b in response.content if b.type == "tool_use")
        usage = response.usage
        return ToolCallResult(
            tool_input=tool_use.input,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )

    async def call_structured(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str | list[dict],
        messages: list[dict],
        schema: dict,
        timeout: float,
    ) -> ToolCallResult:
        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        started = time.perf_counter()
        # Raw JSON schemas may contain constraints that Anthropic's grammar
        # compiler does not support (for example minItems > 1). The SDK's
        # official transformer strips those provider-incompatible constraints
        # and preserves them in descriptions. Callers still validate the
        # original schema's business rules after the response.
        provider_schema = anthropic.transform_schema(schema)
        response = await asyncio.wait_for(
            client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": provider_schema,
                    }
                },
            ),
            timeout=timeout,
        )
        text_block = next(block for block in response.content if block.type == "text")
        usage = response.usage
        return ToolCallResult(
            tool_input=json.loads(text_block.text),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )


def get_llm_client(api_key: str) -> LLMClient:
    return AnthropicAdapter(api_key=api_key)
