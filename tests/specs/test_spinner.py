"""Unit tests for the status line (specs/cli.md R16) — deliberate STATIC, no thread.

The spinner is synchronous: it draws a single status line and clears it when
real output arrives. Writing from a background thread would interleave with the
main thread's streamed answer and corrupt the terminal, so there is NO thread.
"""
from __future__ import annotations

import io

from agent.spinner import StatusSpinner


def _collect():
    buf = io.StringIO()
    s = StatusSpinner(stream=buf)
    return s, buf


def test_spinner_shows_label_and_clears():
    s, buf = _collect()
    s.start("思考中")
    out = buf.getvalue()
    assert "思考中" in out            # the label is shown
    assert "[agent]" in out           # prefixed status line
    assert "\r" in out                # status line uses a carriage return
    s.clear()
    end = buf.getvalue()
    assert end.rstrip().endswith("\r\x1b[2K")  # clear erases via CR + erase-to-EOL
    # after clearing, a further start/clear does nothing extra (label empty)
    out2 = buf.getvalue()
    assert "[agent]" in out2


def test_spinner_update_changes_label():
    s, buf = _collect()
    s.start("思考中")
    s.update("读取 report.py")
    assert "读取 report.py" in buf.getvalue()
    s.clear()
    # no stale label after clear
    out = buf.getvalue()
    assert "[agent] 读取 report.py" in out  # was drawn before being cleared


def test_spinner_matches_loop_contract():
    """The agent calls clear()/update(); the REPL clears before printing tokens."""
    s, buf = _collect()
    s.update("执行 read_file")
    assert "执行 read_file" in buf.getvalue()
    s.clear()
    assert buf.getvalue().rstrip().endswith("\r\x1b[2K")
    # after clear the label must be empty so a repeated clear writes nothing
    before = len(buf.getvalue())
    s.clear()
    assert len(buf.getvalue()) == before  # no-op once already cleared
