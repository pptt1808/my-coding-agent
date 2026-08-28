"""Diff utilities (specs/review.md RV4, D1/P2).

Snapshots of a directory and unified diffs between snapshots, used by the
REPL's /review and the eval harness.
"""
from __future__ import annotations

import difflib
from pathlib import Path

DEFAULT_SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules",
    ".coding-agent", ".idea", ".vscode", "build", "dist", ".env",
}


def snapshot_dir(root: Path, skip_dirs: set[str] | None = None) -> dict[str, str]:
    """Map relative path -> text content for every (text-readable) file."""
    skip = skip_dirs or DEFAULT_SKIP_DIRS
    snapshot: dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in skip for part in rel.parts):
            continue
        try:
            snapshot[str(rel).replace("\\", "/")] = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
    return snapshot


def collect_diff(before: dict[str, str], after: dict[str, str]) -> str:
    """Unified diff between two {relpath: content} snapshots."""
    diffs: list[str] = []
    for rel in sorted(set(before) | set(after)):
        old, new = before.get(rel, ""), after.get(rel, "")
        if old == new:
            continue
        diffs.append(f"--- a/{rel}\n+++ b/{rel}\n")
        diffs.extend(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=1))
    return "\n".join(diffs)


def collect_diff_dirs(before: Path, after: Path, skip_dirs: set[str] | None = None) -> str:
    """Unified diff between two directories (used by the eval harness)."""
    return collect_diff(snapshot_dir(before, skip_dirs), snapshot_dir(after, skip_dirs))
