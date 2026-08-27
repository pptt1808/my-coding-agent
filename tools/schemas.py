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
        "description": "Run a shell command in the working directory with a timeout. Returns combined stdout+stderr (capped).",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run."},
            },
            "required": ["command"],
        },
    },
}

ALL: list[dict[str, Any]] = [READ_FILE, WRITE_FILE, BASH]
