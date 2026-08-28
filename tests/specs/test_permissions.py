"""Contract tests for specs/permissions.md — P1-P3.

Written BEFORE the implementation (spec-driven): RED now.
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult
from agent.repl import ReplSession
from tools import context


class FakeLLM:
    def complete(self, _sys, _messages, _tools=None):
        return LLMResult(text="ok", usage={"total_tokens": 1})


@pytest.fixture
def sess(tmp_path):
    return ReplSession(Config(api_key="x", workdir=tmp_path), llm=FakeLLM())


def test_p1_permissions_shows_workdir_and_blacklist(sess):
    text = "\n".join(sess.handle("/permissions"))
    assert "workdir" in text
    assert "blacklist" in text


def test_p2_block_adds_pattern(sess, tmp_path):
    from tools.shell import bash

    context.configure(workdir=tmp_path)
    sess.handle("/permissions block my-dangerous-cmd")
    out = bash("my-dangerous-cmd --go")
    assert "blocked" in out.lower()


def test_p3_reset_restores_default(sess, tmp_path):
    from tools.shell import bash

    context.configure(workdir=tmp_path)
    sess.handle("/permissions block my-dangerous-cmd")
    assert "blocked" in bash("my-dangerous-cmd --go").lower()
    sess.handle("/permissions reset")
    out = bash("my-dangerous-cmd --go")
    assert "blocked" not in out.lower()
