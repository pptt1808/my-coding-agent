"""Live smoke test — the REAL agent against a REAL model (needs a key in .env).

Runs the full CodingAgent (real LLMClient -> OpenAI-compatible gateway) on a
real task: fix a bug in src/util.py so the hidden test passes.

Usage:
    python examples/live_smoke.py [--model deepseek-v4-pro]

The API key is read from .env only and is never printed.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.config import Config  # noqa: E402
from agent.loop import CodingAgent  # noqa: E402

BUGGY = '''def add(a, b):
    return a + b  # BUG: should be a - b

def sub(a, b):
    return a - b
'''

TEST = '''import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from util import add, sub


def test_bug_fixed():
    assert add(10, 4) == 6  # passes only after the fix
    assert sub(10, 4) == 6
'''

TASK = (
    "Fix the bug in src/util.py: the function add() currently returns a + b, "
    "but it should return a - b. There is a test file test_util.py at the repo "
    "root; make it pass. Verify with the tests before finishing."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="override model tier")
    parser.add_argument("--trace", action="store_true", help="print each agent step")
    args = parser.parse_args()

    cfg = Config.from_env()  # raises a clear error if no key is set
    model = args.model or cfg.model
    print(f"model={model}  base_url={cfg.base_url}  workdir isolated")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src/util.py").write_text(BUGGY, encoding="utf-8")
        (root / "test_util.py").write_text(TEST, encoding="utf-8")

        # The agent must work INSIDE the isolated task repo, not the project root.
        from dataclasses import replace

        agent_cfg = replace(cfg, workdir=root)
        agent = CodingAgent(agent_cfg, model=model, trace=args.trace)
        print("\n=== task ===")
        print(TASK)
        print("\n=== agent run (real model) ===")
        answer = agent.run(TASK)
        print(f"\n=== final answer ===\n{answer}")

        print("\n=== fixed src/util.py ===")
        print((root / "src/util.py").read_text(encoding="utf-8"))

        print("=== hidden test ===")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "test_util.py"],
            cwd=root, capture_output=True, text=True, timeout=120,
        )
        print((result.stdout or "")[-400:].strip() or result.stderr[-400:].strip())
        passed = "passed" in result.stdout and "failed" not in result.stdout
        print(f"\nPASS/FAIL: {'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
