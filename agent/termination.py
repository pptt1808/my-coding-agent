"""Loop termination conditions (N5, B11, specs/termination.md T1-T6).

Multiple thresholds combined so the loop ALWAYS stops: done signal, max steps,
max tool calls, consecutive failures, no-progress (repeated identical tool),
and wall-clock timeout.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config


@dataclass
class LoopState:
    steps: int = 0
    tool_calls: int = 0
    consecutive_failures: int = 0
    no_progress_count: int = 0
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
        if state.consecutive_failures >= self._config.max_consecutive_failures:
            return True
        if state.no_progress_count >= self._config.no_progress_limit:
            return True
        if elapsed_s >= self._config.max_elapsed_s:
            return True
        return False
