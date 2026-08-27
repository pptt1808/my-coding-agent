"""Contract tests for specs/eval-harness.md — EH1-EH4.

Uses scripted FakeLLM agents (no network). Written BEFORE implementation (RED).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agent.config import Config
from agent.llm import LLMResult, ToolCall
from eval.harness import run_task
from eval.tasks import Task


def _make_task(tmp_path) -> Task:
    seed = tmp_path / "seed"
    (seed / "src").mkdir(parents=True)
    (seed / "src/util.py").write_text(
        "def add(a, b):\n    return a + b  # BUG\n\ndef sub(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    hidden = tmp_path / "hidden"
    hidden.mkdir()
    (hidden / "test_util.py").write_text(
        'import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parent.parent / "src"))\n'
        "from util import add\n\ndef test_fixed():\n    assert add(10, 4) == 6\n",
        encoding="utf-8",
    )
    return Task(id="t1", description="Fix add() so add(10, 4) == 6.", repo_seed=seed, hidden_tests=hidden)


class FixingLLM:
    """Reads util.py, writes the fix, then answers — makes the hidden test pass."""

    def __init__(self) -> None:
        self.calls = []

    def complete(self, _sys, messages, _tools):
        self.calls.append(list(messages))
        n = len(self.calls)
        if n == 1:
            return LLMResult(text="", tool_calls=[ToolCall("c1", "read_file", {"path": "src/util.py"})],
                             usage={"total_tokens": 10})
        if n == 2:
            content = next(
                (str(m["content"]) for m in reversed(messages) if m.get("role") == "tool"),
                "",
            )
            fixed = content.replace("a + b", "a - b")
            return LLMResult(text="", tool_calls=[ToolCall("c2", "write_file",
                                                          {"path": "src/util.py", "content": fixed})],
                             usage={"total_tokens": 10})
        return LLMResult(text="fixed", usage={"total_tokens": 10})


class DoNothingLLM:
    def complete(self, _sys, _messages, _tools):
        return LLMResult(text="I did nothing", usage={"total_tokens": 5})


def _config(tmp_path) -> Config:
    return Config(api_key="x", workdir=tmp_path, max_steps=10, max_tool_calls=20)


def test_eh1_seed_repo_untouched(tmp_path):
    task = _make_task(tmp_path)
    seed_before = (task.repo_seed / "src/util.py").read_text(encoding="utf-8")
    run_task(task, _config(tmp_path), llm=FixingLLM())
    assert (task.repo_seed / "src/util.py").read_text(encoding="utf-8") == seed_before


def test_eh2_record_has_elapsed_tokens_trajectory(tmp_path):
    task = _make_task(tmp_path)
    rec = run_task(task, _config(tmp_path), llm=FixingLLM())
    assert rec.elapsed_s >= 0.0
    assert rec.tokens >= 10
    assert rec.trajectory  # non-empty step log


def test_eh3_passes_when_hidden_tests_pass(tmp_path):
    task = _make_task(tmp_path)
    rec = run_task(task, _config(tmp_path), llm=FixingLLM())
    assert rec.passed is True


def test_eh3b_fails_when_hidden_tests_fail(tmp_path):
    task = _make_task(tmp_path)
    rec = run_task(task, _config(tmp_path), llm=DoNothingLLM())
    assert rec.passed is False


def test_eh4_isolated_dir_cleaned_up(tmp_path, monkeypatch):
    import tempfile

    captured: list[str] = []
    real_mkdtemp = tempfile.mkdtemp

    def spy_mkdtemp(*args, **kwargs):
        path = real_mkdtemp(*args, **kwargs)
        captured.append(path)
        return path

    monkeypatch.setattr(tempfile, "mkdtemp", spy_mkdtemp)
    task = _make_task(tmp_path)
    run_task(task, _config(tmp_path), llm=FixingLLM())
    assert captured, "harness should create an isolated dir"
    assert not Path(captured[0]).exists(), "isolated dir must be removed after the run"
