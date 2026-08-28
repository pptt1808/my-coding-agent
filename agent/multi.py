"""Multi-agent orchestration (specs/multi-agent.md).

The primary constraint is the **launch timing** of the explore subagent: it is
NEVER spawned unless it is clearly worth it. `should_explore` is deterministic
and free (a single os.walk, no model call), defaults to OFF, and respects
explicit --explore / --no-explore overrides.

Pipeline: explore (cheap, read-only) -> brief -> implement (brief injected).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .config import Config
from .loop import CodingAgent
from .llm import LLMClient

EXPLORE_TOOLS = ["read_file", "list_dir", "glob", "grep"]  # read-only only

EXPLORE_PROMPT = (
    "You are a READ-ONLY codebase explorer working in: {workdir}\n"
    "Explore the repository to plan a change. Use only the read-only tools "
    "(read_file / list_dir / glob / grep). Do NOT modify any file.\n"
    "Return a concise project brief: directory structure, key files, where the "
    "relevant code lives, entry points, conventions, and anything suspicious. "
    "Keep it under a few hundred words."
)

# directories excluded from size stats (noise + secrets)
_SKIP = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules",
         ".coding-agent", ".idea", ".vscode", "build", "dist", ".env"}


@dataclass
class RepoStats:
    n_files: int = 0
    loc: int = 0
    top_level_modules: int = 0


def collect_repo_stats(workdir: Path | str) -> RepoStats:
    """One os.walk: file count, lines of code, top-level module dirs. Zero model calls."""
    root = Path(workdir)
    stats = RepoStats()
    top_dir_names = set()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in _SKIP for part in rel.parts):
            continue
        stats.n_files += 1
        try:
            stats.loc += sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
        except Exception:
            pass
        if len(rel.parts) > 1 and rel.parts[0] not in top_dir_names:
            top_dir_names.add(rel.parts[0])
    stats.top_level_modules = len(top_dir_names)
    return stats


def should_explore(config: Config, stats: RepoStats | None = None, explicit: int = 0) -> bool:
    """Decide whether to launch the explore subagent.

    `explicit`: +1 (--explore) forces on, -1 (--no-explore) forces off,
    0 = rely on config.auto_explore and (for 'auto') the repo size heuristics.
    """
    if explicit != 0:
        return explicit > 0
    if config.auto_explore == "always":
        return True
    if config.auto_explore == "off":
        return False
    # 'auto': only for large/complex repos — small repos never pay the overhead
    if stats is None:
        stats = collect_repo_stats(config.workdir)
    return (
        stats.n_files >= config.explore_min_files
        or stats.loc >= config.explore_min_loc
        or stats.top_level_modules >= config.explore_min_modules
    )


def brief_block(brief: str) -> str:
    """An extra_system block carrying the explore subagent's project brief (E7)."""
    return "PROJECT BRIEF (from the explore subagent — use it to avoid re-exploring):\n" + brief


def run_explore(config: Config, task: str, *, llm: LLMClient | None = None,
                trace: bool = False) -> str:
    """Run the cheap, read-only exploration subagent; return the (bounded) brief."""
    explore_config = replace(config, max_steps=config.explore_max_steps)
    agent = CodingAgent(
        explore_config,
        llm=llm or LLMClient(explore_config, model=config.explore_model_name),
        model=config.explore_model_name,
        tools=EXPLORE_TOOLS,          # read-only whitelist (E5)
        trace=trace,
        system_prompt=EXPLORE_PROMPT.format(workdir=config.workdir),
    )
    brief = agent.run(task)
    return brief[: config.explore_brief_chars]  # bounded (E6)


def orchestrate(config: Config, task: str, *, explicit: int = 0, trace: bool = False,
                stream: bool = False, on_delta: Any | None = None,
                explore_llm: LLMClient | None = None,
                impl_llm: LLMClient | None = None,
                on_brief: Any | None = None) -> tuple[str, str | None]:
    """Run the full pipeline, spawning the explore subagent ONLY when warranted.

    Returns (final answer, brief_or_None). The explore subagent is launched only
    if `should_explore` is true; otherwise this is a plain single-agent run with
    no extra subagent and no extra model cost. `on_brief` (optional) is invoked
    with the brief right after exploration, before the implement agent runs.
    """
    stats = collect_repo_stats(config.workdir)
    brief: str | None = None
    if should_explore(config, stats, explicit):
        try:
            brief = run_explore(config, task, llm=explore_llm, trace=trace)
        except Exception:
            brief = None  # explore failed -> downgrade to single agent (2.0.2)
        if brief and on_brief:
            on_brief(brief)
    impl = CodingAgent(config, llm=impl_llm)
    answer = impl.run(task, stream=stream, on_delta=on_delta,
                      extra_system=brief_block(brief) if brief else "")
    return answer, brief
