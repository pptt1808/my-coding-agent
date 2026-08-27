"""LLM-as-judge rubric scoring (B8, T4).

Grades dimensions that deterministic tests cannot capture: code quality,
whether the change is minimal and on-topic, adherence to conventions. Outputs
a 0-5 score per dimension plus a one-line rationale.

Spec: specs/eval-judge.md (to be written). Placeholder.
"""
from __future__ import annotations


def score(trajectory: str, final_diff: str, rubric: dict[str, str]) -> dict[str, float]:
    """Return per-dimension scores (0-5) plus an overall grade.

    Prompt pattern: give the task, the agent trajectory, the final change, then
    ask the judge to score each rubric dimension with a short rationale.
    """
    raise NotImplementedError("eval/judge.py lands in Phase 6 (specs/eval-judge.md).")
