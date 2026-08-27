"""Context / conversation history management (N7, specs/context.md CT1-CT5).

Full transcript is carried by default (B7); large outputs are truncated, and
`summarize_oldest` compresses the oldest messages when the token budget is
exceeded. Token counts are cheap deterministic estimates (chars // 4).
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
        """CT4: return a copy, not the internal mutable list."""
        return list(self._messages)

    def truncate_large_output(self, text: str, cap: int = 8000) -> str:
        """CT2/CT3: cap long text with a truncation marker; short text unchanged."""
        if len(text) <= cap:
            return text
        return text[:cap] + f"\n... [truncated {len(text) - cap} chars]"

    @staticmethod
    def _estimate_tokens(content: str) -> int:
        return max(1, len(content) // 4)

    def _total_tokens(self) -> int:
        return sum(self._estimate_tokens(str(m.get("content", ""))) for m in self._messages)

    def summarize_oldest(self) -> None:
        """CT5: compress oldest messages until the total token estimate fits.

        Deterministic heuristic summary (head + marker); an LLM-based summarizer
        can replace this later without changing the contract.
        """
        while self._total_tokens() > self._max_tokens and self._messages:
            oldest = self._messages.pop(0)
            content = str(oldest.get("content", ""))
            head = content[:50]
            summary = head + (" ... [summarized]" if len(content) > 50 else "")
            if len(summary) >= len(content):
                # Already as small as the summary would be; drop it instead.
                continue
            self._messages.insert(0, {"role": oldest.get("role", "user"), "content": summary})
