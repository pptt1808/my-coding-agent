"""Shell execution tool (`bash`).

Spec: specs/tools.md (to be written). Placeholder.
Phase 1 executes commands with a timeout, captures stdout/stderr, and reports
a clean error string on timeout/failure so the loop never crashes.
"""
from __future__ import annotations


def bash(command: str, *, timeout: int = 60) -> str:
    """Run a shell command and return combined stdout/stderr (capped).

    Must honor the dangerous-command blacklist (B4 / Phase 4) for commands like
    `rm -rf`, `git push --force`, etc.
    """
    raise NotImplementedError("bash is implemented in Phase 1 (specs/tools.md).")
