"""Skill system (specs/skills.md) — Claude Agent Skills-style, self-built.

A skill is a reusable capability package: `skills/<name>/SKILL.md` with YAML
frontmatter (name, description) + a concise markdown body (instructions/recipe).
The agent (a) sees a catalog of available skills (discovery) and (b) can load a
skill's instructions on demand (invoke) to guide it on that kind of task.

Reference: Claude Agent Skills (code.claude.com/docs/en/agent-sdk/skills),
OpenCode agent-skills.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_SKILLS_DIR = "skills"  # <workdir>/skills
GLOBAL_SKILLS_DIR = "~/.coding-agent/skills"


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split YAML frontmatter (--- ... ---) from the body. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm = text[3:end].strip()
    body = text[end + 3:].strip()
    meta: dict[str, str] = {}
    for line in fm.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip().lower()] = v.strip().strip("\"'")
    return meta, body


def _skills_root(workdir: Path | str) -> list[Path]:
    roots = [Path(workdir) / DEFAULT_SKILLS_DIR, Path(GLOBAL_SKILLS_DIR).expanduser()]
    return [r for r in roots if r.is_dir()]


def discover_skills(workdir: Path | str) -> list[dict[str, Any]]:
    """Return the skill catalog: [{name, description, path, dir}]."""
    skills: list[dict[str, Any]] = []
    for root in _skills_root(workdir):
        for skill_dir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            smd = skill_dir / "SKILL.md"
            if smd.exists():
                meta, _ = _parse_frontmatter(smd.read_text(encoding="utf-8", errors="replace"))
                name = meta.get("name", skill_dir.name)
                skills.append({"name": name, "description": meta.get("description", ""),
                               "path": str(smd), "dir": str(skill_dir)})
    return skills


def load_skill(workdir: Path | str, name: str) -> str | None:
    """Load a skill's instructions (SKILL.md body) by name; None if not found."""
    for s in discover_skills(workdir):
        if s["name"].lower() == name.lower():
            text = Path(s["path"]).read_text(encoding="utf-8", errors="replace")
            _meta, body = _parse_frontmatter(text)
            return body
    return None


def skills_catalog_block(workdir: Path | str) -> str:
    """A context block listing available skills (discovery)."""
    skills = discover_skills(workdir)
    if not skills:
        return ""
    lines = ["Available skills (call `Skill` with the name to load one):"]
    for s in skills:
        lines.append(f"  - {s['name']}: {s['description']}")
    return "\n".join(lines)
