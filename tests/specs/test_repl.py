"""Contract tests for specs/cli.md — R1-R8 (interactive REPL + slash commands).

Uses a scripted FakeLLM (no network). Written BEFORE implementation (RED).
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult
from agent.repl import ReplSession


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    def complete(self, system_prompt, messages, tools=None):
        self.calls.append(list(messages))
        return LLMResult(text="ok", usage={"total_tokens": 5})


@pytest.fixture
def session():
    fake = FakeLLM()
    sess = ReplSession(Config(api_key="x"), llm=fake)
    return sess, fake


def test_r1_plain_line_runs_turn_and_returns_answer(session):
    sess, _ = session
    assert sess.handle("do something") == ["ok"]


def test_r2_consecutive_turns_share_history(session):
    sess, fake = session
    sess.handle("first task")
    sess.handle("second task")
    assert fake.calls[1][0]["content"] == "first task"  # history carries over
    assert fake.calls[1][-1]["content"] == "second task"  # new turn appended


def test_r3_exit_stops_session(session):
    sess, _ = session
    sess.handle("/exit")
    assert sess.running is False


def test_r4_clear_resets_history(session):
    sess, fake = session
    sess.handle("first task")
    sess.handle("/clear")
    sess.handle("fresh start")
    last_messages = fake.calls[-1]
    assert len(last_messages) == 1
    assert last_messages[0]["content"] == "fresh start"


def test_r5_status_shows_model_and_tokens(session):
    sess, _ = session
    sess.handle("work")
    lines = sess.handle("/status")
    text = "\n".join(lines)
    assert "model=" in text
    assert "tokens=" in text
    assert "steps=" in text


def test_r6_compact_replaces_history_with_summary(session):
    sess, fake = session
    sess.handle("do the bug fix")
    sess.handle("/compact")
    sess.handle("continue")
    first_content = fake.calls[-1][0]["content"]
    assert "[compacted conversation]" in first_content or "compacted" in first_content


def test_r7_unknown_command_help_no_crash(session):
    sess, _ = session
    lines = sess.handle("/bogus")
    assert any("/help" in line for line in lines)


def test_r8_model_switch_shown_in_status(session):
    sess, _ = session
    sess.handle("/model deepseek-v4-pro")
    text = "\n".join(sess.handle("/status"))
    assert "deepseek-v4-pro" in text


def test_r9_save_and_resume_restores_history(tmp_path):
    fake = FakeLLM()
    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    sess.handle("first task")
    lines = sess.handle("/save my-session")
    assert any("my-session" in line for line in lines)
    sess2 = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    sess2.handle("/resume my-session")
    sess2.handle("second task")
    assert fake.calls[-1][0]["content"] == "first task"  # resumed history carried over
    assert fake.calls[-1][-1]["content"] == "second task"


def test_r10_cost_shows_token_split(session):
    sess, _ = session
    sess.handle("work")
    text = "\n".join(sess.handle("/cost"))
    assert "input" in text and "output" in text and "total" in text
