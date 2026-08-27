# tasks/ — automated evaluation task set

Each task is a directory:
```
tasks/<task-id>/
  repo/          # starter repository (seed code)
  DESCRIPTION.md # what the agent must do (the problem statement)
  tests/         # hidden tests run to judge PASS/FAIL
  rubric.json    # optional LLM-judge dimensions
```

Filled in Phase 5 (eval harness). See `specs/eval-tasks.md` (to be written).
