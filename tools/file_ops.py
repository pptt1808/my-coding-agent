"""File tools (specs/tools.md): read/write (A/B), plus the T1 set:
list_dir L1-L3, glob G1-G3, grep GR1-GR4, append_file AP1-AP2, edit_file ED1-ED5.

All paths are confined to the tools context's workdir: escapes are rejected.
Tool functions NEVER raise on expected failures — they return an error string
so the agent loop can feed it back to the model (errors.md E4).
"""
from __future__ import annotations

import re
from pathlib import Path

from agent.errors import ToolError
from tools import context

# Directories never searched by grep / list_dir (noise + secrets).
_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv",
              "node_modules", ".idea", ".vscode", "build", "dist"}
_MAX_GREP_LINES = 200


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
        # Tail-first (A3b/P2): errors and results usually sit at the end.
        text = f"... [truncated {len(text) - cap} chars]\n" + text[-cap:]
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


# --------------------------------------------------------------------------
# T1 tool set (specs/tools.md)
# --------------------------------------------------------------------------

def list_dir(path: str = ".") -> str:
    """List directory entries, dirs suffixed with '/' (L1/L2/L3)."""
    try:
        resolved = _resolve(path)
    except ToolError as exc:
        return f"Error: {exc.message}"
    if not resolved.is_dir():
        return f"Error: directory not found: {path}"
    entries = [
        child.name + ("/" if child.is_dir() else "")
        for child in sorted(resolved.iterdir(), key=lambda p: p.name.lower())
    ]
    return "\n".join(entries) if entries else "(empty)"


def glob(pattern: str) -> str:
    """Return matching file paths relative to the workdir (G1/G2/G3)."""
    if ".." in Path(pattern).parts:
        return f"Error: glob pattern escapes workdir: {pattern}"
    wd = context.workdir()
    try:
        matches = sorted(
            str(p.relative_to(wd)).replace("\\", "/")
            for p in wd.glob(pattern)
            if p.is_file()
        )
    except Exception as exc:
        return f"Error: invalid glob pattern: {exc}"
    if not matches:
        return "(no matches)"
    return "\n".join(matches)


def grep(pattern: str, path: str = ".") -> str:
    """Regex search inside the workdir; `path:line: content` lines (GR1-GR4)."""
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"
    try:
        root = _resolve(path)
    except ToolError as exc:
        return f"Error: {exc.message}"
    if not root.exists():
        return f"Error: path not found: {path}"

    out: list[str] = []

    def visit(p: Path) -> None:
        if len(out) >= _MAX_GREP_LINES:
            return
        if p.is_dir():
            for child in sorted(p.iterdir(), key=lambda c: c.name.lower()):
                if child.name in _SKIP_DIRS or child.name.startswith("."):
                    continue
                visit(child)
        elif p.is_file():
            rel = str(p.relative_to(context.workdir())).replace("\\", "/")
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                return
            for i, line in enumerate(lines, start=1):
                if rx.search(line):
                    out.append(f"{rel}:{i}: {line}")
                    if len(out) >= _MAX_GREP_LINES:
                        return

    visit(root)
    if not out:
        return "(no matches)"
    text = "\n".join(out)
    cap = context.output_cap()
    if len(text) > cap:
        text = text[:cap] + "\n... [truncated]"
    return text


def append_file(path: str, content: str) -> str:
    """Append content to a file, creating it if missing (AP1/AP2)."""
    try:
        resolved = _resolve(path)
    except ToolError as exc:
        return f"Error: {exc.message}"
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("a", encoding="utf-8") as fh:
            fh.write(content)
    except Exception as exc:
        return f"Error: cannot append {path}: {exc}"
    return f"Appended {len(content)} chars to {path}"


def edit_file(path: str, old: str, new: str, replace_all: bool = False) -> str:
    """Exact text replacement in a workdir file (ED1-ED5)."""
    if not old:
        return "Error: 'old' must not be empty"
    try:
        resolved = _resolve(path)
    except ToolError as exc:
        return f"Error: {exc.message}"
    if not resolved.is_file():
        return f"Error: file not found: {path}"
    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Error: cannot read {path}: {exc}"
    if old not in text:
        return f"Error: pattern not found in {path}: {old[:80]!r}"
    new_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    try:
        resolved.write_text(new_text, encoding="utf-8")
    except Exception as exc:
        return f"Error: cannot write {path}: {exc}"
    count = text.count(old) if replace_all else 1
    return f"Replaced {count} occurrence(s) in {path}"
