"""Report aggregation: pass rate, avg time, tokens, per-dimension scores.

Spec: specs/eval-report.md (to be written). Placeholder.
"""
from __future__ import annotations

from pathlib import Path

from .harness import EvalRecord


def summarize(records: list[EvalRecord]) -> dict[str, object]:
    """Aggregate a batch of EvalRecord into a readable summary dict."""
    raise NotImplementedError("eval/report.py lands in Phase 5 (specs/eval-report.md).")


def render_markdown(summary: dict[str, object]) -> str:
    """Turn a summary into a markdown report for复盘 / demo."""
    raise NotImplementedError("eval/report.py lands in Phase 5 (specs/eval-report.md).")
