"""Contract tests for specs/tasklist.md — T1-T4.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult
from agent.repl import ReplSession


class FakeLLM:
    def __init__(self) -> None:
        self.systems: list[str] = []
        self.calls = 0

    def complete(self, system_prompt, _messages, _tools=None):
        self.systems.append(system_prompt)
        self.calls += 1
        return LLMResult(text="ok", usage={"total_tokens": 5})


@pytest.fixture
def sess(tmp_path):
    fake = FakeLLM()
    return ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake), fake


def test_t1_task_add_appears_in_system_prompt(sess):
    s, fake = sess
    s.handle("/task add fix the add() bug")
    s.handle("work on it")
    assert any("fix the add() bug" in sys_p for sys_p in fake.systems)


def test_t2_task_list_shows_entries(sess):
    s, _ = sess
    s.handle("/task add one")
    s.handle("/task add two")
    lines = s.handle("/task list")
    text = "\n".join(lines)
    assert "1. one" in text and "2. two" in text


def test_t3_task_done_removes(sess):
    s, _ = sess
    s.handle("/task add one")
    s.handle("/task add two")
    s.handle("/task done 1")
    lines = s.handle("/task list")
    text = "\n".join(lines)
    assert "one" not in text
    assert "1. two" in text  # remaining item is renumbered


def test_t4_task_clear_empties(sess):
    s, _ = sess
    s.handle("/task add one")
    s.handle("/task clear")
    lines = s.handle("/task list")
    assert all("one" not in line for line in lines)
