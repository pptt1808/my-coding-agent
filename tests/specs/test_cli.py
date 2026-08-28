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
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)


def _reader(chars):
    it = iter(chars)

    def read():
        try:
            return next(it)
        except StopIteration:
            return "\r"  # default to Enter at end
    return read


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
