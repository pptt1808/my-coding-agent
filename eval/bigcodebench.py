"""BigCodeBench adapter (specs/bigcodebench.md).

BigCodeBench is a modern (2024) code-generation benchmark: each problem is a
function to implement from a signature+docstring, graded by hidden unittest
cases. It runs on any modern Python and needs no heavy repos — ideal for our
Python 3.14 environment.

We wrap each problem as a harness Task:
  repo/solution.py      = complete_prompt (imports + def task_func(...) + docstring)
  repo/__init__.py      = empty (so `from solution import task_func` works)
  tests/test_solution.py= "from solution import task_func" + the unittest test code
  DESCRIPTION.md        = the function's docstring (what to implement)
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from .tasks import Task

WORK = Path(__file__).resolve().parents[1] / "swe_work" / "bcb"  # gitignored

# stdlib-only import whitelist (avoid numpy/pandas/matplotlib/... heavy deps)
STDLIB = {"random", "itertools", "math", "re", "json", "unittest", "functools",
          "collections", "string", "datetime", "typing", "copy", "statistics",
          "heapq", "bisect", "operator", "fractions", "decimal", "sys", "hashlib",
          "base64", "uuid", "io", "os", "textwrap", "itertools", "dataclasses"}

_DOC_RE = re.compile(r'"""(.*?)"""', re.DOTALL)


def _stdlib_only(d) -> bool:
    try:
        libs = eval(d.get("libs", "[]"))  # libs is a string like "['random', 'itertools']"
    except Exception:
        libs = []
    return all(lib in STDLIB for lib in libs)


def _docstring(prompt: str) -> str:
    m = _DOC_RE.search(prompt)
    return (m.group(1).strip() if m else prompt[:400]) or "(implement the function)"


def _make_task(d, seq: int) -> Task:
    out_dir = WORK / f"{seq:03d}"
    repo = out_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "__init__.py").write_text("", encoding="utf-8")
    (repo / "solution.py").write_text(d["complete_prompt"], encoding="utf-8")

    tests = out_dir / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    (tests / "test_solution.py").write_text(
        "from solution import task_func\n\n" + d["test"], encoding="utf-8")

    desc = (
        "Implement `task_func` in `solution.py` according to its docstring so the "
        "hidden tests pass.\n\nDocstring:\n" + _docstring(d["complete_prompt"])
    )
    (out_dir / "DESCRIPTION.md").write_text(desc, encoding="utf-8")
    return Task(id=f"bcb-{d['task_id']}", description=desc, repo_seed=repo, hidden_tests=tests,
                rubric={"correctness": "Are all hidden tests satisfied?",
                        "quality": "Is the implementation correct, clear and idiomatic?"})


def load_bigcodebench(limit: int = 30, seed: int = 42, stdlib_only: bool = True) -> list[Task]:
    """Build `limit` tasks from BigCodeBench v0.1.4 (stdlib-only by default)."""
    from datasets import load_dataset

    ds = load_dataset("bigcode/bigcodebench", split="v0.1.4")
    if stdlib_only:
        ds = [d for d in ds if _stdlib_only(d)]
    else:
        ds = list(ds)
    import random
    rng = random.Random(seed)
    rng.shuffle(ds)
    return [_make_task(d, i) for i, d in enumerate(ds[:limit], start=1)]
