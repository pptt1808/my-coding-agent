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
        "answer with a short summary of what you changed.\n"
        "PLATFORM: the shell is Windows cmd.exe — heredocs (`<<`) and Unix "
        "`find`/`ls` are NOT available; use `python -c \"...\"`, `dir`, or the "
        "provided glob/grep tools.\n"
        "WORKFLOW: read the full signature and docstring before implementing; "
        "if the spec is ambiguous, match the docstring example exactly and add "
        "your own edge-case checks — avoid speculative verbose probing."
    )


class CodingAgent:
    """A task-solving agent; `run`/`run_turn` for one-shot or conversational use."""

    def __init__(self, config: Config, llm: LLMClient | None = None, model: str | None = None,
                 trace: bool = False, tools: list[str] | None = None,
                 system_prompt: str | None = None) -> None:
        self._config = config
        self._workdir = config.workdir
        self._model = model or config.model
        self._llm = llm or LLMClient(config, model=model)
        self._trace = trace
        self._allowed_tools = set(tools) if tools else None
        self._system_prompt_override = system_prompt  # e.g. the read-only explore prompt
        self.total_tokens: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.steps: int = 0
        self.trajectory: list[dict[str, Any]] = []
        register_builtins()  # idempotent

    @property
    def model(self) -> str:
        return self._model

    def set_model(self, name: str) -> None:
        """Hot-switch the model tier mid-session (/model). Injected fakes are kept."""
        self._model = name
        if isinstance(self._llm, LLMClient):
            self._llm = LLMClient(self._config, model=name)

    def compact(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compress a conversation into a single summary message (specs/compact.md)."""
        if not messages:
            return []
        from .compact import summarize_conversation

        summary = summarize_conversation(self._llm, messages)
        return [{
            "role": "user",
            "content": f"[compacted conversation]\n{summary}\nContinue from here.",
        }]

    def _log(self, msg: str) -> None:
        if self._trace:
            print(f"[trace] {msg}", flush=True)

    def run(self, task: str, stream: bool = False, on_delta: Any | None = None,
            extra_system: str = "") -> str:
        """Run the agent on a task and return its final answer (L1).

        `stream=True` prints model tokens as they arrive (when the LLM client
        supports streaming); `extra_system` is appended to the system prompt
        (e.g. the explore subagent's project brief).
        """
        answer, _ = self.run_turn([{"role": "user", "content": task}],
                                  stream=stream, on_delta=on_delta, extra_system=extra_system)
        return answer

    def run_turn(self, messages: list[dict[str, Any]], extra_system: str = "",
                 stream: bool = False, on_delta: Any | None = None) -> tuple[str, list[dict[str, Any]]]:
        """Execute the loop starting from `messages` (already containing the new user turn).

        `extra_system` is appended to the system prompt (e.g. the REPL's task list /
        the explore subagent's project brief). `stream=True` + `on_delta` streams
        text tokens as they arrive.

        Returns (final answer, updated messages) so callers (e.g. the REPL) can
        continue the same conversation on the next turn.
        """
        tools_context.configure(
            workdir=self._workdir,
            timeout=self._config.command_timeout,
            output_cap=self._config.output_cap_chars,
        )

        history: list[dict[str, Any]] = list(messages)
        system_prompt = self._system_prompt_override or build_system_prompt(str(self._workdir))
        if extra_system:
            system_prompt += "\n\n" + extra_system
        # Aider-style repo map: give the model a compact codebase overview (cached).
        if self._config.code_map:
            try:
                from .repomap import code_map
                cmap = code_map(self._workdir, max_chars=self._config.code_map_chars)
                if cmap.strip():
                    system_prompt += "\n\nCODE MAP (repo structure — use it to locate code):\n" + cmap
            except Exception:
                pass
        # Persistent project conventions (CLAUDE.md-style): read AGENT.md if present.
        if self._config.agent_md:
            try:
                md_file = self._workdir / "AGENT.md"
                if md_file.exists():
                    txt = md_file.read_text(encoding="utf-8")[: self._config.agent_md_chars]
                    system_prompt += "\n\nPROJECT CONVENTIONS (AGENT.md — follow these):\n" + txt
            except Exception:
                pass
        terminator = Terminator(self._config)
        state = LoopState()
        last_tool: str | None = None
        self._last_call_key: str | None = None
        start = time.monotonic()

        while not terminator.should_stop(state, time.monotonic() - start):
            state.steps += 1
            if stream and hasattr(self._llm, "stream_complete"):
                result = self._llm.stream_complete(
                    system_prompt, history, registry.tool_schemas(self._allowed_tools),
                    on_delta=on_delta,
                )
            else:
                result = self._llm.complete(system_prompt, history, registry.tool_schemas(self._allowed_tools))
            self.total_tokens += int(result.usage.get("total_tokens", 0))
            self.input_tokens += int(result.usage.get("prompt_tokens", 0))
            self.output_tokens += int(result.usage.get("completion_tokens", 0))
            # Token budget cap (AgentBudget-style): stop a runaway loop before it
            # balloons the session cost/context.
            if self._config.max_total_tokens > 0 and self.total_tokens >= self._config.max_total_tokens:
                self._log(f"token budget exceeded ({self.total_tokens} >= {self._config.max_total_tokens})")
                break
            self.trajectory.append({
                "step": state.steps,
                "text": result.text[:300],
                "tool_calls": [{"name": tc.name, "arguments": tc.arguments}
                               for tc in result.tool_calls],
                "usage": dict(result.usage),
            })
            self._log(f"step {state.steps}: usage={result.usage}")

            # Auto-compaction (B2/P1): shrink the history when it grows past the threshold.
            if self._config.auto_compact_at_tokens > 0:
                estimate = sum(len(str(m.get("content", ""))) // 4 for m in history)
                if estimate > self._config.auto_compact_at_tokens:
                    self._log(f"auto-compacting history ({estimate} est. tokens)")
                    history = self.compact(history)

            native_calls = parse_tool_calls(result)
            fallback_call = parse_tool_call_from_text(result.text) if not native_calls else None

            # No tool call at all -> this is the final answer.
            if not native_calls and fallback_call is None:
                history.append({"role": "assistant", "content": result.text})
                self._log(f"final answer: {result.text[:200]!r}")
                self.steps += state.steps
                return result.text, history

            self._log("tool calls: " + ", ".join(
                f"{tc.name}({json.dumps(tc.arguments, ensure_ascii=False)[:120]})"
                for tc in (native_calls or [fallback_call])
            ))

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
                    last_tool = tc.name
                    history.append({"role": "tool", "tool_call_id": tc.id, "content": output})
            else:
                # Text-protocol fallback: assistant text + tool output as a user turn.
                assert fallback_call is not None
                history.append({"role": "assistant", "content": result.text})
                state.tool_calls += 1
                output = self._dispatch(state, fallback_call, last_tool)
                last_tool = fallback_call.name
                history.append({"role": "user", "content": f"[tool:{fallback_call.name}]\n{output}"})

        self.steps += state.steps
        return (
            "Error: agent loop stopped without a final answer "
            f"(steps={state.steps}, tool_calls={state.tool_calls})."
        ), history

    def _dispatch(self, state: LoopState, tc: ToolCall, last_tool: str | None) -> str:
        """Run one tool, updating failure/progress counters (L2/L5).

        Tools not enabled via `--tools` are blocked before execution (E1/P2).
        No-progress is only counted for *identical* repeated calls (same tool
        + same arguments) — exploring several different files must not look
        like no progress.
        """
        if self._allowed_tools is not None and tc.name not in self._allowed_tools:
            output = f"Error: tool '{tc.name}' is not enabled in this session"
            self._log(f"  {tc.name} -> blocked (not enabled)")
            state.consecutive_failures += 1
            return output
        output = registry.dispatch(tc.name, tc.arguments)
        self._log(f"  {tc.name} -> {output[:160]!r}")
        if output.startswith("Error:"):
            state.consecutive_failures += 1
        else:
            state.consecutive_failures = 0
        call_key = json.dumps([tc.name, tc.arguments], sort_keys=True, ensure_ascii=False)
        if call_key == self._last_call_key:
            state.no_progress_count += 1
        else:
            state.no_progress_count = 0
        self._last_call_key = call_key
        return output
