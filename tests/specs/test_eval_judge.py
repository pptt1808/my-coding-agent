"""Contract tests for specs/eval-judge.md — EJ1-EJ4.

The judge calls an LLM; tests inject a fake one (no network).
Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

from agent.config import Config
from agent.llm import LLMResult
from eval.judge import Judge


class FakeJudgeLLM:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls = 0

    def complete(self, system_prompt, messages, tools=None):
        self.calls += 1
        return LLMResult(text=self.response_text, usage={"total_tokens": 20})


RUBRIC = {"quality": "code quality", "minimal": "minimal change"}


def _judge(fake) -> Judge:
    return Judge(Config(api_key="x"), llm=fake)


def test_ej1_scores_every_rubric_dimension():
    fake = FakeJudgeLLM('{"quality": 4, "minimal": 3, "overall": 4, "rationale": "solid fix"}')
    scores = _judge(fake).score("fix the bug", "trajectory...", "--- a/x\n+++ b/x", RUBRIC)
    assert scores["quality"] == 4.0
    assert scores["minimal"] == 3.0


def test_ej2_has_overall_and_rationale():
    fake = FakeJudgeLLM('{"quality": 4, "minimal": 3, "overall": 4, "rationale": "solid fix"}')
    judge = _judge(fake)
    scores = judge.score("fix the bug", "trajectory...", "diff", RUBRIC)
    assert scores["overall"] == 4.0
    assert judge.last_rationale == "solid fix"


def test_ej3_missing_dimension_skipped_no_crash():
    fake = FakeJudgeLLM('{"quality": 4}')  # 'minimal' missing
    scores = _judge(fake).score("t", "tr", "d", RUBRIC)
    assert scores["quality"] == 4.0
    assert "minimal" not in scores


def test_ej3b_garbage_response_no_crash():
    fake = FakeJudgeLLM("this is not json at all")
    scores = _judge(fake).score("t", "tr", "d", RUBRIC)
    assert scores == {}


def test_ej4_empty_rubric_returns_empty():
    fake = FakeJudgeLLM("whatever")
    judge = _judge(fake)
    assert judge.score("t", "tr", "d", {}) == {}
    assert fake.calls == 0  # no LLM call needed for an empty rubric


def test_ej3c_out_of_range_score_clamped():
    fake = FakeJudgeLLM('{"quality": 99, "minimal": -1, "overall": 4}')
    scores = _judge(fake).score("t", "tr", "d", RUBRIC)
    assert scores["quality"] == 5.0
    assert scores["minimal"] == 0.0
