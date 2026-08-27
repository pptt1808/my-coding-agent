# specs/ — spec-driven development

**Spec-driven only constrains how WE build this agent project** (decision B13),
never the agent's runtime behavior. Every component goes through the loop:

```
1. Spec (规格说明)  -> this directory, one markdown per component
2. Contract tests    -> written FIRST, in tests/specs/  (red)
3. Implement         -> write code to satisfy the spec
4. Verify            -> run the contract tests (green = spec satisfied)
5. Regress           -> spec stays a living contract; re-run all tests on change
```

## Spec template
```markdown
## <component>
职责:...
接口:...
行为:
  - ...
验收标准（可自动验证）:
  A1 ...
  A2 ...
```

## Naming
Each spec file maps to a `tests/specs/test_*.py` that encodes its acceptance
criteria as pytest tests. The eval harness (`eval/`) is the *second*, higher
layer that grades the running agent — see 开发文档 §6.4.

## Starter specs to write (matching the scaffold)
- `config.md`        -> config contract (C1-C4) [config.py is already implemented]
- `tools.md`         -> read_file A1/A2/A3, write_file, bash (Phase 1)
- `agent-loop.md`    -> the pipeline (Phase 1)
- `parser.md`        -> native + text-fallback parsing (Phase 1+)
- `termination.md`   -> combined thresholds (Phase 3/T1)
- `context.md`       -> history + truncation/summarization (Phase 3/T1)
- `errors.md`        -> error funneling (N6)
- `eval-*.md`        -> task / harness / judge / report (Phase 5-6)
