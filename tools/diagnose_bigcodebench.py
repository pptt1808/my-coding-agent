"""Diagnose WHY BigCodeBench problems fail — to reveal OUR agent's real issues.

Run a few FAILing problems, capturing: how many steps the agent took, what it
did, its final answer, and the ACTUAL hidden-test failure output. This tells us
whether a failure is: (a) the model wrote wrong logic, (b) our termination
config cut it off too early, or (c) a harness/env issue (test import, etc.).

Usage: python -c "... " or import and run below.
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import Config  # noqa: E402
from agent.loop import CodingAgent  # noqa: E402
from eval.bigcodebench import load_bigcodebench  # noqa: E402
from eval.harness import _run_hidden_tests  # noqa: E402
from eval.tasks import Task  # noqa: E402


def diagnose(task: Task, cfg: Config) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        import shutil
        shutil.copytree(task.repo_seed, repo)
        cfg2 = replace(cfg, workdir=repo)
        agent = CodingAgent(cfg2, model=cfg.model)
        answer = agent.run(task.description)
        test_passed, test_out = (_run_hidden_tests(repo, task), "")
        print(f"\n===== {task.id} =====")
        print(f"  steps={agent.steps}  tokens={agent.total_tokens}  final_test_passed={test_passed}")
        print(f"  final answer:\n{answer[:600]}")
        print(f"  trajectory (steps):")
        for e in agent.trajectory:
            calls = [f"{c['name']}({c['arguments']})" for c in e["tool_calls"]]
            print(f"    step {e['step']}: text={str(e['text'])[:120]!r} calls={calls}")
        # reproduce the test to show the concrete failure
        from eval.harness import _run_hidden_tests as _rh
        _rh(repo, task)


if __name__ == "__main__":
    cfg = Config.from_env()
    cfg = replace(cfg, max_steps=12, max_tool_calls=24, max_consecutive_failures=3,
                  no_progress_limit=3)
    tasks = {t.id: t for t in load_bigcodebench(limit=30, seed=42)}
    for tid in sys.argv[1:]:
        t = tasks.get(tid)
        if t:
            diagnose(t, cfg)
