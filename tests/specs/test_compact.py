"""Contract tests for specs/compact.md — CP1-CP3.

Uses a scripted FakeLLM (no network). Written BEFORE implementation (RED).
"""
from __future__ import annotations

import pytest

from agent.compact import summarize_conversation
from agent.config import Config
from agent.llm import LLMResult
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
