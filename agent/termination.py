"""Loop termination conditions (N5, B11).

Multiple thresholds, combined so the loop always stops:
  - max_steps, max_tool_calls
  - explicit "done" signal from the model
  - no-progress threshold (repeated identical tool calls)
  - consecutive-failure threshold
  - wall-clock timeout

Spec: specs/termination.md (to be written). Placeholder for now.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config


@dataclass
class LoopState:
    steps: int = 0
    tool_calls: int = 0
    consecutive_failures: int = 0
    done: bool = False


class Terminator:
    """Combined threshold check for whether the agent loop should stop."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def should_stop(self, state: LoopState, elapsed_s: float) -> bool:
        if state.done:
            return True
        if state.steps >= self._config.max_steps:
            return True
        if state.tool_calls >= self._config.max_tool_calls:
            return True
        # TODO(Phase 3/T1): no-progress + consecutive-failure + timeout checks.
        return False
