"""File tools: read_file / write_file / edit_file / list_dir / grep / glob / append_file.

Spec: specs/tools.md (to be written) — the acceptance criteria for `read_file`
are already set there (A1 normal read, A2 missing file error, A3 truncation).

Phase 1 implements `read_file` (with `write_file`); the rest land in Phase 2 (T1).
Placeholder for now.
"""
from __future__ import annotations

from pathlib import Path

from agent.history import History


def read_file(path: str, *, workdir: Path | None = None, history: History | None = None) -> str:
    """Read a file's text as an absolute path, with truncation and a clear missing-file error.

    Acceptance criteria (specs/tools.md A1/A2/A3):
      A1  existing file         -> returns full text
      A2  missing file          -> returns a clear error string (never raises/crashes)
      A3  long file             -> truncated, capped head + "... [truncated N chars]" marker
    """
    raise NotImplementedError("read_file is implemented in Phase 1 (specs/tools.md A1-A3).")


def write_file(path: str, content: str) -> str:
    """Write (or overwrite) a file and return a short confirmation."""
    raise NotImplementedError("write_file is implemented in Phase 1 (specs/tools.md).")
