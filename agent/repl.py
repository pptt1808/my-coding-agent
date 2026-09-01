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

# directories excluded from undo snapshots (cache/noise, not user content)
_UNDO_SKIP = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules",
              ".coding-agent", ".idea", ".vscode", ".env", "build", "dist"}

HELP = """slash commands (type a prefix and press Enter to expand, e.g. /comp):
  /help            show this help
  /exit            quit the session
  /clear           reset conversation history
  /compact         compress the conversation into an LLM summary
  /status          show model, workdir, steps, tokens, message count
  /cost            show input/output/total token usage
  /model <name>    switch model tier (e.g. deepseek-v4-pro)
  /save [name]     persist the session (auto id if name omitted)
  /resume [id|n]   list saved sessions, then pick a number to load one
  /ls              list saved sessions
  /task add <t>    add a todo item
  /task list       show the todo list
  /task done <n>   mark todo #n done (removes it)
  /task clear      clear the todo list
  /review          diff changes since session start, run tests, judge the diff
  /undo            revert the workdir to before the last turn (checkpoint)
  /redo            re-apply the last undo
  /explore         run a cheap read-only subagent and add a project brief to context
  /codemap         show the Aider-style repo map (codebase structure) for this workspace
  /skills          list available skill packages (skills/<name>/SKILL.md)
  /skill <name>    load a skill's instructions into context
  /pm              toggle PM demo mode (same agent; /vision /story /mvp /validate /polish /pitch)
  /plan            explore + plan a todo list with cheap subagents
  /permissions     show workdir + blacklist
  /permissions block <pattern>   add a session blacklist pattern
  /permissions reset            restore the default blacklist
Anything else is sent to the agent as a new turn."""

COMMANDS = ["help", "exit", "clear", "compact", "status", "cost", "model",
            "save", "resume", "ls", "task", "review", "undo", "redo",
            "explore", "plan", "permissions", "codemap", "skills", "pm",
            "vision", "story", "mvp", "validate", "polish", "pitch"]

# PM-mode step commands (only valid after /pm). Each accepts trailing text as
# the user's message, e.g. "/vision 我的产品是给大学生做的".
_PM_STEP_COMMANDS = frozenset(("vision", "story", "mvp", "validate", "polish", "pitch"))

DEFAULT_REVIEW_RUBRIC = {
    "correctness": "Does the change satisfy the requested behavior?",
    "quality": "Is the code clear, idiomatic and free of dead code?",
    "minimal": "Is the change minimal and on-topic?",
}

# ANSI colors for the chat UI (R13)
C_RESET = "\033[0m"
C_CYAN = "\033[36m"
C_PROMPT = "\033[32m"  # green prompt


def _display_width(text: str) -> int:
    """Terminal display width: CJK/full-width chars count as 2."""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in text)


def _truncate_dw(line: str, width: int) -> str:
    acc = 0
    for i, ch in enumerate(line):
        acc += 2 if ord(ch) > 0x2E7F else 1
        if acc > width:
            return line[:i] + "…"
    return line


def render_chat_box(text: str, prefix: str = "你") -> str:
    """A chat bubble around the user's input (R13)."""
    lines = text.splitlines() or [""]
    lines = [f"{prefix}: {lines[0]}"] + lines[1:]
    width = min(max(max(_display_width(l) for l in lines), 12), 76)
    top = "┌" + "─" * (width + 2) + "┐"
    middle = []
    for line in lines:
        lw = _display_width(line)
        if lw > width:
            line = _truncate_dw(line, width)
            lw = _display_width(line)
        middle.append("│ " + line + " " * (width - lw) + " │")
    bottom = "└" + "─" * (width + 2) + "┘"
    return "\n".join([top, *middle, bottom])


class ReplSession:
    """One interactive session: keeps the conversation between turns."""

    def __init__(self, config: Config, llm: LLMClient | None = None, model: str | None = None,
                 trace: bool = False, tools: list[str] | None = None,
                 judge: Any | None = None, stream: bool = True,
                 echo_input: bool = False) -> None:
        self._config = config
        self._llm = llm
        self._judge = judge
        self._trace = trace           # reused when /resume rebuilds the agent
        self._tools = tools           # reused when /resume rebuilds the agent
        self._agent = CodingAgent(config, llm=llm, model=model, trace=trace, tools=tools)
        self._messages: list[dict[str, Any]] = []
        self._todos: list[str] = []
        self._snapshot = snapshot_dir(self._config.workdir)  # for /review
        self._undo_stack: list[dict[str, str]] = []  # undo/redo snapshots (U1-U4)
        self._redo_stack: list[dict[str, str]] = []
        self._pm_mode = False  # PM mode is a mode of THIS agent (activated via /pm)
        self._pm_messages: list[dict[str, Any]] = []
        self._stream = stream
        self._echo_input = echo_input
        self.running = True

    # ------------------------------------------------------------------ input

    def handle(self, line: str) -> list[str]:
        """Process one input line; returns lines to print (R1/R3-R13)."""
        line = line.strip()
        if not line:
            return []
        if line.startswith("／"):  # full-width slash from CJK IMEs -> "/" (R12)
            line = "/" + line[1:]
        # defensive: collapse a stray leading "//" (e.g. pasted command or a
        # double-slash from the interactive menu path) into a single "/".
        while line.startswith("//"):
            line = line[1:]
        if line.startswith("/"):
            return self._slash(line)
        return self._turn(line)

    def _task_block(self) -> str:
        if not self._todos:
            return ""
        items = "\n".join(f"{i}. {t}" for i, t in enumerate(self._todos, start=1))
        return "TASK LIST (track your work against these items):\n" + items

    def _turn(self, line: str) -> list[str]:
        # echo the input as a chat bubble; the interactive reader already erased
        # the echoed prompt line, so this bubble occupies that spot (shown once).
        # For a multi-line PASTE the reader keeps the pasted lines visible, so
        # we must NOT render a bubble too (would show the text twice).
        if self._echo_input and "\n" not in line:
            print(f"{C_CYAN}{render_chat_box(line)}{C_RESET}", flush=True)
        if self._pm_mode:
            from .pm import pm_turn
            self._pm_messages, out = pm_turn(self._agent, self._pm_messages, line)
            return out
        prev_messages = list(self._messages)  # for Ctrl+C rollback (R14)
        # snapshot the workdir BEFORE the turn so /undo can revert the agent's edits
        self._before_turn_snapshot()
        self._messages.append({"role": "user", "content": line})
        try:
            if self._stream:
                streamed: list[str] = []

                def _on_delta(text: str) -> None:
                    streamed.append(text)
                    print(text, end="", flush=True)

                answer, self._messages = self._agent.run_turn(
                    self._messages, extra_system=self._task_block(), stream=True, on_delta=_on_delta,
                )
                if streamed:
                    print()  # newline after the streamed answer
                    return []  # already printed live (R11: no duplicate)
                return [answer]
            answer, self._messages = self._agent.run_turn(
                self._messages, extra_system=self._task_block())
            return [answer]
        except KeyboardInterrupt:
            # Ctrl+C mid-turn: discard partial output and restore the conversation.
            self._messages = prev_messages
            raise

    # ------------------------------------------------------------------ undo / redo

    def _before_turn_snapshot(self) -> None:
        self._undo_stack.append(snapshot_dir(self._config.workdir, _UNDO_SKIP))
        self._redo_stack.clear()  # new change invalidates redo

    def _restore_workdir(self, snapshot: dict[str, str]) -> None:
        """Revert the workdir to a snapshot: write files, delete files that weren't there."""
        from pathlib import Path
        root = Path(self._config.workdir)
        current = snapshot_dir(root, _UNDO_SKIP)
        for rel, content in snapshot.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        for rel in current:
            if rel not in snapshot:
                p = root / rel
                try:
                    p.unlink()
                except Exception:
                    pass

    def _undo(self) -> list[str]:
        if not self._undo_stack:
            return ["(nothing to undo)"]
        snapshot = self._undo_stack.pop()
        self._redo_stack.append(snapshot_dir(self._config.workdir, _UNDO_SKIP))
        self._restore_workdir(snapshot)
        return [f"[undo] reverted workdir ({len(snapshot)} files)"]

    def _redo(self) -> list[str]:
        if not self._redo_stack:
            return ["(nothing to redo)"]
        snapshot = self._redo_stack.pop()
        self._undo_stack.append(snapshot_dir(self._config.workdir, _UNDO_SKIP))
        self._restore_workdir(snapshot)
        return [f"[redo] re-applied ({len(snapshot)} files)"]

    # ---------------------------------------------------------------- slash

    def _slash(self, line: str) -> list[str]:
        cmd, _, arg = line.partition(" ")
        cmd = cmd.lower()

        # "/" alone -> command menu (R12)
        if cmd == "/":
            return [HELP]
        # prefix expansion (R12): /comp -> /compact when unique
        name = cmd[1:]
        if len(cmd) > 1 and name not in COMMANDS:
            matches = [c for c in COMMANDS if c.startswith(name)]
            if len(matches) == 1:
                expanded = "/" + matches[0] + (" " + arg if arg else "")
                return self._slash(expanded)
            if len(matches) > 1:
                return [f"ambiguous prefix {cmd}: {', '.join('/' + m for m in matches)}",
                        "type / for the full list."]

        if cmd == "/help":
            return [HELP]
        # PM mode: /pm toggles a MODE of this same agent; pm steps when in that mode.
        if cmd == "/pm":
            from .pm import apply_pm_mode, exit_pm_mode
            if not self._pm_mode:
                self._pm_mode = True
                self._pm_messages = []
                return [apply_pm_mode(self._agent)]
            self._pm_mode = False
            return [exit_pm_mode(self._agent)]
        # PM steps (only meaningful inside PM mode); the text after the command
        # (e.g. "/vision 我的产品给大学生") is passed through as the user's message.
        if cmd[1:] in _PM_STEP_COMMANDS:
            if not self._pm_mode:
                return [f"[pm:{cmd[1:]}] not in PM mode — run /pm first."]
            from .pm import pm_step
            self._pm_messages, out = pm_step(self._agent, self._pm_messages,
                                             self._config.workdir, cmd[1:], arg.strip())
            return out
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
            return self._resume(arg)
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
        if cmd == "/undo":
            return self._undo()
        if cmd == "/redo":
            return self._redo()
        if cmd == "/explore":
            return self._explore()
        if cmd == "/codemap":
            try:
                from .repomap import code_map
                m = code_map(self._config.workdir, max_chars=self._config.code_map_chars)
                return [f"[codemap] {len(m)} chars", m[:1500]]
            except Exception as exc:
                return [f"[codemap] failed: {exc}"]
        if cmd == "/skills":
            try:
                from .skills import discover_skills
                skills = discover_skills(self._config.workdir)
                if not skills:
                    return ["(no skills found — add a skills/<name>/SKILL.md)"]
                return ["Available skills:"] + [f"  - {s['name']}: {s['description']}" for s in skills]
            except Exception as exc:
                return [f"[skills] failed: {exc}"]
        if cmd == "/skill":
            name = arg.strip()
            if not name:
                return ["usage: /skill <name>"]
            try:
                from .skills import load_skill
                body = load_skill(self._config.workdir, name)
                if body is None:
                    return [f"no skill named '{name}'"]
                self._messages.append({"role": "user", "content": f"[skill:{name}] loaded\n{body}"})
                return [f"[skill] loaded '{name}' ({len(body)} chars) into context", body[:1000]]
            except Exception as exc:
                return [f"[skill] failed: {exc}"]
        if cmd == "/plan":
            return self._plan()
        if cmd == "/permissions":
            return self._permissions(arg)
        return [f"unknown command: {cmd}. Available: {', '.join('/' + c for c in COMMANDS)}"]

    # ------------------------------------------------------------- P2: review

    def _explore(self) -> list[str]:
        """Run the cheap read-only explore subagent and inject the brief into context."""
        from .multi import brief_block, run_explore

        try:
            brief = run_explore(self._config, "Explore this repository so we can plan the current work.")
            self._messages.append({"role": "user", "content": brief_block(brief) + "\n\n" + brief})
            return [f"[explore] project brief ({len(brief)} chars) added to context:", brief[:1200]]
        except Exception as exc:
            return [f"[explore] failed: {exc}"]

    def _plan(self) -> list[str]:
        """Explore the repo with a cheap subagent, then plan a todo list (/plan)."""
        from .multi import run_explore, run_planner

        try:
            brief = run_explore(self._config, "Explore this repository so we can plan the current work.")
            todos = run_planner(self._config, "Plan the current work.", brief)
            self._todos = todos
            return ["[plan] todo list updated:", *[f"{i}. {t}" for i, t in enumerate(todos, start=1)],
                    "[plan] brief:", brief[:600]]
        except Exception as exc:
            return [f"[plan] failed: {exc}"]

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

    def _resume(self, arg: str) -> list[str]:
        """Resume a saved session.

        `/resume`          -> list sessions with a number so the user can pick one.
        `/resume <n>`      -> resume the n-th listed session.
        `/resume <name>`   -> resume a session by its exact id (legacy).
        """
        sessions = list_sessions(self._config.workdir)
        if not sessions:
            return ["no saved sessions (use /save to persist the current one)"]
        # numbered selection: ask which one, listing newest-first like /ls
        if not arg.strip():
            lines = ["saved sessions — type /resume <number> to load one:"]
            lines += [
                f"  {i}. {s.id}  updated={s.updated_at:.0f}  messages={len(s.messages)}  model={s.model}"
                for i, s in enumerate(sessions, start=1)
            ]
            lines.append("or /resume <id> to load by exact id.")
            return lines
        sel = arg.strip()
        # a bare integer -> index into the numbered list (1-based)
        if sel.isdigit():
            idx = int(sel)
            if not (1 <= idx <= len(sessions)):
                return [f"invalid number: {sel} (1..{len(sessions)})"]
            return self._apply_session(sessions[idx - 1])
        # otherwise treat it as an exact session id
        try:
            saved = load_session(self._config.workdir, sel)
        except FileNotFoundError as exc:
            return [str(exc)]
        return self._apply_session(saved)

    def _apply_session(self, saved: Session) -> list[str]:
        """Restore a saved session: messages, model, stats; rebuild agent if workdir changed."""
        saved_wd = Path(saved.workdir)
        if saved_wd != self._config.workdir:
            self._config = replace(self._config, workdir=saved_wd)
        self._agent = CodingAgent(self._config, llm=self._llm, model=saved.model,
                                  trace=self._trace, tools=self._tools)
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
