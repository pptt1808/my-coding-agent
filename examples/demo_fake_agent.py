"""End-to-end demo of the agent loop WITHOUT an API key (offline).

A scripted FakeLLM plays the model: it reads the buggy file, writes the fix,
then answers. Everything else is REAL — the loop, the tools, history, parser,
termination. Only the LLM is fake.

Run:  python examples/demo_fake_agent.py
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.config import Config  # noqa: E402
from agent.llm import LLMResult, ToolCall  # noqa: E402
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


class ScriptedLLM:
    """Scripted model: read util.py -> write the fix -> final answer."""

    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    @staticmethod
    def _last_tool_output(messages: list[dict]) -> str:
        for m in reversed(messages):
            if m.get("role") == "tool" and m.get("content"):
                return str(m["content"])
        return ""

    def complete(self, _system_prompt, messages, _tools):
        self.calls.append(list(messages))
        n = len(self.calls)
        if n == 1:
            return LLMResult(text="", tool_calls=[ToolCall("c1", "read_file", {"path": "src/util.py"})])
        if n == 2:
            content = self._last_tool_output(messages)
            fixed = content.replace("a + b", "a - b")
            return LLMResult(text="", tool_calls=[ToolCall("c2", "write_file", {"path": "src/util.py", "content": fixed})])
        return LLMResult(text="Fixed the bug in src/util.py: add() now returns a - b.")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src/util.py").write_text(BUGGY, encoding="utf-8")
        (root / "test_util.py").write_text(TEST, encoding="utf-8")

        config = Config(api_key="demo", workdir=root, max_steps=5, max_tool_calls=10)
        agent = CodingAgent(config, llm=ScriptedLLM())

        print("=== task ===")
        print("Fix the bug in src/util.py so add(10, 4) == 6 (run tests to confirm).")
        print("\n=== agent run ===")
        answer = agent.run("Fix the bug in src/util.py so add(10, 4) == 6. Then verify with the test.")
        print(f"\n=== final answer ===\n{answer}")

        print("\n=== fixed file ===")
        print((root / "src/util.py").read_text(encoding="utf-8"))

        print("=== hidden test ===")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "test_util.py"],
            cwd=root, capture_output=True, text=True, timeout=60,
        )
        print((result.stdout or "")[-400:].strip())
        passed = "passed" in result.stdout and "failed" not in result.stdout
        print(f"\nPASS/FAIL: {'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
