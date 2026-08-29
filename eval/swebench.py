"""SWE-bench adapter (specs/swebench-bench.md).

SWE-bench instances are real GitHub issues -> repo at a base commit -> test_patch.
This module converts a SWE-bench instance (from a local `swe-bench-verified.jsonl`,
or a HuggingFace dataset if reachable) into our eval harness's `Task`, and grades
it with the same hidden-test PASS/FAIL flow.

Network note: this environment cannot reach github.com / huggingface.co, so the
dataset and the repo checkouts must be provided locally by the user:
  - dataset: a JSONL of SWE-bench_Verified instances (place at e.g. ../swe-bench-verified.jsonl
    or point SWEBENCH_JSONL at it);
  - repos: checkout of the repo at the instance's `base_commit` (place under a
    vendored dir, or let the loader clone via a mirror you can reach).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .tasks import Task

REPO_WHITELIST = {
    # lightweight, pip-installable, pytest-based SWE-bench_Verified repos
    "requests", "flask", "pydantic", "sympy", "matplotlib", "sphinx",
    "pylint", "astropy", "scikit-learn", "pytest", "django", "sqlglot",
}


def load_instances(jsonl: Path | str | None = None) -> list[dict[str, Any]]:
    """Load SWE-bench instances from a local JSONL (or a provided path).

    Returns a list of instance dicts with the standard fields:
      instance_id, repo, base_commit, problem_statement, patch, test_patch,
      FAIL_TO_PASS, PASS_TO_PASS, ...
    """
    if jsonl is None:
        jsonl = Path(__file__).resolve().parents[1] / "swe-bench-verified.jsonl"
    path = Path(jsonl)
    if not path.exists():
        raise FileNotFoundError(
            f"SWE-bench data not found at {path}. This environment cannot reach "
            "huggingface.co/github.com, so provide the JSONL locally."
        )
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def filter_instances(instances: list[dict[str, Any]], repos: list[str] | None = None,
                     limit: int | None = None) -> list[dict[str, Any]]:
    """Choose a small, feasible subset (pytest-based, lightweight repos)."""
    picked = [i for i in instances if i.get("repo") in (repos or set(REPO_WHITELIST))]
    if limit:
        picked = picked[:limit]
    return picked


def instance_to_task(instance: dict[str, Any], repo_seed: Path,
                     hidden_dir: Path) -> Task:
    """Convert a SWE-bench instance into a harness Task.

    `repo_seed` must already be a checkout of the repo at the instance base commit.
    `hidden_dir` receives the test files produced by applying `test_patch`.
    """
    apply_patch(instance.get("test_patch", ""), repo_seed)

    # collect the test files the patch touched, copy them to hidden_dir
    hidden_dir.mkdir(parents=True, exist_ok=True)
    for rel in _patched_files(instance.get("test_patch", "")):
        src = repo_seed / rel
        if src.exists():
            dst = hidden_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

    return Task(
        id=instance["instance_id"],
        description=instance["problem_statement"],
        repo_seed=repo_seed,
        hidden_tests=hidden_dir,
        baseline=instance.get("base_commit", ""),
        rubric={"correctness": "Does the patch make the target tests pass?"},
    )


def apply_patch(patch: str, repo_seed: Path) -> None:
    """Apply a unified diff (SWE-bench test_patch) onto a repo checkout.

    The patch is written to a temp file and passed as an argument, so no
    stdin pipe is required (works under restricted sandboxes).
    """
    if not patch:
        return
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as fh:
        fh.write(patch)
        patch_path = fh.name
    try:
        proc = subprocess.run(
            ["git", "apply", patch_path], cwd=repo_seed, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    finally:
        Path(patch_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git apply failed: {proc.stderr[-500:]}")


def _patched_files(patch: str) -> list[str]:
    files: list[str] = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:].strip())
    return files


def fail_to_pass_tests(instance: dict[str, Any]) -> list[str]:
    """The tests that must pass for the instance to be resolved."""
    return [t for t in instance.get("FAIL_TO_PASS", []) or []]
