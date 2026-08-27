"""Contract tests for specs/context.md — CT1-CT5.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

from agent.history import History


def test_ct1_append_preserves_order():
    h = History()
    h.append({"role": "user", "content": "a"})
    h.append({"role": "assistant", "content": "b"})
    assert [m["content"] for m in h.as_list()] == ["a", "b"]


def test_ct2_long_output_truncated_with_marker():
    h = History()
    long = "y" * 300
    out = h.truncate_large_output(long, cap=100)
    assert len(out) < 300
    assert "truncated" in out


def test_ct3_short_output_unchanged():
    h = History()
    assert h.truncate_large_output("short", cap=100) == "short"


def test_ct4_as_list_returns_copy():
    h = History()
    h.append({"role": "user", "content": "x"})
    snapshot = h.as_list()
    snapshot.append({"role": "user", "content": "mutated"})
    assert len(h.as_list()) == 1


def test_ct5_summarize_oldest_keeps_below_token_limit():
    h = History(max_tokens=50)
    big = "word " * 500  # ~2000 chars -> ~500 tokens
    h.append({"role": "user", "content": big})
    h.append({"role": "assistant", "content": big})
    h.summarize_oldest()
    total = sum(len(str(m.get("content", ""))) // 4 for m in h.as_list())
    assert total <= 50
