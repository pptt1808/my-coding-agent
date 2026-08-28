from .models import Status, Task


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
