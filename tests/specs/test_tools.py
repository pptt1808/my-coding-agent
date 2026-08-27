"""Contract tests for specs/tools.md — read_file A1-A3, write_file B1-B2, bash C1-C4.

Written BEFORE the implementation (spec-driven): these should be RED now.
"""
from __future__ import annotations

import pytest

from tools import context
from tools.file_ops import read_file, write_file
from tools.shell import bash


@pytest.fixture(autouse=True)
def _isolated_context(tmp_path):
    """Point the tools context at an isolated temp workdir and reset caps."""
    context.configure(workdir=tmp_path, output_cap=8000, timeout=30)
    yield tmp_path
    context.configure(workdir=tmp_path, output_cap=8000, timeout=30)


# ---- read_file: A1/A2/A3 ----
def test_a1_read_existing_file(_isolated_context):
    path = _isolated_context / "hello.txt"
    path.write_text("hello world", encoding="utf-8")
    assert read_file(str(path)) == "hello world"


def test_a2_read_missing_file_returns_error_not_crash(_isolated_context):
    out = read_file(str(_isolated_context / "nope.txt"))
    assert out.startswith("Error")
    assert "nope.txt" in out


def test_a3_long_file_is_truncated(_isolated_context):
    long = "x" * 500
    path = _isolated_context / "long.txt"
    path.write_text(long, encoding="utf-8")
    context.configure(output_cap=100)
    out = read_file(str(path))
    assert len(out) < len(long)
    assert "truncated" in out


# ---- write_file: B1/B2 ----
def test_b1_write_then_read(_isolated_context):
    path = _isolated_context / "out.py"
    write_file(str(path), "print(1)\n")
    assert (path.read_text(encoding="utf-8")) == "print(1)\n"


def test_b2_write_returns_confirmation(_isolated_context):
    out = write_file(str(_isolated_context / "a.txt"), "hi")
    assert out and not out.startswith("Error")


# ---- bash: C1-C4 ----
def test_c1_bash_normal_output(_isolated_context):
    out = bash("echo hello-bash")
    assert "hello-bash" in out


def test_c2_bash_failure_returns_error_text(_isolated_context):
    out = bash('python -c "raise SystemExit(3)"')
    assert "exit code" in out or "Error" in out


def test_c3_bash_timeout_is_caught(_isolated_context):
    out = bash('python -c "import time; time.sleep(10)"', timeout=1)
    assert "timed out" in out.lower() or "timeout" in out.lower()


def test_c4_dangerous_command_blocked(_isolated_context):
    out = bash("rm -rf /")
    assert "blocked" in out.lower() or "Error" in out
