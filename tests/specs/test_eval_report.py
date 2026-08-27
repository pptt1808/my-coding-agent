"""Contract tests for specs/eval-report.md — ER1-ER4.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

from eval.harness import EvalRecord
from eval.report import render_markdown, summarize


def _rec(task_id, passed, elapsed=1.0, tokens=100, rubric=None):
    return EvalRecord(
        task_id=task_id,
        passed=passed,
        elapsed_s=elapsed,
        tokens=tokens,
        rubric_scores=rubric or {"quality": 4.0},
        trajectory="steps...",
    )


def test_er1_summary_has_pass_rate_time_tokens():
    s = summarize([_rec("a", True, 2.0, 100), _rec("b", False, 3.0, 200)])
    assert s["pass_rate"] == 0.5
    assert s["avg_elapsed_s"] == 2.5
    assert s["avg_tokens"] == 150


def test_er2_summary_has_per_task_detail():
    s = summarize([_rec("a", True, 1.0, 10), _rec("b", False, 2.0, 20)])
    detail = {d["task_id"]: d["passed"] for d in s["tasks"]}
    assert detail == {"a": True, "b": False}


def test_er3_summary_has_rubric_averages():
    s = summarize([_rec("a", True, rubric={"quality": 4.0, "minimal": 3.0}),
                   _rec("b", False, rubric={"quality": 2.0, "minimal": 1.0})])
    assert s["rubric_avg"]["quality"] == 3.0
    assert s["rubric_avg"]["minimal"] == 2.0


def test_er4_markdown_contains_results():
    md = render_markdown(summarize([_rec("a", True, 1.5, 120), _rec("b", False, 2.5, 240)]))
    assert "pass rate" in md
    assert "50" in md  # 1/2
    assert "a" in md and "b" in md
