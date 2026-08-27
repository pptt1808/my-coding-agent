"""Contract tests for specs/errors.md — E1-E4.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

import pytest

from agent.errors import AgentError, ModelOutputError, TimeoutError, ToolError
from tools.registry import dispatch, register


def test_e1_tool_error_carries_message():
    err = ToolError("boom")
    assert err.message == "boom"
    assert isinstance(err, AgentError)


def test_e2_model_output_error_raised_for_bad_output():
    err = ModelOutputError("cannot parse")
    assert isinstance(err, AgentError)


def test_e3_timeout_error_raised_on_timeout():
    err = TimeoutError("took too long")
    assert isinstance(err, AgentError)


def test_e4_dispatch_catches_tool_exception():
    def boom(**kwargs):  # noqa: ARG001
        raise RuntimeError("kaboom")

    register("boom_tool", {"type": "function", "function": {"name": "boom_tool"}}, boom)
    out = dispatch("boom_tool", {})
    assert out.startswith("Error")
    assert "kaboom" in out
