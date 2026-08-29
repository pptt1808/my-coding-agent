"""Contract tests for specs/pm-mode.md — P1-P6.

Uses a scripted FakeLLM (no network). The PM mode is our own synthesis; tests
check the persona, the artifact-writing steps, and the guardrails.
"""
from __future__ import annotations

import pytest

from agent.config import Config
from agent.llm import LLMResult
from agent.pm import ARTIFACTS, PM_PERSONA, STEPS, PmSession


def _ok(text):
    class Fake:
        def complete(self, _sys, _messages, _tools=None):
            return LLMResult(text=text, usage={"total_tokens": 1})

        stream_complete = None
    return Fake()


def test_p1_persona_has_pm_keywords():
    p = PM_PERSONA
    for kw in ("PRODUCT-MANAGER", "audience", "MVP", "WOW-moment", "over-engineering", "demo"):
        assert kw.lower() in p.lower(), f"missing {kw}"


def test_p2_vision_writes_spec(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path),
                            llm=_ok("# DEMO SPEC\n## Vision\nA demo tracker\n## Audience\nPMs\n## Demo moment\nx"))
    out = sess.run_step("vision", "")
    spec = tmp_path / "demo" / ARTIFACTS["vision"]
    assert spec.exists()
    content = spec.read_text(encoding="utf-8")
    assert "Vision" in content
    assert any("DEMO_SPEC" in line for line in out) or any("DEMO_SPEC" in line for line in out)


def test_p3_story_writes_script(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path),
                            llm=_ok("## Problem\n...\n## Payoff\n..."))
    sess.run_step("vision", "")  # gated: spec must exist first
    sess.run_step("story", "")
    assert (tmp_path / "demo" / ARTIFACTS["story"]).exists()


def test_p4_pitch_writes_pitch(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path),
                            llm=_ok("## Value prop\n...\n## Next steps\n..."))
    sess.run_step("vision", "")  # gated: spec must exist first
    sess.run_step("pitch", "")
    assert (tmp_path / "demo" / ARTIFACTS["pitch"]).exists()


def test_p5_mvp_creates_runnable_demo_dir(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=_ok("created demo/app.py\nREADME in demo/"))
    out = sess.run_step("mvp", "")  # NO spec -> gate refuses
    assert "gate refused" in out[0] or "vision" in out[0]  # must align first
    sess.run_step("vision", "")
    out2 = sess.run_step("mvp", "")  # spec exists now; persona may still build
    assert "gate refused" not in out2[0]
    assert (tmp_path / "demo").is_dir()
    assert isinstance(out2, list)


def test_p6_unknown_step_and_turn(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=_ok("a normal PM reply"))
    assert "unknown" in sess.run_step("nope", "")[0]
    assert sess.turn("describe my idea") == ["a normal PM reply"]
    assert sess.run_step("vision", ""), "step runs normally after a turn"


def test_p7_meta_reply_triggers_forced_rewrite(tmp_path):
    """If a step replies with meta, we force a clean artifact-only rewrite."""
    class SequenceLLM:
        def __init__(self, replies):
            self.replies = list(replies)

        def complete(self, _sys, _messages, _tools=None):
            return LLMResult(text=self.replies.pop(0), usage={"total_tokens": 1})

    sess = PmSession.create(Config(api_key="x", workdir=tmp_path),
                            llm=SequenceLLM(["## Spec\nClean spec body.",
                                             "All set, nothing new needed. 👍",
                                             "## Story\nClean 30s narrative."]))
    sess.run_step("vision", "")  # vision writes clean spec so the story gate passes
    sess.run_step("story", "")
    content = (tmp_path / "demo" / ARTIFACTS["story"]).read_text(encoding="utf-8")
    assert content.startswith("## Story")  # the clean (rewritten) content, not the meta
    assert "All set" not in content


def test_p8_clean_reply_no_rewrite(tmp_path):
    """A clean artifact reply is used as-is (no extra write)."""
    class OnceLLM:
        def __init__(self):
            self.calls = 0

        def complete(self, _sys, _messages, _tools=None):
            self.calls += 1
            return LLMResult(text="## Pitch\nClean pitch body.", usage={"total_tokens": 1})

    llm = OnceLLM()
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=llm)
    sess.run_step("vision", "")
    sess.run_step("pitch", "")
    assert llm.calls == 2  # one call per step, no rewrite for clean replies
