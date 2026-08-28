"""CLI entrypoint (`coding-agent`).

Workspace selection (like other coding agents — launch inside your project):
  * `cd <your-project> && coding-agent chat`  -> workdir = <your-project>
  * `coding-agent chat --workdir <path>`      -> explicit workspace from anywhere
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .config import Config


def apply_workdir(cfg: Config, workdir: str | None) -> Config:
    """Override the workdir from a --workdir flag (absolute, resolved)."""
    if not workdir:
        return cfg
    return replace(cfg, workdir=Path(workdir).resolve())


def _cmd_config(_args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    print(f"model={cfg.model}  base_url={cfg.base_url}  workdir={cfg.workdir}")
    print(f"max_steps={cfg.max_steps}  max_tool_calls={cfg.max_tool_calls}")
    return 0


def _parse_tools(raw: str | None) -> list[str] | None:
    """Parse a comma-separated --tools value into a list (E1/P2)."""
    if not raw:
        return None
    tools = [t.strip() for t in raw.split(",") if t.strip()]
    return tools or None


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = apply_workdir(Config.from_env(), args.workdir)
    from .loop import CodingAgent

    answer = CodingAgent(cfg, model=args.model, tools=_parse_tools(args.tools)).run(args.task)
    print(answer)
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    cfg = apply_workdir(Config.from_env(), args.workdir)
    from .repl import ReplSession

    session = ReplSession(cfg, model=args.model, trace=args.trace, tools=_parse_tools(args.tools))
    print(f"coding-agent chat — model={session._agent.model} workdir={cfg.workdir}  (type /help)")
    for line in sys.stdin:
        for out in session.handle(line):
            print(out, flush=True)
        if not session.running:
            break
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coding-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("config", help="print resolved configuration").set_defaults(func=_cmd_config)
    run = sub.add_parser("run", help="run the agent on a task")
    run.add_argument("task", help="the coding task to complete")
    run.add_argument("--model", default=None, help="override the model tier (e.g. deepseek-v4-pro)")
    run.add_argument("--tools", default=None, help="comma-separated tool whitelist, e.g. read_file,edit_file")
    run.add_argument("--workdir", default=None, help="workspace directory (default: current directory)")
    run.set_defaults(func=_cmd_run)
    chat = sub.add_parser("chat", help="start an interactive session (slash commands: /help /compact /status ...)")
    chat.add_argument("--model", default=None, help="override the model tier")
    chat.add_argument("--trace", action="store_true", help="print each agent step")
    chat.add_argument("--tools", default=None, help="comma-separated tool whitelist, e.g. read_file,edit_file")
    chat.add_argument("--workdir", default=None, help="workspace directory (default: current directory)")
    chat.set_defaults(func=_cmd_chat)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
