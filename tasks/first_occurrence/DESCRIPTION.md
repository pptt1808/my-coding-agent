# Task: first_occurrence (L6, subtle edge-case bug)

`first_occurrence(sorted_list, target)` in `src/search.py` should return the
index of the **FIRST** occurrence of `target` in a sorted list that may contain
duplicates, or `-1` if absent.

The current implementation has a subtle bug: with duplicate values it returns
the **last** occurrence instead of the first. For example:
- `first_occurrence([1, 2, 2, 2, 3], 2)` should return `1`, but the buggy code
  returns `3`.
- `first_occurrence([2, 2, 2, 3], 2)` should return `0`.

Find the bug, fix it, and make every hidden test pass before finishing.
