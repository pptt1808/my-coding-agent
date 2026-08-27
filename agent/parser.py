"""Parse a model turn into executable tool calls (N4, specs/parser.md P1-P4).

Preference order (B10): native structured tool calling first; if the model
returned none, fall back to parsing a text tool block. Never raises on
unparseable text — returns None so the loop can treat it as a final answer.
"""
from __future__ import annotations

import json
import re
from uuid import uuid4

from .llm import LLMResult, ToolCall

_TOOL_BLOCK_RE = re.compile(r"<tool\b([^>]*)>(.*?)</tool>", re.DOTALL | re.IGNORECASE)
_NAME_RE = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
_ARGS_RE = re.compile(r"(\{.*\})", re.DOTALL)


def parse_tool_calls(result: LLMResult) -> list[ToolCall]:
    """Return structured tool calls from a model turn.

    P1: native path — passthrough of structured tool calls.
    P3: if none native, try the text fallback; None if unparseable.
    """
    if result.tool_calls:
        return list(result.tool_calls)
    fallback = parse_tool_call_from_text(result.text)
    return [fallback] if fallback is not None else []


def parse_tool_call_from_text(text: str) -> ToolCall | None:
    """Fallback: parse a single `<tool name="...">{"args":...}</tool>` block.

    P2: extracts name + JSON arguments dict. P3: unparseable -> None.
    """
    match = _TOOL_BLOCK_RE.search(text)
    if not match:
        return None
    name_match = _NAME_RE.search(match.group(1))
    if not name_match:
        return None
    args_match = _ARGS_RE.search(match.group(2))
    try:
        arguments = json.loads(args_match.group(1)) if args_match else {}
    except json.JSONDecodeError:
        return None
    if not isinstance(arguments, dict):
        return None
    return ToolCall(id=f"call_{uuid4().hex[:8]}", name=name_match.group(1), arguments=arguments)
