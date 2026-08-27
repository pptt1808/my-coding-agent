"""Context / conversation history management (N7).

Phase 1 keeps a full transcript; Phase 3 (T1) adds token counting, history
summarization and selective context assembly on top.

Spec: specs/context.md (to be written). Placeholder for now.
"""
from __future__ import annotations

from typing import Any


class History:
    """Ordered transcript of turns fed back into the next model call."""

    def __init__(self, max_tokens: int = 100_000) -> None:
        self._messages: list[dict[str, Any]] = []
        self._max_tokens = max_tokens

    def append(self, message: dict[str, Any]) -> None:
        self._messages.append(message)

    def as_list(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def truncate_large_output(self, text: str, cap: int = 8000) -> str:
        """Replace very long tool outputs (files / command stdout) with a capped head + marker."""
        if len(text) <= cap:
            return text
        return text[:cap] + f"\n... [truncated {len(text) - cap} chars]"

    def summarize_oldest(self) -> None:
        raise NotImplementedError("History summarization lands in Phase 3 (specs/context.md).")
