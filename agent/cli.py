"""CLI entrypoint (`coding-agent`).

Workspace selection (like other coding agents — launch inside your project):
  * `cd <your-project> && coding-agent chat`  -> workdir = <your-project>
  * `coding-agent chat --workdir <path>`      -> explicit workspace from anywhere
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

from .config import Config


def apply_workdir(cfg: Config, workdir: str | None) -> Config:
    """Override the workdir from a --workdir flag (absolute, resolved)."""
    if not workdir:
        return cfg
    return replace(cfg, workdir=Path(workdir).resolve())


def read_interactive_line(prompt: str, on_slash, _read_char=None) -> str | None:
    """Interactive line editor (Windows TTY).

    Typing '/' as the FIRST character opens the command menu immediately (no
    Enter required) — like OpenCode/Claude Code. Subsequent typed characters
    complete the command, and Enter sends it (the leading '/' is re-added).
    Falls back to plain `input()` on non-Windows / non-TTY stdin.
    Returns the line, or None on EOF.
    """
    if os.name != "nt" or not sys.stdin.isatty():
        try:
            return input(prompt)
        except EOFError:
            return None

    import msvcrt as _msvcrt

    reader = _read_char or _msvcrt.getwch
    chars: list[str] = []
    slash_seen = False
    sys.stdout.write(prompt)
    sys.stdout.flush()
    while True:
        ch = reader()
        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return ("/" if slash_seen else "") + "".join(chars)
        if ch == "\x03":  # Ctrl+C
            raise KeyboardInterrupt
        if ch in ("\x08", "\x7f"):  # Backspace
            if chars:
                chars.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        if not chars and not slash_seen and ch == "/":
            slash_seen = True
            sys.stdout.write("\n")
            sys.stdout.flush()
            on_slash()  # print the command menu immediately
            sys.stdout.write(prompt)
            sys.stdout.flush()
            continue
        # Menu already opened (leading '/' was consumed) but the user typed
        # another '/' — e.g. "/pm" -> "/" then "/pm". That '/' is the real
        # command slash, so stop auto-prepending to avoid "//pm".
        if slash_seen and not chars and ch == "/":
            slash_seen = False
            chars.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
            continue
        chars.append(ch)
        sys.stdout.write(ch)
        sys.stdout.flush()
    return None


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

    stream = cfg.stream and not args.no_stream
    streamed: list[str] = []

    def _on_delta(text: str) -> None:
        streamed.append(text)
        print(text, end="", flush=True)

    explicit = (1 if args.explore else (-1 if args.no_explore else 0))
    try:
        from .multi import orchestrate

        def _on_brief(brief: str) -> None:
            print(f"[explore] project brief ({len(brief)} chars) gathered", flush=True)

        answer, _brief = orchestrate(cfg, args.task, explicit=explicit,
                                     stream=stream, on_delta=_on_delta, on_brief=_on_brief)
    except KeyboardInterrupt:
        print("\n(interrupted)", flush=True)
        return 130  # 128 + SIGINT (R14)
    if streamed:
        print()  # finish the line after streaming
    else:
        print(answer)
    return 0


def _cmd_chat(args: argparse.Namespace) -> int:
    cfg = apply_workdir(Config.from_env(), args.workdir)
    from .repl import C_PROMPT, C_RESET, HELP, ReplSession

    if os.name == "nt":
        os.system("")  # enable ANSI/VT output in Windows cmd/terminal
    for _stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # not a text stream / encoding unsupported

    session = ReplSession(cfg, model=args.model, trace=args.trace, tools=_parse_tools(args.tools),
                          stream=cfg.stream and not args.no_stream, echo_input=True)
    print(f"coding-agent chat — model={session._agent.model} workdir={cfg.workdir}  (type / for commands)")

    while session.running:
        try:
            if sys.stdin.isatty():
                # Windows interactive: typing '/' as the first char opens the menu
                line = read_interactive_line(f"{C_PROMPT}❯{C_RESET} ", on_slash=lambda: print(HELP))
                if line is None:
                    break
            else:
                line = sys.stdin.readline()
                if not line:
                    break
        except KeyboardInterrupt:
            print("bye.")
            return 0
        try:
            for out in session.handle(line):
                print(out, flush=True)
        except KeyboardInterrupt:
            # Ctrl+C mid-turn: cancel this turn, keep the session alive (R14)
            print("\n[cancelled]", flush=True)
    print("bye.")
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
    run.add_argument("--no-stream", action="store_true", help="disable token streaming output")
    run.add_argument("--explore", action="store_true", help="force the explore subagent (project brief)")
    run.add_argument("--no-explore", action="store_true", help="never spawn the explore subagent")
    run.set_defaults(func=_cmd_run)
    chat = sub.add_parser("chat", help="start an interactive session (slash commands: /help /compact /status ...)")
    chat.add_argument("--model", default=None, help="override the model tier")
    chat.add_argument("--trace", action="store_true", help="print each agent step")
    chat.add_argument("--tools", default=None, help="comma-separated tool whitelist, e.g. read_file,edit_file")
    chat.add_argument("--workdir", default=None, help="workspace directory (default: current directory)")
    chat.add_argument("--no-stream", action="store_true", help="disable token streaming output")
    chat.set_defaults(func=_cmd_chat)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
