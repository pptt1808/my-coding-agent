"""Task definition + task-set loader.

A task = { repo seed / starter code, task description, hidden tests / acceptance
criteria, baseline }.

Spec: specs/eval-tasks.md (to be written). Placeholder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Task:
    id: str
    description: str
    repo_seed: Path  # directory with starter code
    hidden_tests: Path  # test file(s) to run to judge PASS/FAIL
    baseline: str = ""
    rubric: dict[str, str] = field(default_factory=dict)  # dimension -> description, for LLM judge


def load_tasks(tasks_dir: Path) -> list[Task]:
    """Load a task set from disk (one directory per task)."""
    raise NotImplementedError("eval/tasks.py lands in Phase 5 (specs/eval-tasks.md).")
