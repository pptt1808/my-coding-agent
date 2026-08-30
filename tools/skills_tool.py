"""Skill tool: the model invokes `Skill(name=...)` to load a skill's instructions."""
from __future__ import annotations

from tools import context


def skill(name: str) -> str:
    """Load a skill package's SKILL.md body by name (discovery comes from the catalog)."""
    from agent.skills import load_skill

    body = load_skill(context.workdir(), name)
    if body is None:
        return f"Error: no skill named '{name}'"
    return f"[skill:{name}]\n{body}"
