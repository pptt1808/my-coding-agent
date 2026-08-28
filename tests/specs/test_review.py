"""Contract tests for specs/review.md — RV1-RV4.

Uses fake LLM + fake judge (no network). Written BEFORE implementation (RED).
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.diff import collect_diff
from agent.llm import LLMResult
from agent.repl import ReplSession


class FakeLLM:
    def complete(self, _sys, _messages, _tools=None):
        return LLMResult(text="ok", usage={"total_tokens": 1})


class FakeJudge:
    def __init__(self) -> None:
        self.last_call = None

    def score(self, task_description, trajectory, final_diff, rubric):
        self.last_call = (task_description, trajectory, final_diff, rubric)
        return {"correctness": 4.0, "quality": 3.5, "minimal": 4.0, "overall": 4.0}


@pytest.fixture
def sess(tmp_path):
    return ReplSession(Config(api_key="x", workdir=tmp_path), llm=FakeLLM(), judge=FakeJudge())


def test_rv1_review_reports_changed_files(sess, tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    lines = "\n".join(sess.handle("/review"))
    assert "a.py" in lines


def test_rv2_review_includes_judge_scores(sess, tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    lines = "\n".join(sess.handle("/review"))
    assert "correctness" in lines
    assert sess._judge.last_call is not None


def test_rv3_no_changes_nothing_to_review(sess):
    lines = "\n".join(sess.handle("/review"))
    assert "nothing to review" in lines


def test_rv4_collect_diff():
    before = {"a.py": "x = 1\n", "same.txt": "same\n"}
    after = {"a.py": "x = 2\n", "same.txt": "same\n", "new.py": "y = 3\n"}
    diff = collect_diff(before, after)
    assert "a.py" in diff
    assert "x = 2" in diff
    assert "same.txt" not in diff
    assert "new.py" in diff
