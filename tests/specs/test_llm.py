"""Contract tests for the LLM client mapping (N1) — LL1-LL4.

These verify LLMClient maps a raw OpenAI-compatible response into LLMResult
(ToolCall list + usage). No network: a fake OpenAI client is injected.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agent.config import Config
from agent.llm import LLMClient, LLMResult, ToolCall


class FakeOpenAI:
    """Minimal fake of the openai client's chat.completions surface."""

    def __init__(self, api_key, base_url, messages_response):
        self._api_key = api_key
        self._base_url = base_url
        self._response = messages_response
        self.calls = []

    @property
    def chat(self):
        return SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def _resp(content=None, tool_calls=None, usage=None):
    message = {"role": "assistant", "content": content, "tool_calls": tool_calls}
    choice = SimpleNamespace(message=SimpleNamespace(**message))
    return SimpleNamespace(choices=[choice], usage=SimpleNamespace(**usage) if usage else None)


def _make_client(resp):
    cfg = Config(api_key="sk-test", base_url="https://gateway.test/v1")
    fake = FakeOpenAI("sk-test", "https://gateway.test/v1", resp)
    client = LLMClient(cfg, client=fake)
    return client, fake


def _tool_call(tc_id, name, arguments):
    return SimpleNamespace(
        id=tc_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_ll1_tool_call_mapped_into_toolcall():
    tc = _tool_call("call_9", "read_file", json.dumps({"path": "a.py"}))
    client, _ = _make_client(_resp(content="", tool_calls=[tc], usage={"total_tokens": 12}))
    result = client.complete("sys", [{"role": "user", "content": "hi"}], tools=[])
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments == {"path": "a.py"}
    assert result.tool_calls[0].id == "call_9"


def test_ll2_content_only_no_tool_calls():
    client, _ = _make_client(_resp(content="final answer", usage={"total_tokens": 3}))
    result = client.complete("sys", [], tools=[])
    assert result.text == "final answer"
    assert result.tool_calls == []


def test_ll3_usage_recorded():
    client, _ = _make_client(_resp(content="ok", usage={"total_tokens": 42, "prompt_tokens": 10}))
    result = client.complete("sys", [], tools=[])
    assert result.usage["total_tokens"] == 42


def test_ll4_passes_system_messages_and_tools():
    tools = [{"type": "function", "function": {"name": "bash"}}]
    client, fake = _make_client(_resp(content="ok"))
    client.complete("the-system", [{"role": "user", "content": "task"}], tools=tools)
    kwargs = fake.calls[0]
    assert kwargs["messages"][0] == {"role": "system", "content": "the-system"}
    assert kwargs["messages"][1:] == [{"role": "user", "content": "task"}]
    assert kwargs["tools"] == tools
    assert kwargs["model"] == "gpt-4o-mini"
