"""Shell tool: bash (specs/tools.md C1-C4, safety.md S1/S3).

Runs a command in the tools context's workdir with a timeout, captures combined
output, blocks dangerous commands, and always returns a string (never raises).
"""
from __future__ import annotations

import subprocess

from tools import context


def _is_dangerous(command: str) -> bool:
    norm = command.strip().lower()
    return any(pattern in norm for pattern in context.blacklist())


def bash(command: str, *, timeout: int | None = None) -> str:
    """Run a shell command; return combined stdout+stderr (capped) as text."""
    if _is_dangerous(command):
        return f"Error: command blocked by safety blacklist: {command}"

    t = timeout if timeout is not None else context.timeout()
    wd = context.workdir()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=t,
            cwd=wd,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {t}s: {command}"
    except Exception as exc:
        return f"Error: failed to run command: {exc}"

    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        out = f"[exit code: {proc.returncode}]\n" + out
    cap = context.output_cap()
    if len(out) > cap:
        # Tail-first (C4b/P2): command errors/results usually sit at the end.
        out = f"... [truncated {len(out) - cap} chars]\n" + out[-cap:]
    return out
