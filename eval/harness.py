"""Harness runner (specs/eval-harness.md EH1-EH4, B8/B9) — SWE-bench style.

Flow:
  1) copy the task's repo seed into an isolated temp dir
  2) run the agent inside it (eval model tier by default), capture trajectory
  3) copy hidden tests in and run them with pytest -> passed (PASS/FAIL)
  4) if the task has a rubric, ask an LLM judge to score quality dimensions
  5) build an EvalRecord (elapsed, tokens, trajectory, final answer, rubric)
  6) always clean up the isolated dir (EH4)
"""
from __future__ import annotations

import difflib
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.config import Config
from agent.loop import CodingAgent
from agent.llm import LLMClient
from .judge import Judge
from .tasks import Task


@dataclass
class EvalRecord:
    task_id: str
    passed: bool = False
    rubric_scores: dict[str, float] = field(default_factory=dict)
    elapsed_s: float = 0.0
    tokens: int = 0
    trajectory: str = ""
    final_answer: str = ""


def _populate(repo: Path, task: Task) -> None:
    """Copy the seed repo into the isolated workdir."""
    shutil.copytree(task.repo_seed, repo, dirs_exist_ok=True)


def _run_hidden_tests(repo: Path, task: Task) -> bool:
    """Copy hidden tests into the repo and run pytest; PASS iff all pass."""
    hidden = repo / "_hidden_tests"
    shutil.copytree(task.hidden_tests, hidden, dirs_exist_ok=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(hidden), "-q"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=180,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    stdout = proc.stdout or ""
    return proc.returncode == 0 and "passed" in stdout and "failed" not in stdout


def _collect_diff(seed: Path, repo: Path) -> str:
    """Unified diff between the seed repo and the agent's final workspace."""
    hidden = {p.relative_to(repo) for p in (repo / "_hidden_tests").rglob("*")} if (repo / "_hidden_tests").exists() else set()
    seed_files = {p.relative_to(seed) for p in seed.rglob("*") if p.is_file()}
    repo_files = {p.relative_to(repo) for p in repo.rglob("*") if p.is_file() and p.relative_to(repo) not in hidden}

    diffs: list[str] = []
    for rel in sorted(seed_files | repo_files):
        old_p, new_p = seed / rel, repo / rel
        try:
            old_text = old_p.read_text(encoding="utf-8", errors="replace") if old_p.exists() else ""
        except Exception:
            continue
        try:
            new_text = new_p.read_text(encoding="utf-8", errors="replace") if new_p.exists() else ""
        except Exception:
            continue
        if old_text == new_text:
            continue
        diffs.append(f"--- a/{rel}\n+++ b/{rel}\n")
        diffs.extend(difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm="", n=1))
    return "\n".join(diffs)


def _build_trajectory(agent: CodingAgent) -> str:
    return "\n".join(
        f"step {e['step']}: text={e['text']!r} calls={e['tool_calls']}"
        for e in agent.trajectory
    )


def run_task(task: Task, config: Config, llm: LLMClient | None = None, trace: bool = False,
             model: str | None = None, judge: Judge | None = None) -> EvalRecord:
    """Run one task against the agent in an isolated dir; return a graded record."""
    tmp = Path(tempfile.mkdtemp(prefix="eval-"))
    try:
        _populate(tmp, task)
        # The agent must work INSIDE the isolated dir, not config.workdir.
        from dataclasses import replace

        agent_config = replace(config, workdir=tmp)
        agent = CodingAgent(agent_config, llm=llm, model=model or config.eval_model_name, trace=trace)

        start = time.monotonic()
        answer = agent.run(task.description)
        elapsed_s = time.monotonic() - start
        passed = _run_hidden_tests(tmp, task)

        rubric_scores: dict[str, float] = {}
        if task.rubric:
            scorer = judge or Judge(config, model=model or config.eval_model_name)
            rubric_scores = scorer.score(
                task.description,
                _build_trajectory(agent),
                _collect_diff(task.repo_seed, tmp),
                task.rubric,
            )

        return EvalRecord(
            task_id=task.id,
            passed=passed,
            rubric_scores=rubric_scores,
            elapsed_s=elapsed_s,
            tokens=agent.total_tokens,
            trajectory=_build_trajectory(agent),
            final_answer=answer,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
