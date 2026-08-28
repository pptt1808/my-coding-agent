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
    from agent.diff import collect_diff_dirs

    return collect_diff_dirs(
        seed, repo,
        skip_dirs={"__pycache__", ".git", ".pytest_cache", "_hidden_tests", ".coding-agent"},
    )


def _build_trajectory(agent: CodingAgent) -> str:
    return "\n".join(
        f"step {e['step']}: text={e['text']!r} calls={e['tool_calls']}"
        for e in agent.trajectory
    )


def run_task(task: Task, config: Config, llm: LLMClient | None = None, trace: bool = False,
             model: str | None = None, judge: Judge | None = None, multi: bool = False) -> EvalRecord:
    """Run one task against the agent in an isolated dir; return a graded record.

    `multi=True` uses the multi-agent pipeline (explore subagent + planner with
    `should_explore` gating) instead of a single agent — for A/B comparison.
    """
    tmp = Path(tempfile.mkdtemp(prefix="eval-"))
    try:
        _populate(tmp, task)
        from dataclasses import replace

        agent_config = replace(config, workdir=tmp)

        if multi:
            from agent.multi import orchestrate

            mcfg = replace(config, workdir=tmp, model=model or config.eval_model_name,
                           auto_explore="auto", auto_plan="auto", parallel_explore="auto",
                           explore_model=config.model)
            metrics: dict[str, Any] = {}
            start = time.monotonic()
            answer, _brief = orchestrate(mcfg, task.description, trace=trace, metrics=metrics)
            elapsed_s = time.monotonic() - start
            tokens = int(metrics.get("total_tokens", 0))
        else:
            from agent.loop import CodingAgent

            agent = CodingAgent(agent_config, llm=llm, model=model or config.eval_model_name, trace=trace)
            start = time.monotonic()
            answer = agent.run(task.description)
            elapsed_s = time.monotonic() - start
            tokens = agent.total_tokens

        passed = _run_hidden_tests(tmp, task)

        rubric_scores: dict[str, float] = {}
        if task.rubric:
            scorer = judge or Judge(config, model=model or config.eval_model_name)
            rubric_scores = scorer.score(
                task.description,
                _build_trajectory(agent) if not multi else "",
                _collect_diff(task.repo_seed, tmp),
                task.rubric,
            )

        return EvalRecord(
            task_id=task.id,
            passed=passed,
            rubric_scores=rubric_scores,
            elapsed_s=elapsed_s,
            tokens=tokens,
            trajectory=_build_trajectory(agent) if not multi else "",
            final_answer=answer,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
