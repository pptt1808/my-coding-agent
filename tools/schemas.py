"""JSON-schema tool definitions exposed to the model (specs/tools.md).

Each entry follows the OpenAI function-calling schema shape so any
OpenAI-compatible gateway can consume them natively.
"""
from __future__ import annotations

from typing import Any

READ_FILE: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file inside the working directory. Returns its content, truncated with a marker if very long.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file, relative to the working directory or absolute within it."},
            },
            "required": ["path"],
        },
    },
}

WRITE_FILE: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write (overwrite) a file inside the working directory. Parent directories are created as needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write."},
                "content": {"type": "string", "description": "Full content to write."},
            },
            "required": ["path", "content"],
        },
    },
}

BASH: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Run a shell command in the working directory with a timeout. Returns combined "
            "stdout+stderr (capped, tail-first). "
            "IMPORTANT: the shell is Windows cmd.exe — do NOT use heredocs (`<<`), Unix "
            "`find`/`ls`/`grep`; use `python -c \"...\"` for inline checks, `dir` for listing, "
            "and the provided glob/grep/read_file tools instead."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run."},
            },
            "required": ["command"],
        },
    },
}

LIST_DIR: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_dir",
        "description": "List entries of a directory inside the working directory (subdirectories are suffixed with '/').",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path, defaults to '.'."},
            },
        },
    },
}

GLOB: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "glob",
        "description": "Find files inside the working directory matching a glob pattern, e.g. '**/*.py'.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern relative to the working directory."},
            },
            "required": ["pattern"],
        },
    },
}

GREP: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "grep",
        "description": "Regex search inside the working directory (file or recursive directory). Returns 'path:line: content' matches.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regular expression to search for."},
                "path": {"type": "string", "description": "File or directory to search, defaults to '.'."},
            },
            "required": ["pattern"],
        },
    },
}

APPEND_FILE: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "append_file",
        "description": "Append content to a file inside the working directory (creates the file if missing).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path of the file to append to."},
                "content": {"type": "string", "description": "Content to append."},
            },
            "required": ["path", "content"],
        },
    },
}

EDIT_FILE: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Exact text replacement in a file inside the working directory (default: first occurrence; replace_all to replace every occurrence).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path of the file to edit."},
                "old": {"type": "string", "description": "Exact text to find."},
                "new": {"type": "string", "description": "Replacement text."},
                "replace_all": {"type": "boolean", "description": "Replace every occurrence (default false)."},
            },
            "required": ["path", "old", "new"],
        },
    },
}

SKILL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "Skill",
        "description": "Load a skill package's instructions (its SKILL.md body) by name, from the available-skills catalog. Use when the task matches a skill's description.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The skill name to load."},
            },
            "required": ["name"],
        },
    },
}

ALL: list[dict[str, Any]] = [READ_FILE, WRITE_FILE, BASH, LIST_DIR, GLOB, GREP, APPEND_FILE, EDIT_FILE, SKILL]
