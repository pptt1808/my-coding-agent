"""Contract tests for specs/compact.md — CP1-CP3.

Uses a scripted FakeLLM (no network). Written BEFORE implementation (RED).
"""
from __future__ import annotations

import pytest

from agent.compact import summarize_conversation
from agent.config import Config
from agent.llm import LLMResult, ToolCall
from agent.loop import CodingAgent


class FakeLLM:
    def __init__(self, response_text: str = "SUMMARY: fix add() in src/util.py") -> None:
        self.response_text = response_text
        self.calls = 0

    def complete(self, system_prompt, messages, tools=None):
        self.calls += 1
        return LLMResult(text=self.response_text, usage={"total_tokens": 10})


def test_cp1_summarize_returns_text():
    fake = FakeLLM("the summary")
    out = summarize_conversation(fake, [{"role": "user", "content": "hello"}])
    assert out == "the summary"
    assert fake.calls == 1


def test_cp2_compact_replaces_with_single_summary_message():
    fake = FakeLLM("SUMMARY: fix add() in src/util.py")
    agent = CodingAgent(Config(api_key="x"), llm=fake)
    new_messages = agent.compact([{"role": "user", "content": "long history"},
                                  {"role": "assistant", "content": "more"}])
    assert len(new_messages) == 1
    assert "SUMMARY: fix add()" in new_messages[0]["content"]
    assert "[compacted conversation]" in new_messages[0]["content"]


def test_cp3_empty_history_no_llm_call():
    fake = FakeLLM()
    agent = CodingAgent(Config(api_key="x"), llm=fake)
    assert agent.compact([]) == []
    assert fake.calls == 0


class AutoCompactFake:
    """Keeps issuing read_file tool calls so the loop keeps running; records history."""

    def __init__(self) -> None:
        self.calls = 0
        self.seen_compacted = False

    def complete(self, system_prompt, messages, tools=None):
        self.calls += 1
        if any(str(m.get("content", "")).startswith("[compacted conversation]") for m in messages):
            self.seen_compacted = True
        return LLMResult(
            text="",
            tool_calls=[ToolCall("c", "read_file", {"path": "p" * 80})],
            usage={"total_tokens": 10},
        )


def test_cp4_auto_compact_triggers_inside_loop(tmp_path):
    fake = AutoCompactFake()
    config = Config(api_key="x", workdir=tmp_path, max_steps=8, max_tool_calls=20,
                    max_consecutive_failures=10, no_progress_limit=10,
                    auto_compact_at_tokens=50)
    agent = CodingAgent(config, llm=fake)
    agent.run("fix the bug in this repository")
    assert fake.seen_compacted
