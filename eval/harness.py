"""Harness runner: execute a Task against the running agent, isolated.

Flow (SWE-bench style, B9):
  1) copy repo seed into an isolated temp dir (+ venv)
  2) run the agent inside it, capture full trajectory
  3) collect the agent's diff / final workspace
  4) apply patch, run hidden tests, judge -> PASS/FAIL + rubric score
  5) produce a report record (耗时, tokens, per-dimension scores)

Spec: specs/eval-harness.md (to be written). Placeholder.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .tasks import Task


@dataclass
class EvalRecord:
    task_id: str
    passed: bool = False
    rubric_scores: dict[str, float] = field(default_factory=dict)
    elapsed_s: float = 0.0
    tokens: int = 0
    trajectory: str = ""


def run_task(task: Task, workdir: str | None = None) -> EvalRecord:
    """Run one task against the agent and return a graded record."""
    raise NotImplementedError("eval/harness.py lands in Phase 5 (specs/eval-harness.md).")
