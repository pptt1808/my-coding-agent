"""Conversation compaction (specs/compact.md CP1-CP3, B1/P0).

Compresses a long session into a structured LLM summary (goals / confirmed
facts / done / remaining / next step) so the conversation can continue without
context decay. Complements the heuristic `History.summarize_oldest` fallback.
"""
from __future__ import annotations

from typing import Any

from .llm import LLMClient

COMPACT_SYSTEM = (
    "You manage context for a coding agent. Compress the following conversation "
    "into a concise structured summary that preserves everything needed to "
    "continue the task: the goal, confirmed facts about the repository, what has "
    "already been done, what remains, and the next step. Keep it under 400 words."
)


def summarize_conversation(llm: LLMClient, messages: list[dict[str, Any]]) -> str:
    """Ask the LLM to compress the conversation; returns the summary text (CP1)."""
    if not messages:
        return ""
    transcript = "\n".join(f"[{m.get('role', '?')}] {m.get('content', '')}" for m in messages)
    result = llm.complete(COMPACT_SYSTEM, [{"role": "user", "content": transcript}], tools=[])
    return result.text
