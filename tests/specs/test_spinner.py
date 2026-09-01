"""Unit tests for the Claude-Code-style status spinner (specs/cli.md R16)."""
from __future__ import annotations

import io
import time

from agent.spinner import StatusSpinner


def _collect():
    buf = io.StringIO()
    s = StatusSpinner(stream=buf)
    return s, buf


def test_spinner_shows_label_and_clears():
    s, buf = _collect()
    s.start("思考中")
    time.sleep(0.05)
    out = buf.getvalue()
    assert "思考中" in out            # the label is shown
    assert "\r" in out               # status line uses a carriage return
    s.clear()
    # clear() erases the line in the terminal via a carriage-return + erase-to-EOL;
    # the StringIO buffer keeps the prior text, so assert the erase was emitted.
    end = buf.getvalue()
    assert end.rstrip().endswith("\r\x1b[2K")  # last action is erase-to-EOL


def test_spinner_update_changes_label():
    s, buf = _collect()
    s.start("思考中")
    s.update("读取 report.py")
    time.sleep(0.02)
    assert "读取 report.py" in buf.getvalue()
    s.clear()


def test_spinner_matches_loop_contract():
    """The agent calls on_status('') to mean 'clear', non-empty to mean 'show'."""
    s, buf = _collect()
    s.update("执行 read_file")        # like a status callback
    assert "执行 read_file" in buf.getvalue()
    s.update("")                      # clear
    time.sleep(0.01)
    assert "\x1b[2K" in buf.getvalue()
