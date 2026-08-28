"""Contract tests for --tools filtering (E1/P2) — TF1-TF3.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult, ToolCall
from agent.loop import CodingAgent


class RecordingLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.tools_seen: list[list[dict]] = []
        self.messages_seen: list[list[dict]] = []

    def complete(self, _sys, messages, tools):
        self.tools_seen.append(list(tools or []))
        self.messages_seen.append(list(messages))
        if not self.responses:
            return LLMResult(text="done", usage={"total_tokens": 1})
        return self.responses.pop(0)


def test_tf1_tools_filter_limits_exposed_schemas(tmp_path):
    fake = RecordingLLM([LLMResult(text="answer", usage={"total_tokens": 1})])
    agent = CodingAgent(Config(api_key="x", workdir=tmp_path), llm=fake, tools=["read_file", "edit_file"])
    agent.run("hello")
    names = [t["function"]["name"] for t in fake.tools_seen[0]]
    assert set(names) == {"read_file", "edit_file"}


def test_tf2_unexposed_tool_blocked(tmp_path):
    fake = RecordingLLM([
        LLMResult(text="", tool_calls=[ToolCall("c1", "bash", {"command": "echo hi"})],
                  usage={"total_tokens": 1}),
        LLMResult(text="done", usage={"total_tokens": 1}),
    ])
    agent = CodingAgent(Config(api_key="x", workdir=tmp_path), llm=fake, tools=["read_file"])
    out = agent.run("do it")
    assert out == "done"
    # the blocked call must have been fed back as an error, not executed
    fed_back = "\n".join(str(m.get("content", "")) for m in fake.messages_seen[1])
    assert "not enabled" in fed_back


def test_tf3_no_filter_exposes_all(tmp_path):
    fake = RecordingLLM([LLMResult(text="answer", usage={"total_tokens": 1})])
    agent = CodingAgent(Config(api_key="x", workdir=tmp_path), llm=fake)
    agent.run("hello")
    names = {t["function"]["name"] for t in fake.tools_seen[0]}
    assert "bash" in names and "grep" in names
