"""Model client — single completion + native tool-calling (N1).

Phase 1 will implement this against an OpenAI-compatible gateway using the
vendor client library and *native tool calling* only (no agent frameworks).

Spec: specs/llm.md (to be written). Placeholder for now.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import Config


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResult:
    """A single model turn: either tool calls, or a final text answer."""
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


class LLMClient:
    """Thin wrapper over the OpenAI-compatible chat completions API.

    TODO(Phase 1):
      - call `client.chat.completions.create(..., tools=TOOL_SCHEMAS, tool_choice="auto")`
      - map the response's `tool_calls` into `ToolCall` objects
      - record token usage
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResult:
        raise NotImplementedError("LLMClient.complete is implemented in Phase 1 (specs/llm.md).")
