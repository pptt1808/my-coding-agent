"""LLM-as-judge rubric scoring (specs/eval-judge.md EJ1-EJ4, B8, Phase 6).

Grades dimensions that deterministic tests cannot capture (code quality,
whether the change is minimal / on-topic, adherence to conventions). A strong
model (EVAL_MODEL by default) reads the task, the agent trajectory and the
final diff, then returns a 0-5 score per rubric dimension + overall grade +
a one-line rationale.

Robustness: unparseable or partial judge output never crashes — missing
dimensions are skipped, out-of-range scores are clamped, garbage -> {}.
"""
from __future__ import annotations

import json
import re
from typing import Any

from agent.config import Config
from agent.llm import LLMClient, LLMResult

JUDGE_SYSTEM = (
    "You are an expert software engineering judge. Score the agent's solution "
    "on each given dimension from 0 to 5 (5 = excellent). Base your judgment on "
    "the task, the agent's trajectory and the final diff. Reply with ONLY a JSON "
    'object shaped like {"<dimension>": 0-5, ..., "overall": 0-5, "rationale": '
    '"one short sentence"}. Do not output anything else.'
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _clamp(value: float) -> float:
    return max(0.0, min(5.0, value))


def parse_scores(text: str, rubric: dict[str, str]) -> dict[str, float]:
    """Parse the judge's JSON reply into {dimension: 0-5, "overall": 0-5}.

    Missing dimensions are skipped; out-of-range values are clamped;
    unparseable text yields {}.
    """
    match = _JSON_RE.search(text)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}

    scores: dict[str, float] = {}
    for dim in rubric:
        if dim in data and isinstance(data[dim], (int, float)):
            scores[dim] = _clamp(float(data[dim]))
    if isinstance(data.get("overall"), (int, float)):
        scores["overall"] = _clamp(float(data["overall"]))
    return scores


class Judge:
    """Rubric-based scorer used by the eval harness (Phase 6)."""

    def __init__(self, config: Config, llm: LLMClient | None = None, model: str | None = None) -> None:
        self._llm = llm or LLMClient(config, model=model or config.eval_model_name)
        self.last_rationale: str = ""

    def score(self, task_description: str, trajectory: str, final_diff: str,
              rubric: dict[str, str]) -> dict[str, float]:
        """Score the agent's solution; returns {dimension: 0-5, overall: 0-5}."""
        if not rubric:
            return {}
        prompt = (
            f"TASK:\n{task_description}\n\n"
            f"AGENT TRAJECTORY (abridged):\n{trajectory}\n\n"
            f"FINAL DIFF:\n{final_diff}\n\n"
            f"DIMENSIONS:\n" + "\n".join(f"- {dim}: {desc}" for dim, desc in rubric.items())
        )
        result: LLMResult = self._llm.complete(JUDGE_SYSTEM, [{"role": "user", "content": prompt}], tools=[])
        scores = parse_scores(result.text, rubric)
        # Record the one-line rationale for reports / debugging.
        match = _JSON_RE.search(result.text)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict) and isinstance(data.get("rationale"), str):
                    self.last_rationale = data["rationale"]
            except json.JSONDecodeError:
                pass
        return scores
