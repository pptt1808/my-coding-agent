"""Generate a large, multi-module task for the A/B evaluation.

Creates tasks/large_task/ with:
  repo/            a small task-tracker app spread over several modules + filler
                   config/data/docs so the repo crosses the auto-explore gate
  DESCRIPTION.md   the problem (a bug + a missing feature + hidden tests)
  tests/           hidden tests (fail on the seed)
  rubric.json      LLM-judge dimensions
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "large_task"


def w(rel: str, content: str) -> None:
    p = TASK / "repo" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main() -> None:
    # ---- app package (real logic) ----
    w("app/__init__.py", "")
    w("app/models.py", '''from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional


class Status(str, Enum):
    OPEN = "open"
    DONE = "done"


@dataclass
class Task:
    id: int
    title: str
    status: Status = Status.OPEN
    priority: int = 1  # 1 low, 2 medium, 3 high

    def to_dict(self):
        return asdict(self)
''')
    w("app/storage.py", '''import json
from pathlib import Path
from .models import Task


def load(path) -> list[Task]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Task(**t) for t in data]


def save(path, tasks) -> None:
    Path(path).write_text(json.dumps([t.to_dict() for t in tasks], indent=2), encoding="utf-8")
''')
    w("app/service.py", '''from .models import Status, Task


def add_task(tasks: list[Task], title: str, priority: int = 1) -> Task:
    t = Task(id=len(tasks) + 1, title=title, priority=priority)
    tasks.append(t)
    return t


def complete_task(tasks: list[Task], task_id: int) -> None:
    for t in tasks:
        if t.id == task_id:
            t.status = Status.DONE


def filter_by_status(tasks: list[Task], status: str) -> list[Task]:
    # BUG: comparison is inverted — returns tasks whose status != status
    return [t for t in tasks if t.status != status]


def top_priority_open(tasks: list[Task]) -> Task | None:
    # TODO: return the OPEN task with the highest priority, or None
    raise NotImplementedError


def sort_by_priority(tasks: list[Task]) -> list[Task]:
    return sorted(tasks, key=lambda t: t.priority, reverse=True)
''')
    w("app/cli.py", '''import sys
from .service import add_task, sort_by_priority


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m app.cli add <title> | list [--priority]")
        return 1
    # TODO: handle a --priority flag that prints tasks sorted by priority
    actions = {"add": lambda: add_task([], " ".join(argv[1:])), "list": lambda: []}
    if argv[0] not in actions:
        print(f"unknown action: {argv[0]}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
''')
    w("app/schemas.py", ''''"""JSON schemas for the task store."""\nTASK = {"id": int, "title": str, "status": str, "priority": int}\n''')
    w("app/validators.py", '''def validate_title(title: str) -> None:
    if not title or not title.strip():
        raise ValueError("title must not be empty")
''')
    w("app/config.py", "DEFAULT_PRIORITY = 1\nSTATUSES = (\"open\", \"done\")\n")

    # ---- utils ----
    w("utils/__init__.py", "")
    w("utils/format.py", "def fmt(t): return f\"{t.id}. [{t.status.value}] {t.title} (P{t.priority})\"\n")
    w("utils/dates.py", "import datetime\n\ndef today(): return datetime.date.today().isoformat()\n")
    w("utils/logging.py", "import logging\nlogging.basicConfig(level=logging.INFO)\n")

    # ---- plugins ----
    w("plugins/__init__.py", "")
    w("plugins/base.py", "class Plugin:\n    name = \"base\"\n")
    w("plugins/reminder.py", "from .base import Plugin\n\nclass Reminder(Plugin):\n    name = \"reminder\"\n")
    w("plugins/stats.py", "from .base import Plugin\n\nclass Stats(Plugin):\n    name = \"stats\"\n")

    # ---- configs (filler to reach the explore gate) ----
    for i in range(10):
        w(f"configs/{i:02d}.json", json.dumps({"index": i, "enabled": True}))
    w("configs/README.md", "Runtime configuration templates.\n")

    # ---- data ----
    w("data/seed.json", json.dumps([
        {"id": 1, "title": "write tests", "status": "open", "priority": 3},
        {"id": 2, "title": "fix bug", "status": "done", "priority": 2},
    ]))
    for i in range(12):
        w(f"data/samples/sample_{i:02d}.json", json.dumps({"id": i, "tag": f"s{i}"}))
    w("data/README.md", "Sample data for the task store.\n")

    # ---- docs ----
    w("docs/README.md", "# task-tracker\nA small CLI to manage tasks.\n")
    w("docs/API.md", "## Service API\n- add_task, complete_task, filter_by_status, top_priority_open\n")
    w("docs/conventions.md", "## Conventions\n- status is lowercase\n")

    # ---- scripts ----
    w("scripts/setup.py", "print(\"setup\")\n")
    w("scripts/run.py", "from app.cli import main\nmain()\n")

    # ---- hidden tests (fail on the seed) ----
    (TASK / "tests").mkdir(parents=True, exist_ok=True)
    (TASK / "tests" / "test_service.py").write_text(
        '''from app.models import Status, Task
from app.service import (complete_task, filter_by_status, sort_by_priority,
                         top_priority_open)


def _open(p): return Task(id=p, title=f"t{p}", status=Status.OPEN, priority=p)
def _done(p): return Task(id=p, title=f"t{p}", status=Status.DONE, priority=p)


def test_filter_open_only():
    tasks = [_open(1), _done(2), _open(3)]
    assert filter_by_status(tasks, "open") == [_open(1), _open(3)]


def test_filter_done_only():
    tasks = [_open(1), _done(2)]
    assert filter_by_status(tasks, "done") == [_done(2)]


def test_top_priority_open():
    tasks = [_open(2), _done(3), _open(1)]
    assert top_priority_open(tasks).id == 2


def test_top_priority_none_when_all_done():
    assert top_priority_open([_done(1), _done(2)]) is None


def test_sort_by_priority_desc():
    tasks = [_open(2), _open(1), _open(3)]
    assert [t.id for t in sort_by_priority(tasks)] == [3, 2, 1]


def test_complete_sets_done():
    tasks = [_open(1)]
    complete_task(tasks, 1)
    assert tasks[0].status is Status.DONE
''', encoding="utf-8")

    (TASK / "DESCRIPTION.md").write_text(
        "# Task: large_task\n\n"
        "This is a multi-module task-tracker app. Do the following:\n"
        "1. Fix the bug in `app/service.py`: `filter_by_status(tasks, status)`\n"
        "   currently returns tasks whose status is **not** `status` (inverted).\n"
        "   It must return only the tasks that **match** `status`.\n"
        "2. Implement `top_priority_open(tasks)` in `app/service.py`: return the\n"
        "   OPEN task with the highest `priority` (3 = highest), or `None` if\n"
        "   there is no open task.\n"
        "3. Make the hidden tests pass (they are not in the repo). Verify with\n"
        "   `python -m pytest tests -q` after the code is in place.\n", encoding="utf-8")

    (TASK / "rubric.json").write_text(json.dumps({
        "correctness": "Is the bug fixed and top_priority_open implemented correctly?",
        "quality": "Is the code clear, idiomatic and consistent with the app?",
        "minimal": "Is the change minimal and on-topic?",
    }), encoding="utf-8")

    # repo needs an app package importable from repo root: add a conftest
    w("conftest.py", "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parent))\n")

    nf = sum(1 for p in (TASK / "repo").rglob("*") if p.is_file())
    print(f"{TASK} created: {nf} files in repo/")


if __name__ == "__main__":
    main()
