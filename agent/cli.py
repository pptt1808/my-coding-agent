"""CLI entrypoint (`coding-agent`). Phase 1 wires real behavior.

Currently only loads config and echoes the resolved settings so Phase 0 is
runnable/verifiable end-to-end.
"""
from __future__ import annotations

import argparse
import sys

from .config import Config


def _cmd_config(_args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    print(f"model={cfg.model}  base_url={cfg.base_url}  workdir={cfg.workdir}")
    print(f"max_steps={cfg.max_steps}  max_tool_calls={cfg.max_tool_calls}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = Config.from_env()
    from .loop import CodingAgent

    answer = CodingAgent(cfg, model=args.model).run(args.task)
    print(answer)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coding-agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("config", help="print resolved configuration").set_defaults(func=_cmd_config)
    run = sub.add_parser("run", help="run the agent on a task")
    run.add_argument("task", help="the coding task to complete")
    run.add_argument("--model", default=None, help="override the model tier (e.g. deepseek-v4-pro)")
    run.set_defaults(func=_cmd_run)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
