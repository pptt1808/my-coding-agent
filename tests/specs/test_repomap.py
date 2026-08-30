"""Contract tests for specs/repomap.md — R1-R5.

Uses real files (no network). The repo map is built from the filesystem.
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult
from agent.repomap import build_repo_map, code_map


def _repo(root):
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "app.py").write_text(
        "class Service(Base):\n    def do(self, x, y=1):\n        return x\n\n"
        "def helper(a, b):\n    return a\n", encoding="utf-8")
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / ".venv" / "lib").mkdir(parents=True, exist_ok=True)
    (root / ".venv" / "lib" / "ignored.py").write_text("def nope():\n    pass\n", encoding="utf-8")
    (root / "demo").mkdir(parents=True, exist_ok=True)
    (root / "demo" / "x.py").write_text("def demo_func():\n    pass\n", encoding="utf-8")
    return root


def test_r1_extracts_symbols_with_signatures(tmp_path):
    _repo(tmp_path)
    m = build_repo_map(tmp_path)
    assert "class Service(Base)" in m
    assert "def do(self, x, y)" in m  # params are listed (compact names)
    assert "def helper(a, b)" in m


def test_r3_skips_noise_dirs_and_non_py(tmp_path):
    _repo(tmp_path)
    m = build_repo_map(tmp_path)
    assert "ignored.py" not in m  # .venv skipped
    assert "demo_func" not in m   # demo/ skipped
    (tmp_path / "src" / "note.txt").write_text("x", encoding="utf-8")
    assert "note.txt" not in m    # non-.py not in symbol table


def test_r2_truncated_over_max_chars(tmp_path):
    _repo(tmp_path)
    long = "".join(f"def f{i}(a):\n    return a\n" for i in range(200))
    (tmp_path / "src" / "big.py").write_text(long, encoding="utf-8")
    m = build_repo_map(tmp_path, max_chars=200)
    assert "truncated" in m
    assert len(m) > 200  # cap + marker extends slightly past the budget


def test_r4_code_map_cached(tmp_path):
    _repo(tmp_path)
    a = code_map(tmp_path, max_chars=4000)
    b = code_map(tmp_path, max_chars=4000)
    assert a == b  # cached; identical content
    # fingerprint cache file written under .coding-agent
    cache = tmp_path / ".coding-agent" / "repomap.txt"
    assert cache.exists()


def test_r5_injected_into_system_prompt(tmp_path):
    _repo(tmp_path)
    class RecordingLLM:
        def __init__(self):
            self.system = None
        def complete(self, system_prompt, _messages, _tools=None):
            self.system = system_prompt
            return LLMResult(text="ok", usage={"total_tokens": 1})
    fake = RecordingLLM()
    from agent.loop import CodingAgent
    agent = CodingAgent(Config(api_key="x", workdir=tmp_path), llm=fake)
    agent.run("hi")
    assert "CODE MAP" in fake.system
    assert "class Service(Base)" in fake.system
