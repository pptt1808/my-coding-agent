"""Task definition + task-set loader (specs/eval-tasks.md EV1-EV4).

A task = a directory under the tasks root:
    tasks/<id>/
      repo/          # starter repository (seed code)
      DESCRIPTION.md # what the agent must do
      tests/         # hidden tests run to judge PASS/FAIL
      rubric.json    # optional LLM-judge dimension descriptions
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Task:
    id: str
    description: str
    repo_seed: Path  # directory with starter code
    hidden_tests: Path  # test file(s) run to judge PASS/FAIL
    baseline: str = ""
    rubric: dict[str, str] = field(default_factory=dict)  # dimension -> description, for LLM judge


def _load_task(task_dir: Path) -> Task:
    task_id = task_dir.name
    repo_seed = task_dir / "repo"
    hidden_tests = task_dir / "tests"
    description_file = task_dir / "DESCRIPTION.md"
    rubric_file = task_dir / "rubric.json"

    missing = [part for part, path in (("repo/", repo_seed), ("tests/", hidden_tests),
                                       ("DESCRIPTION.md", description_file)) if not path.exists()]
    if missing:
        raise ValueError(
            f"task '{task_id}' is missing required parts: {', '.join(missing)}"
        )

    description = description_file.read_text(encoding="utf-8").strip()
    rubric: dict[str, str] = {}
    if rubric_file.exists():
        try:
            loaded = json.loads(rubric_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                rubric = {str(k): str(v) for k, v in loaded.items()}
        except json.JSONDecodeError as exc:
            raise ValueError(f"task '{task_id}' has an invalid rubric.json: {exc}") from exc

    return Task(id=task_id, description=description, repo_seed=repo_seed,
                hidden_tests=hidden_tests, rubric=rubric)


def load_tasks(tasks_dir: Path | str) -> list[Task]:
    """Load every valid task directory under `tasks_dir` (EV1/EV2/EV3/EV4)."""
    root = Path(tasks_dir)
    tasks: list[Task] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        tasks.append(_load_task(entry))
    return tasks
