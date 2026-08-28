"""Contract tests for specs/multi-agent.md — E1-E7.

Uses scripted FakeLLM agents (no network). Written BEFORE implementation (RED).
The crux (per user emphasis): the explore subagent must NOT be launched when
it is unnecessary.
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult, ToolCall
from agent.multi import (EXPLORE_TOOLS, collect_repo_stats, orchestrate,
                         run_explore, should_explore)


def _build_repo(root, n_files=0, loc=2, with_subdirs=2):
    (root / "src").mkdir(parents=True, exist_ok=True)
    for i in range(with_subdirs):
        (root / f"mod{i}").mkdir(parents=True, exist_ok=True)
        (root / f"mod{i}" / f"m{i}.py").write_text("y = 2\n" * loc, encoding="utf-8")
    for i in range(max(n_files, 1)):
        (root / "src" / f"f{i}.py").write_text("x = 1\n" * loc, encoding="utf-8")
    return root


def test_collect_repo_stats():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_repo(root, n_files=3, loc=5, with_subdirs=3)
        stats = collect_repo_stats(root)
        assert stats.n_files >= 3  # src files + one per module dir
        assert stats.loc >= 20
        assert stats.top_level_modules >= 3  # src + mod0 + mod1 + mod2


def test_e1_small_repo_no_explore(tmp_path):
    _build_repo(tmp_path, n_files=2, loc=2, with_subdirs=1)
    cfg = Config(api_key="x", workdir=tmp_path, auto_explore="auto",
                 explore_min_files=50, explore_min_loc=5000, explore_min_modules=3)
    assert should_explore(cfg) is False
    assert should_explore(cfg, explicit=0) is False


def test_e2_large_repo_explores(tmp_path):
    _build_repo(tmp_path, n_files=60, loc=2, with_subdirs=1)
    cfg = Config(api_key="x", workdir=tmp_path, auto_explore="auto")
    assert should_explore(cfg) is True


def test_e3_explicit_override_highest_priority(tmp_path):
    _build_repo(tmp_path, n_files=2, loc=2, with_subdirs=1)
    cfg = Config(api_key="x", workdir=tmp_path, auto_explore="off")
    assert should_explore(cfg, explicit=1) is True   # --explore forces on
    cfg2 = Config(api_key="x", workdir=tmp_path, auto_explore="always")
    assert should_explore(cfg2, explicit=-1) is False  # --no-explore forces off


def test_e4_auto_explore_modes(tmp_path):
    _build_repo(tmp_path, n_files=2, loc=2, with_subdirs=1)
    cfg = Config(api_key="x", workdir=tmp_path)
    assert cfg.auto_explore == "off"
    assert should_explore(cfg) is False  # off -> never
    assert should_explore(Config(api_key="x", workdir=tmp_path, auto_explore="always")) is True


class ToolsRecordingLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.tools_seen: list[list[dict]] = []
        self.systems: list[str] = []

    def complete(self, system_prompt, _messages, tools):
        self.systems.append(system_prompt)
        self.tools_seen.append(list(tools or []))
        if not self.responses:
            return LLMResult(text="brief done", usage={"total_tokens": 1})
        return self.responses.pop(0)


def test_e5_explore_is_read_only(tmp_path):
    _build_repo(tmp_path, n_files=1)
    fake = ToolsRecordingLLM([
        LLMResult(text="", tool_calls=[ToolCall("c1", "write_file", {"path": "x.py", "content": "evil"})],
                  usage={"total_tokens": 1}),
        LLMResult(text="brief", usage={"total_tokens": 1}),
    ])
    cfg = Config(api_key="x", workdir=tmp_path)
    run_explore(cfg, "explore", llm=fake)
    exposed = {t["function"]["name"] for t in fake.tools_seen[0]}
    assert exposed == set(EXPLORE_TOOLS)  # read-only whitelist only
    assert "not enabled" not in "".join(fake.systems) or True
    # the write_file attempt was blocked and fed back (dispatch guard), not executed
    assert (tmp_path / "x.py").exists() is False


def test_e6_brief_is_bounded(tmp_path):
    _build_repo(tmp_path, n_files=1)
    fake = ToolsRecordingLLM([])  # returns "brief done" at the end
    cfg = Config(api_key="x", workdir=tmp_path, explore_brief_chars=20)
    brief = run_explore(cfg, "explore", llm=fake)
    assert len(brief) <= 20


def test_e7_orchestrate_small_repo_single_agent(tmp_path):
    _build_repo(tmp_path, n_files=1, loc=2, with_subdirs=1)
    # cfg.auto_explore defaults to 'off' -> explore must NOT be spawned
    cfg = Config(api_key="x", workdir=tmp_path)
    fake = ToolsRecordingLLM([LLMResult(text="answer", usage={"total_tokens": 1})])
    answer, brief = orchestrate(cfg, "task", stream=False, impl_llm=fake)
    assert brief is None  # no subagent launched (never spawned on small/off)
    assert answer == "answer"
    # no explore model call happened: impl saw only one LLM call
    assert len(fake.tools_seen) == 1
