"""Contract tests for specs/parser.md — P1-P4.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

from agent.llm import LLMResult, ToolCall
from agent.parser import parse_tool_call_from_text, parse_tool_calls


def _tool(name="read_file", args=None):
    return ToolCall(id="call_1", name=name, arguments=args or {"path": "a.py"})


# ---- P1: native structured path passes through ----
def test_p1_native_tool_calls_passthrough():
    calls = [_tool(), _tool("bash", {"command": "ls"})]
    result = LLMResult(text="", tool_calls=calls)
    assert parse_tool_calls(result) == calls


# ---- P2: text fallback parses a tool block ----
def test_p2_text_fallback_tool_block():
    text = 'Some thinking... <tool name="read_file">{"path": "a.py"}</tool>'
    tc = parse_tool_call_from_text(text)
    assert tc is not None
    assert tc.name == "read_file"
    assert tc.arguments == {"path": "a.py"}


# ---- P3: unparseable text -> None (no crash) ----
def test_p3_unparseable_text_returns_none():
    assert parse_tool_call_from_text("just a normal answer, no tool here") is None
    assert parse_tool_call_from_text('<tool name="x">{bad json}</tool>') is None


# ---- P4: parsed arguments keep native types ----
def test_p4_arguments_have_native_types():
    text = '<tool name="bash">{"command": "ls -la", "timeout": 5}</tool>'
    tc = parse_tool_call_from_text(text)
    assert tc.arguments["timeout"] == 5
    assert tc.arguments["command"] == "ls -la"
