from app.models import Status, Task
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
