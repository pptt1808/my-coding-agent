# Task: large_task

This is a multi-module task-tracker app. Do the following:
1. Fix the bug in `app/service.py`: `filter_by_status(tasks, status)`
   currently returns tasks whose status is **not** `status` (inverted).
   It must return only the tasks that **match** `status`.
2. Implement `top_priority_open(tasks)` in `app/service.py`: return the
   OPEN task with the highest `priority` (3 = highest), or `None` if
   there is no open task.
3. Make the hidden tests pass (they are not in the repo). Verify with
   `python -m pytest tests -q` after the code is in place.
