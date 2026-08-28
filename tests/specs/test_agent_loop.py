"""Contract tests for specs/agent-loop.md — L1-L5.

Uses a scripted FakeLLM (no network) injected into CodingAgent.
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.loop import CodingAgent, build_system_prompt
from agent.llm import LLMResult, ToolCall


class FakeLLM:
    """Plays back scripted LLMResult objects and records the messages it saw."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[tuple[str, list, list]] = []

    def complete(self, system_prompt, messages, tools):
        self.calls.append((system_prompt, list(messages), list(tools)))
        if not self.responses:
            return LLMResult(text="done")
        return self.responses.pop(0)


@pytest.fixture
def workdir(tmp_path):
    (tmp_path / "hello.txt").write_text("hello world", encoding="utf-8")
    return tmp_path


def _agent(workdir, fake, **cfg):
    from dataclasses import replace

    config = Config(api_key="x", workdir=workdir, max_steps=10, max_tool_calls=20,
                    max_consecutive_failures=5, no_progress_limit=5, max_elapsed_s=120)
    if cfg:
        config = replace(config, **cfg)
    return CodingAgent(config, llm=fake)


def _read_tool(path="hello.txt"):
    return ToolCall(id="c1", name="read_file", arguments={"path": path})


def test_l1_simple_answer_returned(workdir):
    fake = FakeLLM([LLMResult(text="final answer")])
    agent = _agent(workdir, fake)
    assert agent.run("do the thing") == "final answer"
    assert len(fake.calls) == 1


def test_l2_tool_result_fed_back(workdir):
    fake = FakeLLM([
        LLMResult(text="", tool_calls=[_read_tool()]),
        LLMResult(text="answer"),
    ])
    agent = _agent(workdir, fake)
    assert agent.run("read the file") == "answer"
    second_messages = fake.calls[1][1]
    contents = [str(m.get("content", "")) for m in second_messages]
    assert any("hello world" in c for c in contents)


def test_l3_stops_at_max_steps(workdir):
    infinite = [LLMResult(text="", tool_calls=[_read_tool()])] * 20
    fake = FakeLLM(infinite)
    agent = _agent(workdir, fake, max_steps=2)
    out = agent.run("loop forever")
    assert "Error" in out  # loop stopped without a final answer
    assert fake.calls[0]  # at least one model call happened


def test_l4_system_prompt_mentions_workdir(workdir):
    prompt = build_system_prompt(str(workdir))
    assert str(workdir) in prompt


def test_l4b_system_prompt_mentions_platform(workdir):
    """Gradient-test fix: the model must know the shell is Windows cmd."""
    prompt = build_system_prompt(str(workdir))
    assert "Windows" in prompt
    assert "heredoc" in prompt


def test_l5_tool_error_does_not_crash_loop(workdir):
    fake = FakeLLM([
        LLMResult(text="", tool_calls=[_read_tool("missing.txt")]),
        LLMResult(text="recovered"),
    ])
    agent = _agent(workdir, fake)
    assert agent.run("try missing file") == "recovered"
    second_messages = fake.calls[1][1]
    contents = [str(m.get("content", "")) for m in second_messages]
    assert any("Error" in c for c in contents)


def test_l6_exploring_different_files_is_not_no_progress(workdir):
    """Reading several different files must NOT look like no-progress (T5/P2 fix)."""
    fake = FakeLLM([
        LLMResult(text="", tool_calls=[_read_tool("hello.txt")]),
        LLMResult(text="", tool_calls=[ToolCall(id="c2", name="read_file", arguments={"path": "other.txt"})]),
        LLMResult(text="", tool_calls=[ToolCall(id="c3", name="read_file", arguments={"path": "third.txt"})]),
        LLMResult(text="answer"),
    ])
    agent = _agent(workdir, fake, no_progress_limit=2)
    assert agent.run("explore") == "answer"


def test_l7_identical_repeated_call_is_no_progress(workdir):
    """The SAME tool+arguments repeated should stop the loop (T5)."""
    same = [LLMResult(text="", tool_calls=[_read_tool("hello.txt")])] * 10
    fake = FakeLLM(same)
    agent = _agent(workdir, fake, no_progress_limit=2, max_steps=10)
    out = agent.run("repeat the same call")
    assert "Error" in out  # stopped by no-progress before finishing
