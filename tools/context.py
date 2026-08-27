"""Per-run tool context (workdir, timeouts, caps, safety blacklist).

Tools need runtime configuration (which directory the agent may touch, how long
commands may run, how much output to keep) without threading it through every
call signature. contextvars keeps this per-run/thread safe.
"""
from __future__ import annotations

import contextvars
from pathlib import Path

DEFAULT_BLACKLIST: tuple[str, ...] = (
    "rm -rf",
    "rm -fr",
    "git push --force",
    "git push -f",
    "sudo",
    "mkfs.",
    "shutdown",
    ":(){",          # fork bomb
    "> /dev/sda",
    "dd if=/dev/zero",
)

_workdir: contextvars.ContextVar[Path] = contextvars.ContextVar("workdir", default=Path.cwd())
_timeout: contextvars.ContextVar[int] = contextvars.ContextVar("timeout", default=60)
_output_cap: contextvars.ContextVar[int] = contextvars.ContextVar("output_cap", default=8000)
_blacklist: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
    "blacklist", default=DEFAULT_BLACKLIST
)


def configure(
    *,
    workdir: Path | str | None = None,
    timeout: int | None = None,
    output_cap: int | None = None,
    extra_blacklist: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Set tool runtime context. Only the given fields change; others persist."""
    if workdir is not None:
        _workdir.set(Path(workdir).resolve())
    if timeout is not None:
        _timeout.set(timeout)
    if output_cap is not None:
        _output_cap.set(output_cap)
    if extra_blacklist is not None:
        _blacklist.set(DEFAULT_BLACKLIST + tuple(extra_blacklist))


def workdir() -> Path:
    return _workdir.get()


def timeout() -> int:
    return _timeout.get()


def output_cap() -> int:
    return _output_cap.get()


def blacklist() -> tuple[str, ...]:
    return _blacklist.get()
