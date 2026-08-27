"""Contract tests for specs/termination.md — T1-T6.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

from agent.config import Config
from agent.termination import LoopState, Terminator


def _config(**overrides) -> Config:
    base = dict(api_key="x", max_steps=3, max_tool_calls=5,
                max_consecutive_failures=2, no_progress_limit=2, max_elapsed_s=60)
    base.update(overrides)
    return Config(**base)


def test_t1_done_stops():
    t = Terminator(_config())
    assert t.should_stop(LoopState(done=True), 0.0)


def test_t2_max_steps_stops():
    t = Terminator(_config(max_steps=3))
    assert t.should_stop(LoopState(steps=3), 0.0)
    assert not t.should_stop(LoopState(steps=2), 0.0)


def test_t3_max_tool_calls_stops():
    t = Terminator(_config(max_tool_calls=5))
    assert t.should_stop(LoopState(tool_calls=5), 0.0)


def test_t4_consecutive_failures_stops():
    t = Terminator(_config(max_consecutive_failures=2))
    assert t.should_stop(LoopState(consecutive_failures=2), 0.0)


def test_t5_no_progress_stops():
    t = Terminator(_config(no_progress_limit=2))
    assert t.should_stop(LoopState(no_progress_count=2), 0.0)


def test_t6_timeout_stops():
    t = Terminator(_config(max_elapsed_s=60))
    assert t.should_stop(LoopState(), 61.0)
    assert not t.should_stop(LoopState(), 59.0)
