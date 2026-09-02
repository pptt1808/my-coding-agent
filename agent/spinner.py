"""A Claude-Code-style status line for the REPL — no background thread.

The agent loop calls `on_status(label)` (thinking, running a tool) but emits no
text while it works, so the terminal would otherwise look frozen. This renders a
single status line (using `\r` + erase-to-EOL) and clears it the moment real
output arrives.

IMPORTANT design choice: this is deliberately STATIC — no background thread
advances a spin glyph. A background thread writing to stdout concurrently with
the main thread (which prints the streamed answer) interleaves bytes and leaves
garbage on screen. Instead the REPL:

  - calls `start(label)` / `update(label)` right before a long operation, and
  - calls `clear()` as soon as it prints any real token / the final answer.

Everything is synchronous and single-threaded, so nothing can be torn.
"""
from __future__ import annotations

import sys
from typing import Any

_ERASE = "\x1b[2K"  # erase to end of line


class StatusSpinner:
    """Renders a single status line on the terminal (sync, no thread)."""

    def __init__(self, stream: Any = None) -> None:
        self._stream = stream or sys.stdout
        self._label = ""

    def start(self, label: str = "思考中") -> None:
        """Show a status line (idempotent; just redraws)."""
        self._label = label
        self._draw()

    def update(self, label: str) -> None:
        """Change the status text (idempotent)."""
        self._label = label
        self._draw()

    def clear(self) -> None:
        """Erase the status line (call before printing real output)."""
        if self._label:
            self._stream.write("\r" + _ERASE)
            self._stream.flush()
            self._label = ""

    def _draw(self) -> None:
        if not self._label:
            return
        # move to column 0, erase to EOL, then draw the status line.
        self._stream.write(f"\r{_ERASE}[agent] {self._label}")
        self._stream.flush()
