"""Parse a model turn into an executable tool call (N4).

Preference order (B10): model-native structured tool calling first; if the
provider/gateway returns malformed or text-only output, fall back to a
regex/JSON parser.

Spec: specs/parser.md (to be written). Placeholder for now.
"""
from __future__ import annotations

from typing import Any

from .llm import LLMResult, ToolCall


def parse_tool_calls(result: LLMResult) -> list[ToolCall]:
    """Return structured tool calls from a model turn.

    Phase 1+ implements two paths:
      1) native          -> pass through `result.tool_calls`
      2) text fallback   -> scan the text for <!-- TOOL --> blocks / JSON and parse
    """
    # Native path (best case) is already surfaced by the client.
    if result.tool_calls:
        return result.tool_calls
    raise NotImplementedError("Text-fallback parsing lands in Phase 1+ (specs/parser.md).")


def parse_tool_call_from_text(text: str) -> ToolCall | None:
    """Fallback: parse a single tool invocation out of raw model text."""
    raise NotImplementedError("specs/parser.md")
