"""Multi-turn, real-usage demo (development + debugging, real API key needed).

Runs the REAL agent over several interactive turns on a multi-file project:
  T1  explore + fix a bug + implement a function + add a CLI flag + pass tests
  T2  summarize the changes
  T3  re-run the test suite and report
  /review  self-review of the diff (tests + LLM judge)
  /cost    token usage

Usage:
    python examples/demo_multi_turn.py [--model deepseek-v4-pro]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.config import Config  # noqa: E402
from agent.repl import ReplSession  # noqa: E402

TURNS = [
    (
        "Explore this project. Then: 1) fix the bug in src/stats.py so variance() "
        "computes the population variance, 2) implement median() in src/stats.py, "
        "3) add a --stats flag to src/main.py that prints mean, variance and median. "
        "Run the test suite and make every test pass before finishing."
    ),
    "Summarize which files you changed and why, in 3 short bullets.",
    "Run python -m pytest -q again and report the final result line.",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="override model tier")
    args = parser.parse_args()

    cfg = Config.from_env()  # raises a clear error if no key is set
    model = args.model or cfg.model
    print(f"demo: model={model}  base_url={cfg.base_url}")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "demo_project"
        shutil.copytree(Path(__file__).parent / "demo_project", repo)
        sess = ReplSession(replace(cfg, workdir=repo), model=model)

        for i, turn in enumerate(TURNS, start=1):
            print(f"\n{'=' * 18} TURN {i} {'=' * 18}\n>>> {turn}")
            for out in sess.handle(turn):
                print(out)

        print(f"\n{'=' * 18} /review {'=' * 18}")
        for out in sess.handle("/review"):
            print(out)

        print(f"\n{'=' * 18} /cost {'=' * 18}")
        for out in sess.handle("/cost"):
            print(out)

        print(f"\n{'=' * 18} final test run {'=' * 18}")
        import subprocess

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"], cwd=repo,
            capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace",
        )
        print((proc.stdout or proc.stderr or "")[-400:].strip())
        return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
