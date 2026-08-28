"""Contract tests for specs/session.md — S1-S4.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

import pytest

from agent.session import list_sessions, load_session, new_session_id, save_session, Session


def test_s1_roundtrip(tmp_path):
    s = Session(id="abc", model="deepseek-v4-flash", workdir=str(tmp_path),
                messages=[{"role": "user", "content": "hi"}], steps=3, total_tokens=42)
    save_session(s, tmp_path)
    loaded = load_session(tmp_path, "abc")
    assert loaded.id == "abc"
    assert loaded.model == "deepseek-v4-flash"
    assert loaded.messages == [{"role": "user", "content": "hi"}]
    assert loaded.steps == 3
    assert loaded.total_tokens == 42


def test_s2_list_sessions_newest_first_and_skips_bad(tmp_path):
    import os
    import time

    a = Session(id="a", model="m", workdir=str(tmp_path), messages=[{"role": "user", "content": "1"}])
    b = Session(id="b", model="m", workdir=str(tmp_path), messages=[{"role": "user", "content": "2"}])
    save_session(a, tmp_path)
    save_session(b, tmp_path)
    # control mtimes so ordering is deterministic (newest = a)
    base = time.time()
    os.utime(tmp_path / ".coding-agent" / "sessions" / "b.json", (base, base + 1))
    os.utime(tmp_path / ".coding-agent" / "sessions" / "a.json", (base, base + 2))
    (tmp_path / ".coding-agent" / "sessions" / "bad.json").write_text("{not json", encoding="utf-8")
    ids = [s.id for s in list_sessions(tmp_path)]
    assert ids == ["a", "b"]


def test_s3_missing_session_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_session(tmp_path, "nope")


def test_s4_new_session_id_unique():
    assert new_session_id() != new_session_id()
