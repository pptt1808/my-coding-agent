"""Contract tests for specs/skills.md — S1-S5."""
from __future__ import annotations

import pytest

from agent.skills import discover_skills, load_skill, skills_catalog_block


def _make_skill(root, name, desc, body):
    d = root / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n{body}\n", encoding="utf-8")
    return root


def test_s1_discover_parses_frontmatter(tmp_path):
    _make_skill(tmp_path, "jtbd", "Clarify the user's real need.", "Ask one question.")
    skills = discover_skills(tmp_path)
    assert any(s["name"] == "jtbd" and "Clarify" in s["description"] for s in skills)


def test_s2_load_skill_by_name(tmp_path):
    _make_skill(tmp_path, "demo", "Make a quick demo.", "## Steps\n1. scaffold\n2. run")
    body = load_skill(tmp_path, "demo")
    assert body is not None and "scaffold" in body
    assert load_skill(tmp_path, "nope") is None


def test_s3_catalog_block_lists_skills(tmp_path):
    _make_skill(tmp_path, "jtbd", "Clarify need.", "body")
    block = skills_catalog_block(tmp_path)
    assert "Available skills" in block
    assert "jtbd" in block


def test_s4_skill_tool_hit_and_miss(tmp_path):
    _make_skill(tmp_path, "jtbd", "Clarify need.", "Ask about the job.")
    from tools import context
    from tools.skills_tool import skill

    context.configure(workdir=tmp_path)
    assert "jtbd" in skill("jtbd").lower()
    assert "Error" in skill("ghost")  # miss -> error, no crash


def test_s5_no_skills_dir(tmp_path):
    assert discover_skills(tmp_path) == []
    assert skills_catalog_block(tmp_path) == ""
