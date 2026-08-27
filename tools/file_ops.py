"""File tools: read_file / write_file (specs/tools.md A1-A3, B1-B2; safety S2).

All paths are confined to the tools context's workdir: escapes are rejected.
Tool functions NEVER raise on expected failures — they return an error string
so the agent loop can feed it back to the model (errors.md E4).
"""
from __future__ import annotations

from pathlib import Path

from agent.errors import ToolError
from tools import context


def _resolve(path: str) -> Path:
    """Resolve `path` and enforce it stays inside the workdir (safety S2)."""
    wd = context.workdir().resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = wd / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(wd):
        raise ToolError(f"path escapes workdir: {path}")
    return resolved


def read_file(path: str) -> str:
    """Read a file's text. A1 normal read / A2 missing-file error / A3 truncation."""
    try:
        resolved = _resolve(path)
    except ToolError as exc:
        return f"Error: {exc.message}"
    if not resolved.is_file():
        return f"Error: file not found: {path}"
    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # e.g. permission / binary decode issues
        return f"Error: cannot read {path}: {exc}"
    cap = context.output_cap()
    if len(text) > cap:
        text = text[:cap] + f"\n... [truncated {len(text) - cap} chars]"
    return text


def write_file(path: str, content: str) -> str:
    """Write (overwrite) a file and return a short confirmation (B1/B2)."""
    try:
        resolved = _resolve(path)
    except ToolError as exc:
        return f"Error: {exc.message}"
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
    except Exception as exc:
        return f"Error: cannot write {path}: {exc}"
    return f"Wrote {len(content)} chars to {path}"
