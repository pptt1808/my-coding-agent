"""Contract tests for specs/agentmd.md — M1-M4."""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult
from agent.pm import PmSession


class RecordingLLM:
    def __init__(self):
        self.system = None

    def complete(self, system_prompt, _messages, _tools=None):
        self.system = system_prompt
        return LLMResult(text="ok", usage={"total_tokens": 1})


def test_m1_agent_md_injected(tmp_path):
    (tmp_path / "AGENT.md").write_text("Use tabs, type hints, and `ruff` linting.\n", encoding="utf-8")
    fake = RecordingLLM()
    from agent.loop import CodingAgent
    CodingAgent(Config(api_key="x", workdir=tmp_path), llm=fake).run("hi")
    assert "PROJECT CONVENTIONS (AGENT.md" in fake.system
    assert "Use tabs" in fake.system


def test_m2_no_agent_md_no_block(tmp_path):
    fake = RecordingLLM()
    from agent.loop import CodingAgent
    CodingAgent(Config(api_key="x", workdir=tmp_path), llm=fake).run("hi")
    assert "PROJECT CONVENTIONS" not in fake.system


def test_m3_agent_md_truncated(tmp_path):
    (tmp_path / "AGENT.md").write_text("x" * 5000, encoding="utf-8")
    fake = RecordingLLM()
    from agent.loop import CodingAgent
    CodingAgent(Config(api_key="x", workdir=tmp_path, agent_md_chars=500), llm=fake).run("hi")
    # the conventions block is present and capped
    i = fake.system.find("PROJECT CONVENTIONS")
    assert i != -1
    assert len(fake.system) - i < 500 + 80  # roughly capped


def test_m4_pm_profile_injected(tmp_path):
    (tmp_path / "PM_PROFILE.md").write_text("Prefer a 30-second story; audience = busy PMs.\n", encoding="utf-8")
    fake = RecordingLLM()
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=fake)
    # persona is set as the agent's system prompt override; run a turn to capture it
    sess.turn("describe idea")
    assert "USER PM PROFILE" in fake.system
    assert "busy PMs" in fake.system
