"""Multi-agent orchestration (specs/multi-agent.md).

The primary constraint is the **launch timing** of the explore subagent: it is
NEVER spawned unless it is clearly worth it. `should_explore` is deterministic
and free (a single os.walk, no model call), defaults to OFF, and respects
explicit --explore / --no-explore overrides.

Phase A pipeline: explore (cheap, read-only) -> brief -> implement (brief injected).
Phase B adds: a cheap planner (brief+task -> todo plan) and parallel exploration
fan-out (one read-only explore agent per top-level module for large repos).
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
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

PLANNER_PROMPT = (
    "You are a task planner working in: {workdir}\n"
    "Given a task and a project brief, decompose the work into an ordered todo "
    "list (one item per line, numbered). Keep items concrete and verifiable, "
    "at most 10 items. Do not modify any file."
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


def _top_level_modules(workdir: Path | str) -> list[str]:
    """Directories directly under the repo root (used for parallel fan-out)."""
    root = Path(workdir)
    if not root.exists():
        return []
    return sorted(d.name for d in root.iterdir() if d.is_dir() and d.name not in _SKIP)


def parse_todos(text: str) -> list[str]:
    """Parse a planner's numbered/bulleted output into a concise todo list."""
    todos: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s*", "", line).strip()
        if cleaned:
            todos.append(cleaned)
        if len(todos) >= 10:
            break
    return todos


def plan_block(todos: list[str]) -> str:
    items = "\n".join(f"{i}. {t}" for i, t in enumerate(todos, start=1))
    return "PLAN (from the planner subagent — follow these steps):\n" + items


def run_planner(config: Config, task: str, brief: str, *, llm: LLMClient | None = None,
                trace: bool = False, metrics: dict[str, Any] | None = None) -> list[str]:
    """Cheap planner subagent: task + brief -> ordered todo list (Phase B)."""
    plan_cfg = replace(config, max_steps=config.explore_max_steps)
    agent = CodingAgent(
        plan_cfg,
        llm=llm or LLMClient(plan_cfg, model=config.explore_model_name),
        model=config.explore_model_name,
        tools=[],  # pure reasoning, no tools
        trace=trace,
        system_prompt=PLANNER_PROMPT.format(workdir=config.workdir),
    )
    text = agent.run(f"TASK:\n{task}\n\nBRIEF:\n{brief}")
    _record(metrics, agent)
    return parse_todos(text)


def _record(metrics: dict[str, Any] | None, agent: CodingAgent) -> None:
    """Accumulate a subagent's cost into a shared metrics dict (for A/B comparisons)."""
    if metrics is None:
        return
    metrics["subagent_tokens"] = metrics.get("subagent_tokens", 0) + agent.total_tokens
    metrics["subagent_steps"] = metrics.get("subagent_steps", 0) + agent.steps
    metrics["subagents"] = metrics.get("subagents", 0) + 1


def run_explore(config: Config, task: str, *, llm: LLMClient | None = None,
                trace: bool = False, metrics: dict[str, Any] | None = None) -> str:
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
    _record(metrics, agent)
    return brief[: config.explore_brief_chars]  # bounded (E6)


def parallel_explore(config: Config, task: str, *, modules: list[str] | None = None,
                     llms: dict[str, LLMClient] | None = None, trace: bool = False,
                     metrics: dict[str, Any] | None = None) -> str:
    """One read-only explore agent per top-level module, run concurrently (Phase B).

    Each subagent is scoped to its own module dir (workdir=<repo>/<module>), so
    they can never touch each other's files. Merged into one bounded brief.
    """
    root = Path(config.workdir)
    if modules is None:
        modules = _top_level_modules(root)
    if not modules:
        return run_explore(config, task, trace=trace, metrics=metrics)

    def _one(module_name: str) -> str:
        mod_cfg = replace(config, workdir=root / module_name)
        llm = (llms or {}).get(module_name)
        return f"[{module_name}]\n{run_explore(mod_cfg, task, llm=llm, trace=trace, metrics=metrics)}"

    with ThreadPoolExecutor(max_workers=min(len(modules), 4)) as pool:
        results = list(pool.map(_one, modules))
    merged = "\n\n".join(r for r in results if r)
    return merged[: config.explore_brief_chars]  # bounded


def orchestrate(config: Config, task: str, *, explicit: int = 0, trace: bool = False,
                stream: bool = False, on_delta: Any | None = None,
                explore_llm: LLMClient | None = None,
                explore_llms: dict[str, LLMClient] | None = None,
                planner_llm: LLMClient | None = None,
                impl_llm: LLMClient | None = None,
                on_brief: Any | None = None,
                metrics: dict[str, Any] | None = None) -> tuple[str, str | None]:
    """Run the full pipeline, spawning the explore subagent ONLY when warranted.

    Returns (final answer, brief_or_None). The explore subagent is launched only
    if `should_explore` is true; otherwise this is a plain single-agent run with
    no extra subagent and no extra model cost. `on_brief` (optional) is invoked
    with the brief right after exploration, before the implement agent runs.
    `metrics` (optional) accumulates token/step counts across all subagents for
    A/B cost comparisons.

    Phase B: if `parallel_explore` is enabled and there are enough top-level
    modules, fan out one explore subagent per module; if `auto_plan` is enabled,
    a cheap planner turns (brief+task) into an ordered todo that is injected too.
    """
    stats = collect_repo_stats(config.workdir)
    brief: str | None = None
    if should_explore(config, stats, explicit):
        try:
            if config.parallel_explore in ("auto", "always") and \
                    stats.top_level_modules >= config.explore_fanout_min_modules:
                brief = parallel_explore(config, task, llms=explore_llms, trace=trace, metrics=metrics)
            else:
                brief = run_explore(config, task, llm=explore_llm, trace=trace, metrics=metrics)
        except Exception:
            brief = None  # explore failed -> downgrade to single agent (2.0.2)
        if brief and on_brief:
            on_brief(brief)

    extra_parts: list[str] = []
    if brief:
        extra_parts.append(brief_block(brief))
    if brief and config.auto_plan != "off":
        try:
            todos = run_planner(config, task, brief, llm=planner_llm, trace=trace, metrics=metrics)
            if todos:
                extra_parts.append(plan_block(todos))
        except Exception:
            pass  # planning failed -> implement still has the brief

    impl = CodingAgent(config, llm=impl_llm)
    answer = impl.run(task, stream=stream, on_delta=on_delta,
                      extra_system="\n\n".join(extra_parts) if extra_parts else "")
    if metrics is not None:
        metrics["impl_tokens"] = impl.total_tokens
        metrics["impl_steps"] = impl.steps
        metrics["total_tokens"] = impl.total_tokens + metrics.get("subagent_tokens", 0)
    return answer, brief
