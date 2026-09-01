"""Contract tests for specs/cli.md — R1-R8 (interactive REPL + slash commands).

Uses a scripted FakeLLM (no network). Written BEFORE implementation (RED).
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult, ToolCall
from agent.repl import ReplSession


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    def complete(self, system_prompt, messages, tools=None):
        self.calls.append(list(messages))
        return LLMResult(text="ok", usage={"total_tokens": 5})


@pytest.fixture
def session():
    fake = FakeLLM()
    sess = ReplSession(Config(api_key="x"), llm=fake)
    return sess, fake


def test_r1_plain_line_runs_turn_and_returns_answer(session):
    sess, _ = session
    assert sess.handle("do something") == ["ok"]


def test_r2_consecutive_turns_share_history(session):
    sess, fake = session
    sess.handle("first task")
    sess.handle("second task")
    assert fake.calls[1][0]["content"] == "first task"  # history carries over
    assert fake.calls[1][-1]["content"] == "second task"  # new turn appended


def test_r3_exit_stops_session(session):
    sess, _ = session
    sess.handle("/exit")
    assert sess.running is False


def test_r4_clear_resets_history(session):
    sess, fake = session
    sess.handle("first task")
    sess.handle("/clear")
    sess.handle("fresh start")
    last_messages = fake.calls[-1]
    assert len(last_messages) == 1
    assert last_messages[0]["content"] == "fresh start"


def test_r5_status_shows_model_and_tokens(session):
    sess, _ = session
    sess.handle("work")
    lines = sess.handle("/status")
    text = "\n".join(lines)
    assert "model=" in text
    assert "tokens=" in text
    assert "steps=" in text


def test_r6_compact_replaces_history_with_summary(session):
    sess, fake = session
    sess.handle("do the bug fix")
    sess.handle("/compact")
    sess.handle("continue")
    first_content = fake.calls[-1][0]["content"]
    assert "[compacted conversation]" in first_content or "compacted" in first_content


def test_r7_unknown_command_help_no_crash(session):
    sess, _ = session
    lines = sess.handle("/bogus")
    assert any("/help" in line for line in lines)


def test_r8_model_switch_shown_in_status(session):
    sess, _ = session
    sess.handle("/model deepseek-v4-pro")
    text = "\n".join(sess.handle("/status"))
    assert "deepseek-v4-pro" in text


def test_r9_save_and_resume_restores_history(tmp_path):
    fake = FakeLLM()
    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    sess.handle("first task")
    lines = sess.handle("/save my-session")
    assert any("my-session" in line for line in lines)
    sess2 = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    sess2.handle("/resume my-session")
    sess2.handle("second task")
    assert fake.calls[-1][0]["content"] == "first task"  # resumed history carried over
    assert fake.calls[-1][-1]["content"] == "second task"


def test_r9b_resume_no_arg_lists_sessions_numbered(tmp_path):
    fake = FakeLLM()
    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    sess.handle("first task")
    sess.handle("/save alpha")
    sess.handle("/clear")  # drop in-memory history so only the saved one matters
    sess2 = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    lines = sess2.handle("/resume")
    text = "\n".join(lines)
    assert "alpha" in text          # lists the saved session
    assert "1." in text             # numbered so the user can pick
    # picking by number resumes it
    sess2.handle("/resume 1")
    sess2.handle("second task")
    assert fake.calls[-1][0]["content"] == "first task"  # resumed history carried over


def test_r9c_resume_out_of_range_number(tmp_path):
    fake = FakeLLM()
    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    sess.handle("/save only")
    sess2 = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    text = "\n".join(sess2.handle("/resume 9"))
    assert "invalid number" in text


def test_r9d_resume_no_sessions(tmp_path):
    fake = FakeLLM()
    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=fake)
    text = "\n".join(sess.handle("/resume"))
    assert "no saved sessions" in text


def test_r10_cost_shows_token_split(session):
    sess, _ = session
    sess.handle("work")
    text = "\n".join(sess.handle("/cost"))
    assert "input" in text and "output" in text and "total" in text


def test_r11_streaming_prints_deltas_and_no_duplicate(capsys, tmp_path):
    class StreamingFake:
        def complete(self, _sys, _messages, _tools=None):
            return LLMResult(text="plain", usage={"total_tokens": 1})

        def stream_complete(self, _sys, _messages, _tools=None, on_delta=None):
            if on_delta:
                on_delta("hel")
                on_delta("lo")
            return LLMResult(text="hello", usage={"total_tokens": 1})

    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=StreamingFake(), stream=True)
    out = sess.handle("hi")
    assert out == []  # streamed: no duplicate final print
    captured = capsys.readouterr().out
    assert captured.strip() == "hello"  # deltas printed live + trailing newline


def test_r12_slash_alone_shows_menu(session):
    sess, _ = session
    lines = sess.handle("/")
    text = "\n".join(lines)
    assert "/compact" in text and "/status" in text and "/task" in text


def test_r12b_prefix_expansion(session):
    sess, _ = session
    lines = sess.handle("/sta")
    text = "\n".join(lines)
    assert "model=" in text  # expanded to /status


def test_r12c_unknown_prefix_lists_commands(session):
    sess, _ = session
    lines = sess.handle("/zzz")
    text = "\n".join(lines)
    assert "unknown" in text
    assert "/compact" in text  # available commands listed


def test_r12d_fullwidth_slash_shows_menu(session):
    """CJK IMEs often emit U+FF0F; it must behave like '/'."""
    sess, _ = session
    text = "\n".join(sess.handle("／"))
    assert "/compact" in text and "/status" in text


def test_r12e_fullwidth_slash_command_works(session):
    sess, _ = session
    sess.handle("／exit")
    assert sess.running is False


def test_r12f_double_slash_is_collapsed(session):
    """Regression: a stray leading '//' must be collapsed to '/' so it routes
    as a command instead of "unknown command: //pm"."""
    sess, _ = session
    # '//exit' and '///exit' both behave like '/exit'
    for line in ("//exit", "///exit"):
        s = ReplSession(Config(api_key="x", workdir=sess._config.workdir), llm=sess._llm, stream=False)
        s.handle(line)
        assert s.running is False


def test_r13_echo_input_renders_chat_box(capsys, tmp_path):
    class Fake:
        def complete(self, _sys, _messages, _tools=None):
            return LLMResult(text="ok", usage={"total_tokens": 1})

    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=Fake(),
                       stream=False, echo_input=True)
    lines = sess.handle("修复这个 bug")
    assert lines == ["ok"]
    captured = capsys.readouterr().out
    assert "┌" in captured and "└" in captured  # chat box drawn
    assert "修复这个 bug" in captured  # input echoed inside the box


def test_r13b_echo_input_off_by_default(capsys, tmp_path):
    class Fake:
        def complete(self, _sys, _messages, _tools=None):
            return LLMResult(text="ok", usage={"total_tokens": 1})

    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=Fake(), stream=False)
    sess.handle("hello")
    captured = capsys.readouterr().out
    assert "┌" not in captured


def test_r14_ctrl_c_mid_turn_restores_history(tmp_path):
    import pytest as _pytest

    class OkLLM:
        def complete(self, _sys, _messages, _tools=None):
            return LLMResult(text="ok", usage={"total_tokens": 1})

    class InterruptingLLM:
        def complete(self, _sys, _messages, _tools=None):
            raise KeyboardInterrupt

    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=OkLLM(), stream=False)
    sess.handle("hello")
    before = list(sess._messages)

    sess._agent._llm = InterruptingLLM()  # simulate Ctrl+C during a turn
    with _pytest.raises(KeyboardInterrupt):
        sess.handle("explode")
    assert sess._messages == before  # interrupted turn fully rolled back

    sess._agent._llm = OkLLM()
    assert sess.handle("again") == ["ok"]  # session still usable


# --------------------------- undo / redo (specs/cli.md U1-U4) ---------------------------

class EditingLLM:
    """Writes a file each turn (no final answer) — simulates the agent editing the workdir."""

    def __init__(self, path, content):
        self.path = path
        self.content = content

    def complete(self, _sys, _messages, _tools=None):
        return LLMResult(text="", tool_calls=[ToolCall("c1", "write_file",
                                                       {"path": self.path, "content": self.content})],
                         usage={"total_tokens": 1})


def _sess(tmp_path, llm):
    return ReplSession(Config(api_key="x", workdir=tmp_path, max_steps=3), llm=llm, stream=False)


def test_u1_undo_reverts_file_change(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    sess = _sess(tmp_path, EditingLLM("a.py", "x = 2\n"))
    sess.handle("change a.py")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "x = 2\n"
    sess.handle("/undo")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "x = 1\n"


def test_u2_redo_reapplies_change(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    sess = _sess(tmp_path, EditingLLM("a.py", "x = 2\n"))
    sess.handle("change a.py")
    sess.handle("/undo")
    sess.handle("/redo")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "x = 2\n"


def test_u3_multiple_undos(tmp_path):
    (tmp_path / "a.py").write_text("v0\n", encoding="utf-8")
    sess = _sess(tmp_path, EditingLLM("a.py", "v1\n"))
    sess.handle("one")
    sess._agent._llm = EditingLLM("a.py", "v2\n")
    sess.handle("two")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "v2\n"
    sess.handle("/undo")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "v1\n"  # back to after turn 1
    sess.handle("/undo")
    assert (tmp_path / "a.py").read_text(encoding="utf-8") == "v0\n"  # back to original


def test_u4_undo_removes_new_file(tmp_path):
    (tmp_path / "a.py").write_text("ok\n", encoding="utf-8")
    sess = _sess(tmp_path, EditingLLM("new.txt", "runtime\n"))
    sess.handle("create new.txt")
    assert (tmp_path / "new.txt").exists()
    sess.handle("/undo")
    assert not (tmp_path / "new.txt").exists()  # created file reverted


def test_pm_mode_toggles_within_same_session(tmp_path):
    """PM mode is a mode of the SAME agent, activated by /pm (not a separate agent)."""
    class FakePMLLM:
        def complete(self, _sys, _messages, _tools=None):
            return LLMResult(text="# DEMO_SPEC.md\n## Vision\nA demo\n## Acceptance\npass", usage={"total_tokens": 1})

    sess = ReplSession(Config(api_key="x", workdir=tmp_path), llm=FakePMLLM(), stream=False)
    out = sess.handle("/pm")
    assert any("PM mode on" in line for line in out)  # enters PM mode
    assert sess._pm_mode is True
    sess.handle("/vision")  # a PM step, still the same session
    assert (tmp_path / "demo" / "DEMO_SPEC.md").exists()
    out2 = sess.handle("/pm")
    assert any("normal" in line for line in out2)  # back to normal mode
    assert sess._pm_mode is False
