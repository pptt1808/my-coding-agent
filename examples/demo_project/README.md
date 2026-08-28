# Demo Project (multi-file, for the multi-turn demo)

A tiny statistics CLI used to demonstrate the coding agent over multiple
interactive turns — it contains a bug, a missing function and a missing CLI
feature, with a test suite that defines "done".

- `src/stats.py` — `variance()` has a bug; `median()` is not implemented.
- `src/main.py` — the `--stats` flag is missing (should print variance + median).
- `tests/` — defines what "done" means.
