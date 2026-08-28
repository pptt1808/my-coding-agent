"""Interactive REPL (specs/cli.md R1-R8, A1/P0).

`coding-agent chat` turns the one-shot CLI into a conversational session:
plain lines are sent to the agent as new turns (shared history), `/`-prefixed
lines are session-control slash commands. All logic is self-built — no
frameworks, per the assignment rules.
"""
from __future__ import annotations

from typing import Any

from .config import Config
from .llm import LLMClient
from .loop import CodingAgent

HELP = """slash commands:
  /help            show this help
  /exit            quit the session
  /clear           reset conversation history
  /compact         compress the conversation into an LLM summary
  /status          show model, workdir, steps, tokens, message count
  /model <name>    switch model tier (e.g. deepseek-v4-pro)
Anything else is sent to the agent as a new turn."""


class ReplSession:
    """One interactive session: keeps the conversation between turns."""

    def __init__(self, config: Config, llm: LLMClient | None = None, model: str | None = None,
                 trace: bool = False) -> None:
        self._config = config
        self._agent = CodingAgent(config, llm=llm, model=model, trace=trace)
        self._messages: list[dict[str, Any]] = []
        self.running = True

    def handle(self, line: str) -> list[str]:
        """Process one input line; returns lines to print (R1/R3-R8)."""
        line = line.strip()
        if not line:
            return []
        if line.startswith("/"):
            return self._slash(line)
        return self._turn(line)

    def _turn(self, line: str) -> list[str]:
        self._messages.append({"role": "user", "content": line})
        answer, self._messages = self._agent.run_turn(self._messages)
        return [answer]

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
                f"messages={len(self._messages)}"
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
        return [f"unknown command: {cmd}. Type /help for usage."]
