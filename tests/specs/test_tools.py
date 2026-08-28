"""Contract tests for specs/tools.md — read_file A1-A3, write_file B1-B2, bash C1-C4,
and the T1 tool set: list_dir L1-L3, glob G1-G3, grep GR1-GR4, append_file AP1-AP2,
edit_file ED1-ED5.

Written BEFORE the implementation (spec-driven): the T1 tests should be RED now.
"""
from __future__ import annotations

import pytest

from tools import context
from tools.file_ops import append_file, edit_file, glob, grep, list_dir, read_file, write_file
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


def test_a3b_tail_preserved_on_truncation(_isolated_context):
    long = "x" * 300 + "THE_END"
    path = _isolated_context / "long.txt"
    path.write_text(long, encoding="utf-8")
    context.configure(output_cap=50)
    out = read_file(str(path))
    assert "THE_END" in out  # tail-first: key info at the end survives


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


def test_c4b_bash_tail_preserved(_isolated_context):
    script = _isolated_context / "big_print.py"
    script.write_text('print("line" * 200)\nprint("FINAL_RESULT_OK")\n', encoding="utf-8")
    context.configure(output_cap=100)
    out = bash(f"python big_print.py", timeout=30)
    assert "FINAL_RESULT_OK" in out  # tail-first truncation keeps the end


def test_c5_bash_schema_mentions_windows_env():
    """Gradient-test fix: the model must be told it runs on Windows cmd."""
    from tools.schemas import BASH

    desc = BASH["function"]["description"]
    assert "Windows" in desc
    assert "heredoc" in desc
    assert "python -c" in desc


# ---- list_dir: L1/L2/L3 ----
def test_l1_list_dir_entries(_isolated_context):
    (_isolated_context / "a.py").write_text("x", encoding="utf-8")
    (_isolated_context / "sub").mkdir()
    out = list_dir(".")
    assert "a.py" in out
    assert "sub/" in out


def test_l2_list_dir_missing_returns_error(_isolated_context):
    out = list_dir("no_such_dir")
    assert "Error" in out


def test_l3_list_dir_escape_rejected(_isolated_context):
    out = list_dir("..")
    assert "escapes workdir" in out or "Error" in out


# ---- glob: G1/G2/G3 ----
def test_g1_glob_matches(_isolated_context):
    (_isolated_context / "a.py").write_text("x", encoding="utf-8")
    (_isolated_context / "b.txt").write_text("y", encoding="utf-8")
    out = glob("*.py")
    assert "a.py" in out
    assert "b.txt" not in out


def test_g2_glob_no_match(_isolated_context):
    assert glob("*.rs") == "(no matches)"


def test_g3_glob_escape_rejected(_isolated_context):
    out = glob("../*.py")
    assert "Error" in out


# ---- grep: GR1/GR2/GR3/GR4 ----
def test_gr1_grep_returns_path_line_content(_isolated_context):
    (_isolated_context / "a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    out = grep("def foo")
    assert "a.py:1: def foo():" in out


def test_gr2_grep_no_match(_isolated_context):
    (_isolated_context / "a.py").write_text("nothing here", encoding="utf-8")
    assert grep("zzz") == "(no matches)"


def test_gr3_grep_bad_regex_returns_error(_isolated_context):
    out = grep("[unclosed")
    assert "Error" in out


def test_gr4_grep_restricted_to_workdir(_isolated_context):
    out = grep("x", path="..")
    assert "escapes workdir" in out or "Error" in out


# ---- append_file: AP1/AP2 ----
def test_ap1_append_keeps_existing(_isolated_context):
    p = _isolated_context / "log.txt"
    p.write_text("line1\n", encoding="utf-8")
    append_file("log.txt", "line2\n")
    assert p.read_text(encoding="utf-8") == "line1\nline2\n"


def test_ap2_append_creates_file(_isolated_context):
    append_file("new.txt", "hello")
    assert (_isolated_context / "new.txt").read_text(encoding="utf-8") == "hello"


# ---- edit_file: ED1-ED5 ----
def test_ed1_edit_first_occurrence_only(_isolated_context):
    p = _isolated_context / "t.txt"
    p.write_text("a b a\n", encoding="utf-8")
    edit_file("t.txt", "a", "X")
    assert p.read_text(encoding="utf-8") == "X b a\n"


def test_ed2_edit_missing_old_returns_error(_isolated_context):
    (_isolated_context / "t.txt").write_text("abc", encoding="utf-8")
    out = edit_file("t.txt", "zzz", "X")
    assert "Error" in out


def test_ed3_edit_replace_all(_isolated_context):
    p = _isolated_context / "t.txt"
    p.write_text("a b a\n", encoding="utf-8")
    edit_file("t.txt", "a", "X", replace_all=True)
    assert p.read_text(encoding="utf-8") == "X b X\n"


def test_ed4_edit_keeps_rest(_isolated_context):
    p = _isolated_context / "t.txt"
    p.write_text("def add(a, b):\n    return a + b  # BUG\n", encoding="utf-8")
    edit_file("t.txt", "a + b", "a - b")
    assert p.read_text(encoding="utf-8") == "def add(a, b):\n    return a - b  # BUG\n"


def test_ed5_edit_escape_rejected(_isolated_context):
    out = edit_file("../outside.txt", "a", "b")
    assert "escapes workdir" in out or "Error" in out
