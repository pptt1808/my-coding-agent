"""Contract tests for specs/safety.md — S1-S3 (S4 optional interaction deferred).

Written BEFORE the implementation: these should be RED now.
"""
from __future__ import annotations

import pytest

from tools import context
from tools.file_ops import read_file
from tools.shell import bash


@pytest.fixture(autouse=True)
def _isolated_context(tmp_path):
    context.configure(workdir=tmp_path, output_cap=8000, timeout=30)
    yield tmp_path
    context.configure(workdir=tmp_path, output_cap=8000, timeout=30)


def test_s1_dangerous_commands_blocked(_isolated_context):
    for cmd in ("rm -rf /", "git push --force origin main", "sudo rm -rf /"):
        out = bash(cmd)
        assert "blocked" in out.lower() or "Error" in out


def test_s2_path_escape_workdir_rejected(_isolated_context):
    out = read_file("../outside.txt")
    assert "escapes workdir" in out or "Error" in out


def test_s2_absolute_path_outside_rejected(_isolated_context):
    out = read_file(str(_isolated_context.parent / "other.txt"))
    assert "escapes workdir" in out or "Error" in out


def test_s3_blacklist_extensible(_isolated_context):
    context.configure(extra_blacklist=["my-dangerous-tool"])
    out = bash("my-dangerous-tool --go")
    assert "blocked" in out.lower() or "Error" in out
