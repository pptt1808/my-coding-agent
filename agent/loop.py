"""The agent loop (N2) — the heart of the coding agent.

Pipeline:
    system prompt + history  ->  LLM  ->  parse tool calls  ->  execute locally
    ->  feed results back  ->  check termination  ->  loop

Spec: specs/agent-loop.md (to be written). Placeholder for now; Phase 1 wires
this up end-to-end (including the first `read_file` / `bash` tools).
"""
from __future__ import annotations

from typing import Any

from .config import Config
from .termination import LoopState


class CodingAgent:
    """A single task-solving agent run."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def run(self, task: str) -> str:
        """Run the agent on a task string and return its final answer."""
        state = LoopState()
        history: list[dict[str, Any]] = []
        raise NotImplementedError(
            "CodingAgent.run is wired up in Phase 1 (specs/agent-loop.md). "
            "For now the scaffold only defines the pipeline + termination hooks."
        )


def build_system_prompt(workdir: str) -> str:
    """Compose the system prompt that constrains the agent to its workdir."""
    return (
        "You are a helpful coding agent running inside a sandboxed working "
        f"directory: {workdir}. Read files, edit code and run commands to "
        "complete the user's task. Prefer minimal, correct changes."
    )
