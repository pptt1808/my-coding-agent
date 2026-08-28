# Task: refactor_rename (L3, cross-file refactoring)

Rename the function `calc_total` to `compute_total` across the whole project:
- `src/billing.py` defines `calc_total` (rename the definition);
- `src/report.py` imports and calls `calc_total`;
- `src/main.py` imports and calls `calc_total`.

Keep the behavior identical (sum of each item's `price` field). The hidden test
suite imports `compute_total` — make every test pass before finishing.
