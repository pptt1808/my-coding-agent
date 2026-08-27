"""Report aggregation (specs/eval-report.md ER1-ER4).

summarize() -> pass rate, avg elapsed, avg tokens, per-task detail, rubric averages.
render_markdown() -> a human-readable report for复盘 and the demo.
"""
from __future__ import annotations

from pathlib import Path

from .harness import EvalRecord
from .tasks import Task


def summarize(records: list[EvalRecord]) -> dict[str, object]:
    """Aggregate a batch of EvalRecord into a readable summary dict."""
    n = len(records)
    tasks_detail = [
        {
            "task_id": r.task_id,
            "passed": r.passed,
            "elapsed_s": round(r.elapsed_s, 2),
            "tokens": r.tokens,
            "rubric_scores": r.rubric_scores,
        }
        for r in records
    ]

    rubric_dims: dict[str, list[float]] = {}
    for r in records:
        for dim, score in r.rubric_scores.items():
            rubric_dims.setdefault(dim, []).append(float(score))

    return {
        "n_tasks": n,
        "n_passed": sum(1 for r in records if r.passed),
        "pass_rate": round(sum(1 for r in records if r.passed) / n, 3) if n else 0.0,
        "avg_elapsed_s": round(sum(r.elapsed_s for r in records) / n, 2) if n else 0.0,
        "avg_tokens": round(sum(r.tokens for r in records) / n, 1) if n else 0,
        "tasks": tasks_detail,
        "rubric_avg": {dim: round(sum(scores) / len(scores), 2)
                       for dim, scores in rubric_dims.items()},
    }


def render_markdown(summary: dict[str, object]) -> str:
    """Render the summary as a markdown report."""
    lines = ["# Eval report", ""]
    lines.append(f"- tasks: {summary['n_tasks']}  passed: {summary['n_passed']}  "
                 f"pass rate: {summary['pass_rate'] * 100:.0f}%")
    lines.append(f"- avg elapsed: {summary['avg_elapsed_s']}s  avg tokens: {summary['avg_tokens']}")
    if summary["rubric_avg"]:
        rubric = ", ".join(f"{dim}={score}" for dim, score in summary["rubric_avg"].items())
        lines.append(f"- rubric avg: {rubric}")
    lines.append("")
    lines.append("| task | pass | elapsed (s) | tokens |")
    lines.append("|---|---|---|---|")
    for t in summary["tasks"]:  # type: ignore[union-attr]
        lines.append(f"| {t['task_id']} | {'PASS' if t['passed'] else 'FAIL'} | "
                     f"{t['elapsed_s']} | {t['tokens']} |")
    lines.append("")
    return "\n".join(lines)
