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
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=_ok("## Problem\n...\n## Payoff\n..."))
    sess.run_step("story", "")
    assert (tmp_path / "demo" / ARTIFACTS["story"]).exists()


def test_p4_pitch_writes_pitch(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=_ok("## Value prop\n...\n## Next steps\n..."))
    sess.run_step("pitch", "")
    assert (tmp_path / "demo" / ARTIFACTS["pitch"]).exists()


def test_p5_mvp_creates_runnable_demo_dir(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=_ok("created demo/app.py\nREADME in demo/"))
    out = sess.run_step("mvp", "")
    # mvp should at least create the demo dir / be runnable-oriented
    assert (tmp_path / "demo").is_dir()
    assert isinstance(out, list)


def test_p6_unknown_step_and_turn(tmp_path):
    sess = PmSession.create(Config(api_key="x", workdir=tmp_path), llm=_ok("a normal PM reply"))
    assert "unknown" in sess.run_step("nope", "")[0]
    assert sess.turn("describe my idea") == ["a normal PM reply"]
    assert sess.run_step("vision", ""), "step runs normally after a turn"
