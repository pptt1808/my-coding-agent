"""The agent loop (N2, specs/agent-loop.md L1-L5) — the heart of the coding agent.

Pipeline:
    system prompt + history -> LLM -> parse tool calls (native, then text fallback)
    -> execute locally -> feed results back -> check termination -> loop

All four "must self-build" pieces (context, tools, parsing, termination, errors)
are implemented here and in their sibling modules — no agent frameworks.
"""
from __future__ import annotations

import json
import time
from typing import Any

from tools import context as tools_context
from tools import register_builtins, registry

from .config import Config
from .history import History
from .llm import LLMClient, LLMResult, ToolCall
from .parser import parse_tool_call_from_text, parse_tool_calls
from .termination import LoopState, Terminator


def build_system_prompt(workdir: str) -> str:
    """Compose the system prompt that constrains the agent to its workdir (L4)."""
    return (
        "You are a coding agent running inside a sandboxed working directory: "
        f"{workdir}\n"
        "You complete coding tasks by reading files, editing code and running "
        "commands. Prefer minimal, correct changes. When the task is done, "
        "answer with a short summary of what you changed."
    )


class CodingAgent:
    """A single task-solving agent run."""

    def __init__(self, config: Config, llm: LLMClient | None = None) -> None:
        self._config = config
        self._workdir = config.workdir
        self._llm = llm or LLMClient(config)
        register_builtins()  # idempotent

    def run(self, task: str) -> str:
        """Run the agent on a task and return its final answer (L1)."""
        tools_context.configure(
            workdir=self._workdir,
            timeout=self._config.command_timeout,
            output_cap=self._config.output_cap_chars,
        )

        history: list[dict[str, Any]] = [{"role": "user", "content": task}]
        system_prompt = build_system_prompt(str(self._workdir))
        terminator = Terminator(self._config)
        state = LoopState()
        last_tool: str | None = None
        start = time.monotonic()

        while not terminator.should_stop(state, time.monotonic() - start):
            state.steps += 1
            result = self._llm.complete(system_prompt, history, registry.tool_schemas())

            native_calls = parse_tool_calls(result)
            fallback_call = parse_tool_call_from_text(result.text) if not native_calls else None

            # No tool call at all -> this is the final answer.
            if not native_calls and fallback_call is None:
                history.append({"role": "assistant", "content": result.text})
                return result.text

            if native_calls:
                # OpenAI-compatible protocol: assistant message carries tool_calls,
                # then one "tool" message per call id.
                assistant_msg: dict[str, Any] = {"role": "assistant", "content": result.text or None}
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in native_calls
                ]
                history.append(assistant_msg)
                for tc in native_calls:
                    state.tool_calls += 1
                    output = self._dispatch(state, tc, last_tool)
                    history.append({"role": "tool", "tool_call_id": tc.id, "content": output})
                    last_tool = tc.name
            else:
                # Text-protocol fallback: assistant text + tool output as a user turn.
                assert fallback_call is not None
                history.append({"role": "assistant", "content": result.text})
                state.tool_calls += 1
                output = self._dispatch(state, fallback_call, last_tool)
                history.append({"role": "user", "content": f"[tool:{fallback_call.name}]\n{output}"})
                last_tool = fallback_call.name

        return (
            "Error: agent loop stopped without a final answer "
            f"(steps={state.steps}, tool_calls={state.tool_calls})."
        )

    def _dispatch(self, state: LoopState, tc: ToolCall, last_tool: str | None) -> str:
        """Run one tool, updating failure/progress counters (L2/L5)."""
        output = registry.dispatch(tc.name, tc.arguments)
        if output.startswith("Error:"):
            state.consecutive_failures += 1
        else:
            state.consecutive_failures = 0
        if tc.name == last_tool:
            state.no_progress_count += 1
        else:
            state.no_progress_count = 0
        return output
