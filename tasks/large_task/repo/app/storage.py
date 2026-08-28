import json
from pathlib import Path
from .models import Task


def load(path) -> list[Task]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Task(**t) for t in data]


def save(path, tasks) -> None:
    Path(path).write_text(json.dumps([t.to_dict() for t in tasks], indent=2), encoding="utf-8")
