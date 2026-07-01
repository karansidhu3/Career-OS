"""Provider-agnostic seam for the forced-tool-call completions generation.py needs.

Every call site in generation.py sends a system prompt + messages and forces a single
tool call, then reads the tool's input and token usage. LLMClient captures exactly that
shape. AnthropicAdapter is the only implementation today; Phase 3 (per-user BYO API
keys) will construct it with the requesting user's decrypted key instead of
settings.anthropic_api_key.
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass

import anthropic

from app.config import settings


@dataclass
class ToolCallResult:
    tool_input: dict
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


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
        )


def get_llm_client() -> LLMClient:
    return AnthropicAdapter(api_key=settings.anthropic_api_key)
