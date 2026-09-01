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


def read_interactive_line(prompt: str, on_slash, _read_char=None,
                          erase_on_enter: bool = False,
                          _has_pending=None) -> str | None:
    """Interactive line editor (Windows TTY) — prompts + slash-completion menu.

    This is a full "redraw" editor like prompt_toolkit/OpenCode, not a print-and-
    leave one. We keep a small screen state (the edited text and whether a
    completion menu is showing) and after EVERY keypress re-render from a known
    origin, so the menu can grow/shrink/close without leaving stale lines behind.

    TYPING '/': '/' is echoed as a real input character, and a completion menu of
    slash commands appears UNDER the input line. The menu is a candidate list
    (not a one-shot print): it appears while '/' is the leading char and
    disappears the moment '/' is backspaced (or the line is submitted), because
    each redraw only draws the menu when '/' is present. This is how TUI menus
    stay deletable — the editor owns the whole screen it drew.

    `on_slash(text)` is called on every redraw while the menu is active and
    returns the candidate commands to display (a list of strings). When '/' is
    removed or the line submitted it is not called with an active menu, so the
    caller can skip its work; it may also signal "no menu" by returning [].

    Falls back to plain `input()` on non-Windows / non-TTY stdin. Returns the
    line, or None on EOF.

    PASTE HANDLING: a multi-line paste (e.g. a task doc copied out of TASK.md)
    must NOT be split into one submission per line. When the user hits Enter the
    Windows console may also deliver a trailing '\r'/'\n' from the clipboard,
    so we distinguish a "paste burst" from a real submit:
      - '\n' is NEVER a submit — it is always collected as part of the input.
      - '\r' submits ONLY when no more input is pending (_has_pending() is
        False, i.e. the buffer is empty). Otherwise the '\r' is a paste line
        break and is collected as a newline (swallowing a following '\n' so a
        '\r\n' paste becomes a single '\n').
    """
    if os.name != "nt" or not sys.stdin.isatty():
        try:
            return input(prompt)
        except EOFError:
            return None

    import msvcrt as _msvcrt

    reader = _read_char or _msvcrt.getwch
    has_pending = _has_pending if _has_pending is not None else _msvcrt.kbhit
    chars: list[str] = []

    # one-char lookahead so we can decide on a '\r' whether a '\n' follows (a
    # paste CRLF) vs. this is a real Enter (no following char).
    lookahead: list[str] = []

    def _next_char() -> str:
        if lookahead:
            return lookahead.pop(0)
        return reader()

    def _peek_char() -> str | None:
        """Return the next input char without consuming it, or None if the input
        is empty (a real Enter follows). During a paste a CRLF pair's '\n' lands
        right after '\r', so we briefly wait for it instead of trusting a single
        instant kbhit() (which can flicker to False mid-paste)."""
        if not lookahead:
            import time as _time
            for _ in range(6):  # up to ~12ms for the CRLF's '\n' to arrive
                if has_pending():
                    break
                _time.sleep(0.002)
            if not has_pending():
                return None
            lookahead.append(reader())
        return lookahead[0]

    # screen state: how many lines the completion menu occupied last redraw
    menu_lines = 0
    menu_active = False

    def _menu_candidates() -> list[str]:
        """Current completion candidates, or [] when the menu shouldn't show."""
        text = "".join(chars)
        if not text.startswith("/") or "/" not in text[:1]:
            return []
        try:
            cands = on_slash(text[1:])  # caller segments on the substring after '/'
            return list(cands or [])
        except TypeError:
            return []  # on_slash() is a no-arg legacy callback

    def _render() -> None:
        """Redraw the prompt line + completion menu from a stable origin.

        The cursor is always left at the END of the input line after a render
        (right after the text), so typing/backspace edits at the prompt, never on
        the menu. Since the menu sits BELOW the input line, a '\r\x1b[J'
        (clear-from-cursor-to-end) wipes any previously drawn menu.
        """
        nonlocal menu_lines, menu_active
        # 1. back to the start of the input line and clear it + everything below
        #    (this erases the previous frame's menu if one was drawn)
        sys.stdout.write("\r\x1b[J")
        # 2. draw the prompt + edited text
        text = "".join(chars)
        sys.stdout.write(prompt + text)
        # 3. if a menu is active, draw it under the input line; then return the
        #    cursor to the input line so the next keystroke edits right after '/'
        cands = _menu_candidates()
        if cands:
            menu_active = True
            sys.stdout.write("\n")
            sys.stdout.write("\n".join(f"  {c}" for c in cands))
            menu_lines = 1 + len(cands)
            if menu_lines > 1:
                sys.stdout.write(f"\x1b[{menu_lines - 1}A")
        else:
            menu_active = False
            menu_lines = 0
        sys.stdout.flush()

    # initial render
    _render()

    while True:
        ch = _next_char()
        if ch == "\n":
            # A lone '\n' is a paste line break, never a submit: collect it.
            chars.append("\n")
            _render()
            continue
        if ch == "\r":
            # A '\r' that is immediately followed by a '\n' is a paste CRLF line
            # break (not a submit): collect a single '\n'.
            if _peek_char() == "\n":
                lookahead.pop(0)
                chars.append("\n")
                _render()
                continue
            # Otherwise this is a real Enter. Submit the collected input line.
            # The cursor is already on the input line; clear it + the menu below.
            sys.stdout.write("\r\x1b[J")
            line = "".join(chars)
            if erase_on_enter and not line.startswith("/") and "\n" not in line:
                # The caller re-renders this as a chat bubble in the SAME spot;
                # erase the echoed prompt line so the input is shown only ONCE
                # (replaces the inline echo instead of duplicating it below).
                sys.stdout.write("\r\x1b[2K")
                sys.stdout.flush()
            else:
                sys.stdout.write("\n")
                sys.stdout.flush()
            return line
        if ch == "\x03":  # Ctrl+C
            raise KeyboardInterrupt
        if ch in ("\x08", "\x7f"):  # Backspace
            if chars:
                chars.pop()
                _render()  # re-draw; '/' removed -> menu closes automatically
            continue
        if not chars and ch == "/":
            # First char is '/': echo it; the redraw shows the completion menu.
            chars.append("/")
            _render()
            continue
        if menu_active and chars == ["/"] and ch == "/":
            # The '/' that opened the menu is already the command slash; typing
            # another '/' (e.g. "/pm") must NOT produce a double slash. Keep the
            # one we have; the rest of the command is typed after it.
            continue
        chars.append(ch)
        _render()
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
    from .repl import C_PROMPT, C_RESET, COMMANDS, ReplSession

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
                # Windows interactive: typing '/' as the first char opens the menu.
                # erase_on_enter: the caller re-renders the line as a chat bubble
                # in-place, so erase the echoed prompt line (input shown once).
                def _on_slash(prefix: str = "") -> list[str]:
                    # Completion candidates for the substring after '/' (e.g.
                    # '/p' -> 'pm', 'permissions'...); empty prefix = all.
                    import re as _re
                    p = (prefix or "").lower()
                    cands = [c for c in COMMANDS if c.startswith(p)]
                    # show them as '/' + name so "/p" lists "/pm", "/permissions"
                    return ["/" + c for c in cands]

                line = read_interactive_line(f"{C_PROMPT}❯{C_RESET} ", on_slash=_on_slash,
                                             erase_on_enter=True)
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
