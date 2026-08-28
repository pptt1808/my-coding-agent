"""Batch evaluation entry: `python -m eval [tasks_dir] [--model ...] [--trace]`.

Loads the task set, runs the agent on each in an isolated dir (eval model tier
by default — deepseek-v4-pro in our setup), grades PASS/FAIL against hidden
tests, and prints a markdown report.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.config import Config  # noqa: E402
from eval.harness import run_task  # noqa: E402
from eval.report import render_markdown, summarize  # noqa: E402
from eval.tasks import load_tasks  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval")
    parser.add_argument("tasks_dir", nargs="?", default="tasks",
                        help="directory containing task dirs (default: tasks)")
    parser.add_argument("--task", default=None, help="run only this task id (e.g. parser_calc)")
    parser.add_argument("--model", default=None, help="override model tier for this run")
    parser.add_argument("--trace", action="store_true", help="print each agent step")
    args = parser.parse_args(argv)

    cfg = Config.from_env()  # raises a clear error if no key is set
    tasks = load_tasks(args.tasks_dir)
    if args.task:
        tasks = [t for t in tasks if t.id == args.task]
        if not tasks:
            print(f"task not found: {args.task}")
            return 1
    if not tasks:
        print(f"no tasks found under {args.tasks_dir}")
        return 1

    model = args.model or cfg.eval_model_name
    print(f"loaded {len(tasks)} task(s); agent tier: {model}")
    records = []
    for task in tasks:
        print(f"\n=== running task: {task.id} ===")
        record = run_task(task, cfg, trace=args.trace, model=model)
        print(f"task={task.id} {'PASS' if record.passed else 'FAIL'} "
              f"elapsed={record.elapsed_s:.1f}s tokens={record.tokens}")
        records.append(record)

    print("\n" + render_markdown(summarize(records)))
    n_passed = sum(1 for r in records if r.passed)
    return 0 if n_passed == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
