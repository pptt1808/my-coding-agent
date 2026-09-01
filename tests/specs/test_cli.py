"""Contract tests for the CLI interactive line reader (specs/cli.md R12/R15).

The Windows TTY path reads raw keys; we inject a fake reader and fake
isatty so it is testable without a real console.
"""
from __future__ import annotations

import sys

import pytest

from agent import cli


@pytest.fixture
def tty(monkeypatch):
    """Pretend stdin is an interactive Windows console."""
    monkeypatch.setattr("os.name", "nt")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    # Deterministic: no pending buffered input, so a '\r' is a real Enter/submit.
    monkeypatch.setattr("msvcrt.kbhit", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)


def _reader(chars):
    it = iter(chars)

    def read():
        try:
            return next(it)
        except StopIteration:
            return "\r"  # default to Enter at end
    return read


def _burst_pending(chars):
    """Simulate a paste burst: has_pending() is True while more chars are still
    queued (mid-paste), and False once the final Enter is reached."""
    state = {"i": 0}

    def read():
        if state["i"] >= len(chars):
            return "\r"  # buffer empty -> a real Enter, so this submits
        ch = chars[state["i"]]
        state["i"] += 1
        return ch

    def pending():
        # True while the cursor is not yet past the last delivered paste char
        return state["i"] < len(chars)

    return read, pending


def test_r15_slash_first_char_opens_menu_without_enter(tty, capsys):
    seen = []
    # '/' as first char -> menu; then type 'status' + Enter
    def _on_slash():
        seen.append("MENU")
        print("MENU")

    line = cli.read_interactive_line("❯ ", on_slash=_on_slash,
                                     _read_char=_reader(["/", "s", "t", "a", "t", "u", "s", "\r"]))
    assert seen == ["MENU"]  # menu opened immediately on '/'
    assert line == "/status"  # leading '/' re-added, rest typed normally
    assert "MENU" in capsys.readouterr().out


def test_r15e_slash_menu_then_full_command_no_double_slash(tty, capsys):
    """Regression: '/' opens the menu, then the user types the FULL command with
    its own leading '/' (the common `/pm` case). Must NOT produce '//pm'."""
    seen = []
    def _on_slash():
        seen.append("MENU")
        print("MENU")
    line = cli.read_interactive_line("❯ ", on_slash=_on_slash,
                                     _read_char=_reader(["/", "/", "p", "m", "\r"]))
    assert seen == ["MENU"]          # menu still opened on first '/'
    assert line == "/pm"             # exactly one leading slash, not "//pm"


def test_r15f_slash_menu_then_suffix_no_extra_slash(tty, capsys):
    """After the menu, typing only the suffix (no extra '/') still auto-prepends."""
    seen = []
    def _on_slash():
        seen.append("MENU")
        print("MENU")
    line = cli.read_interactive_line("❯ ", on_slash=_on_slash,
                                     _read_char=_reader(["/", "p", "m", "\r"]))
    assert seen == ["MENU"]
    assert line == "/pm"


def test_r15b_normal_line_no_menu(tty, capsys):
    seen = []
    line = cli.read_interactive_line("❯ ", on_slash=lambda: seen.append("MENU"),
                                     _read_char=_reader(["h", "i", "\r"]))
    assert seen == []  # '/' was not the first char
    assert line == "hi"


def test_r15c_backspace_works(tty):
    line = cli.read_interactive_line("❯ ", on_slash=lambda: None,
                                     _read_char=_reader(["a", "b", "\x08", "c", "\r"]))
    assert line == "ac"  # backspace removed 'b'


def test_r15d_non_tty_uses_input(monkeypatch, capsys):
    """Non-TTY falls back to input() (Enter-based), no msvcrt path."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "task")
    assert cli.read_interactive_line("❯ ", on_slash=lambda: None) == "task"


def test_r15g_erase_on_enter_normal_turn(tty, capsys):
    """Regression: with erase_on_enter, a NORMAL turn erases the echoed prompt
    line so the bubble re-renders it in-place (shown once, not duplicated)."""
    line = cli.read_interactive_line("❯ ", on_slash=lambda: None,
                                     _read_char=_reader(["h", "i", "\r"]),
                                     erase_on_enter=True)
    assert line == "hi"
    # the echoed line was cleared (no trailing \n), not advanced to a new line
    out = capsys.readouterr().out
    assert "\x1b[2K" in out
    assert not out.endswith("\n")  # cursor stays on the same line for the bubble


def test_r15h_erase_on_enter_command_not_erased(tty, capsys):
    """Slash commands keep the normal newline (the bubble only wraps non-commands)."""
    line = cli.read_interactive_line("❯ ", on_slash=lambda: None,
                                     _read_char=_reader(["/", "h", "e", "l", "p", "\r"]),
                                     erase_on_enter=True)
    assert line == "/help"
    out = capsys.readouterr().out
    assert "\x1b[2K" not in out  # command echo is NOT erased
    assert out.endswith("\n")    # advanced to a new line


def test_r15i_paste_lf_multiline_is_one_input(tty):
    """Regression: pasting a multi-line doc (LF line endings, e.g. from TASK.md)
    must be collected as ONE submission, not one line per newline."""
    read, pending = _burst_pending(["t", "a", "s", "k", "\n", "l", "i", "n", "e", "2", "\r"])
    line = cli.read_interactive_line("❯ ", on_slash=lambda: None,
                                     _read_char=read, _has_pending=pending)
    assert line == "task\nline2"  # a single input with an embedded newline


def test_r15j_paste_crlf_multiline_is_one_input(tty):
    """Regression: Windows clipboards paste '\r\n' line endings; those must also
    collapse to ONE submission with a single '\n' per line break."""
    read, pending = _burst_pending(["a", "b", "c", "\r", "\n", "d", "e", "f", "\r"])
    line = cli.read_interactive_line("❯ ", on_slash=lambda: None,
                                     _read_char=read, _has_pending=pending)
    assert line == "abc\ndef"  # '\r\n' became a single '\n'


def test_r15k_lone_lf_never_submits_then_enter_submits(tty):
    """A bare '\n' (no following '\r') is collected as part of the input, and the
    input is only submitted when a real Enter arrives (buffer empty)."""
    read, pending = _burst_pending(["x", "y", "\n", "\r"])
    line = cli.read_interactive_line("❯ ", on_slash=lambda: None,
                                     _read_char=read, _has_pending=pending)
    assert line == "xy\n"  # '\n' was kept; the final '\r' submitted
