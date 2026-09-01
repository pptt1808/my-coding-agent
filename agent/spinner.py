"""A Claude-Code-style status line (spinner) for the REPL.

The agent loop calls `on_status(label)` frequently (thinking, running a tool,
done) but emits no text while it works. This renders a single status line on the
terminal (using `\r` + erase-to-EOL) and clears it the moment real text arrives,
so the user always sees *something* happening and never a dead-looking screen.

Two modes:
  - animated (default): a background thread advances a spinner glyph so the line
    visibly "ticks" while the agent is blocked waiting on the LLM/tool.
  - `on_delta` (streaming): the REPL must call `sink.clear()` before printing each
    incoming token, so the spinner is replaced by the real answer text.

Thread-safety: the tick thread only writes the status line; the main thread
writes real output. Both go through a small lock so lines don't interleave.
"""
from __future__ import annotations

import sys
import threading
import time
from typing import Any

_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧")
_ERASE = "\x1b[2K"  # erase to end of line


class StatusSpinner:
    """Renders a single status line that starts with an animated spinner glyph."""

    def __init__(self, stream: Any = None, frames: tuple[str, ...] = _FRAMES,
                 interval: float = 0.08) -> None:
        self._stream = stream or sys.stdout
        self._frames = frames
        self._interval = interval
        self._label = ""
        self._idx = 0
        self._active = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self, label: str = "思考中") -> None:
        """Begin showing an animated status line."""
        with self._lock:
            if self._active:
                return
            self._label = label
            self._active = True
        self._thread = threading.Thread(target=self._tick, daemon=True)
        self._thread.start()

    def update(self, label: str) -> None:
        """Change the status text (called from on_status)."""
        with self._lock:
            self._label = label
            self._redraw_locked()

    def clear(self) -> None:
        """Erase the status line (call before printing real output)."""
        self._stop()
        with self._lock:
            self._stream.write("\r" + _ERASE)
            self._stream.flush()

    # -- internals ---------------------------------------------------------

    def _redraw_locked(self) -> None:
        frame = self._frames[self._idx % len(self._frames)]
        # move to column 0, erase to EOL, then draw '<spinner> <label>'
        self._stream.write("\r" + _ERASE + f"{frame} {self._label}")
        self._stream.flush()

    def _tick(self) -> None:
        while True:
            with self._lock:
                if not self._active:
                    return
                self._idx += 1
                self._redraw_locked()
            time.sleep(self._interval)

    def _stop(self) -> None:
        with self._lock:
            was = self._active
            self._active = False
        if was and self._thread is not None:
            # a background thread cannot be joined from the same lock, but we
            # only need it to exit; daemon=True lets it clean up on process end.
            self._thread = None
