"""Tool registry: the mapping of tool name -> (schema, callable).

Spec: specs/tools.md (to be written, see the header spec template). Placeholder.
Phase 1 registers `read_file` and `bash`; Phase 2 (T1) adds `write_file`,
`edit_file`, `list_dir`, `grep`, `glob`, `append_file`.
"""
from __future__ import annotations

from typing import Any, Callable

ToolHandler = Callable[..., str]
_SCHEMAS: dict[str, dict[str, Any]] = {}
_HANDLERS: dict[str, ToolHandler] = {}


def register(
    name: str,
    schema: dict[str, Any],
    handler: ToolHandler,
) -> None:
    _SCHEMAS[name] = schema
    _HANDLERS[name] = handler


def tool_schemas(allowed: list[str] | None = None) -> list[dict[str, Any]]:
    """Return tool schemas for the model (optionally filtered to `allowed` names, E1/P2)."""
    if allowed is None:
        return list(_SCHEMAS.values())
    return [_SCHEMAS[name] for name in allowed if name in _SCHEMAS]


def dispatch(name: str, arguments: dict[str, Any]) -> str:
    """Run a tool by name and return a string result (safe to feed back)."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Error: unknown tool '{name}'."
    try:
        return handler(**arguments)
    except TypeError as exc:  # bad arguments
        return f"Error: invalid arguments for '{name}': {exc}"
    except Exception as exc:  # tool-level failure
        return f"Error: '{name}' failed: {exc}"
