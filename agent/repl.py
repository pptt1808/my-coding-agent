"""Interactive REPL (specs/cli.md R1-R10, specs/tasklist.md, specs/session.md).

`coding-agent chat` turns the one-shot CLI into a conversational session:
plain lines are sent to the agent as new turns (shared history), `/`-prefixed
lines are session-control slash commands. P0: /help /exit /clear /compact
/status /model. P1: /save /resume /ls /task /cost. All logic self-built.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from tools import context as tools_context

from .config import Config
from .diff import collect_diff, snapshot_dir
from .llm import LLMClient
from .loop import CodingAgent
from .session import Session, list_sessions, load_session, new_session_id, save_session
from eval.judge import Judge

HELP = """slash commands:
  /help            show this help
  /exit            quit the session
  /clear           reset conversation history
  /compact         compress the conversation into an LLM summary
  /status          show model, workdir, steps, tokens, message count
  /cost            show input/output/total token usage
  /model <name>    switch model tier (e.g. deepseek-v4-pro)
  /save [name]     persist the session (auto id if name omitted)
  /resume <name>   load a saved session
  /ls              list saved sessions
  /task add <t>    add a todo item
  /task list       show the todo list
  /task done <n>   mark todo #n done (removes it)
  /task clear      clear the todo list
  /review          diff changes since session start, run tests, judge the diff
  /permissions     show workdir + blacklist
  /permissions block <pattern>   add a session blacklist pattern
  /permissions reset            restore the default blacklist
Anything else is sent to the agent as a new turn."""

DEFAULT_REVIEW_RUBRIC = {
    "correctness": "Does the change satisfy the requested behavior?",
    "quality": "Is the code clear, idiomatic and free of dead code?",
    "minimal": "Is the change minimal and on-topic?",
}


class ReplSession:
    """One interactive session: keeps the conversation between turns."""

    def __init__(self, config: Config, llm: LLMClient | None = None, model: str | None = None,
                 trace: bool = False, tools: list[str] | None = None,
                 judge: Any | None = None) -> None:
        self._config = config
        self._llm = llm
        self._judge = judge
        self._agent = CodingAgent(config, llm=llm, model=model, trace=trace, tools=tools)
        self._messages: list[dict[str, Any]] = []
        self._todos: list[str] = []
        self._snapshot = snapshot_dir(self._config.workdir)  # for /review
        self.running = True

    # ------------------------------------------------------------------ input

    def handle(self, line: str) -> list[str]:
        """Process one input line; returns lines to print (R1/R3-R10)."""
        line = line.strip()
        if not line:
            return []
        if line.startswith("/"):
            return self._slash(line)
        return self._turn(line)

    def _task_block(self) -> str:
        if not self._todos:
            return ""
        items = "\n".join(f"{i}. {t}" for i, t in enumerate(self._todos, start=1))
        return "TASK LIST (track your work against these items):\n" + items

    def _turn(self, line: str) -> list[str]:
        self._messages.append({"role": "user", "content": line})
        answer, self._messages = self._agent.run_turn(self._messages, extra_system=self._task_block())
        return [answer]

    # ---------------------------------------------------------------- slash

    def _slash(self, line: str) -> list[str]:
        cmd, _, arg = line.partition(" ")
        cmd = cmd.lower()
        if cmd == "/help":
            return [HELP]
        if cmd == "/exit":
            self.running = False
            return ["bye."]
        if cmd == "/clear":
            self._messages = []
            return ["[history cleared]"]
        if cmd == "/status":
            return [(
                f"model={self._agent.model} workdir={self._config.workdir} "
                f"steps={self._agent.steps} tokens={self._agent.total_tokens} "
                f"messages={len(self._messages)} todos={len(self._todos)}"
            )]
        if cmd == "/cost":
            return [(
                f"model={self._agent.model} input={self._agent.input_tokens} "
                f"output={self._agent.output_tokens} total={self._agent.total_tokens} "
                f"steps={self._agent.steps}"
            )]
        if cmd == "/compact":
            if not self._messages:
                return ["[nothing to compact]"]
            self._messages = self._agent.compact(self._messages)
            return ["[conversation compacted]"]
        if cmd == "/model":
            if not arg.strip():
                return [f"current model: {self._agent.model}"]
            self._agent.set_model(arg.strip())
            return [f"model switched to {self._agent.model}"]
        if cmd == "/save":
            sid = arg.strip() or new_session_id()
            session = Session(
                id=sid,
                model=self._agent.model,
                workdir=str(self._config.workdir),
                messages=self._messages,
                steps=self._agent.steps,
                total_tokens=self._agent.total_tokens,
                input_tokens=self._agent.input_tokens,
                output_tokens=self._agent.output_tokens,
            )
            save_session(session, self._config.workdir)
            return [f"session saved: {sid}"]
        if cmd == "/resume":
            if not arg.strip():
                return ["usage: /resume <name>"]
            try:
                saved = load_session(self._config.workdir, arg.strip())
            except FileNotFoundError as exc:
                return [str(exc)]
            return self._apply_session(saved)
        if cmd == "/ls":
            sessions = list_sessions(self._config.workdir)
            if not sessions:
                return ["no saved sessions"]
            return [
                f"{s.id}  updated={s.updated_at:.0f}  messages={len(s.messages)}  model={s.model}"
                for s in sessions
            ]
        if cmd == "/task":
            return self._task(arg)
        if cmd == "/review":
            return self._review()
        if cmd == "/permissions":
            return self._permissions(arg)
        return [f"unknown command: {cmd}. Type /help for usage."]

    # ------------------------------------------------------------- P2: review

    def _trajectory_text(self) -> str:
        return "\n".join(
            f"step {e['step']}: text={e['text']!r} calls={e['tool_calls']}"
            for e in self._agent.trajectory
        )

    def _review(self) -> list[str]:
        current = snapshot_dir(self._config.workdir)
        diff = collect_diff(self._snapshot, current)
        if not diff:
            return ["nothing to review (no changes since session start)"]

        lines = ["[review] diff since session start:", diff[:1500]]
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=self._config.workdir, capture_output=True, text=True,
                timeout=120, encoding="utf-8", errors="replace",
            )
            if proc.returncode == 0:
                lines.append("[review] tests: PASS")
            else:
                tail = ((proc.stdout or "") + (proc.stderr or ""))[-400:]
                lines.append(f"[review] tests: FAIL\n{tail}")
        except Exception as exc:
            lines.append(f"[review] tests: skipped ({exc})")

        judge = self._judge or Judge(self._config, model=self._agent.model)
        scores = judge.score("", self._trajectory_text(), diff, DEFAULT_REVIEW_RUBRIC)
        lines.append("[review] judge: " + ", ".join(f"{k}={v}" for k, v in scores.items()))
        rationale = getattr(judge, "last_rationale", "")
        if rationale:
            lines.append(f"[review] rationale: {rationale}")
        return lines

    # --------------------------------------------------------- P2: permissions

    def _permissions(self, arg: str) -> list[str]:
        sub, _, pattern = arg.partition(" ")
        if sub == "block" and pattern.strip():
            tools_context.configure(extra_blacklist=[pattern.strip()])
            return [f"blocked pattern (session only): {pattern.strip()}"]
        if sub == "reset":
            tools_context.configure(extra_blacklist=[])
            return ["blacklist reset to default"]
        return [
            f"workdir={self._config.workdir}",
            "blacklist: " + ", ".join(tools_context.blacklist()),
            "usage: /permissions [block <pattern>|reset]",
        ]

    def _apply_session(self, saved: Session) -> list[str]:
        """Restore a saved session: messages, model, stats; rebuild agent if workdir changed."""
        saved_wd = Path(saved.workdir)
        if saved_wd != self._config.workdir:
            self._config = replace(self._config, workdir=saved_wd)
        self._agent = CodingAgent(self._config, llm=self._llm, model=saved.model)
        self._agent.steps = saved.steps
        self._agent.total_tokens = saved.total_tokens
        self._agent.input_tokens = saved.input_tokens
        self._agent.output_tokens = saved.output_tokens
        self._messages = list(saved.messages)
        return [f"session resumed: {saved.id} (model={saved.model}, workdir={saved_wd})"]

    def _task(self, arg: str) -> list[str]:
        sub, _, rest = arg.partition(" ")
        sub = sub.lower()
        if sub == "add":
            if not rest.strip():
                return ["usage: /task add <text>"]
            self._todos.append(rest.strip())
            return [f"added todo #{len(self._todos)}: {rest.strip()}"]
        if sub == "list":
            if not self._todos:
                return ["(no todos)"]
            return [f"{i}. {t}" for i, t in enumerate(self._todos, start=1)]
        if sub == "done":
            try:
                idx = int(rest.strip())
            except ValueError:
                return ["usage: /task done <n>"]
            if not (1 <= idx <= len(self._todos)):
                return [f"no todo #{idx}"]
            removed = self._todos.pop(idx - 1)
            return [f"done: {removed}"]
        if sub == "clear":
            self._todos = []
            return ["[todos cleared]"]
        return ["usage: /task add|list|done|clear"]
