"""Local tools package: definitions + local execution (N3).

`register_builtins()` must run before the agent loop starts (CodingAgent.__init__
does this) so the model sees read_file/write_file/bash.
"""
from __future__ import annotations

from . import context, file_ops, schemas, shell, skills_tool  # noqa: F401  (re-export)
from .registry import dispatch, register, tool_schemas


def register_builtins() -> None:
    """Register the built-in tool set into the registry (idempotent)."""
    register("read_file", schemas.READ_FILE, file_ops.read_file)
    register("write_file", schemas.WRITE_FILE, file_ops.write_file)
    register("bash", schemas.BASH, shell.bash)
    register("list_dir", schemas.LIST_DIR, file_ops.list_dir)
    register("glob", schemas.GLOB, file_ops.glob)
    register("grep", schemas.GREP, file_ops.grep)
    register("append_file", schemas.APPEND_FILE, file_ops.append_file)
    register("edit_file", schemas.EDIT_FILE, file_ops.edit_file)
    register("Skill", schemas.SKILL, skills_tool.skill)


__all__ = ["context", "file_ops", "schemas", "shell", "skills_tool",
           "dispatch", "register", "tool_schemas", "register_builtins"]
