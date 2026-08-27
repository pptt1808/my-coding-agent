"""Error handling (N6, B10/T1).

Tool exceptions, malformed model output, timeouts and retries funnel through
here so failures are reported back to the model (and never crash the loop).

Spec: specs/errors.md (to be written). Placeholder for now.
"""
from __future__ import annotations


class AgentError(Exception):
    """Base error raised by the coding agent."""


class ToolError(AgentError):
    """A tool failed to run; carries a message safe to hand back to the model."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ModelOutputError(AgentError):
    """Model returned output we could not parse into a tool call / answer."""


class TimeoutError(AgentError):
    """A tool (usually a shell command) exceeded its timeout."""
