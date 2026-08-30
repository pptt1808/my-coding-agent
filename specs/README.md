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

## Specs authored so far (all match the scaffold module names)
| spec | 对应模块 | 关键验收 | 状态 |
|---|---|---|---|
| `config.md` | `agent/config.py` | C1-C4 | ✅ 已实现，契约测试绿 |
| `tools.md` | `tools/file_ops.py`, `tools/shell.py` | read_file A1-A3, write_file B1-B2, bash C1-C4, list_dir L1-L3, glob G1-G3, grep GR1-GR4, append_file AP1-AP2, edit_file ED1-ED5 | ✅ Phase 1+T1 已实现 |
| `agent-loop.md` | `agent/loop.py` | L1-L5 | 🔲 Phase 1 |
| `parser.md` | `agent/parser.py` | P1-P4 | 🔲 Phase 1+ |
| `termination.md` | `agent/termination.py` | T1-T6 | 🔲 Phase 1 (T1-T3) / Phase 3 (T4-T6) |
| `context.md` | `agent/history.py` | CT1-CT5 | 🔲 Phase 1 (CT1-CT4) / Phase 3 (CT5) |
| `errors.md` | `agent/errors.py`, `tools/registry.py` | E1-E4 | 🔲 Phase 1 |
| `safety.md` | `tools/shell.py`, `tools/file_ops.py` | S1-S4 | 🔲 Phase 4 (T2) |
| `eval-tasks.md` | `eval/tasks.py` | EV1-EV4 | ✅ Phase 5 已实现 |
| `eval-harness.md` | `eval/harness.py` | EH1-EH4 | ✅ Phase 5 已实现 |
| `eval-judge.md` | `eval/judge.py` | EJ1-EJ4 | ✅ Phase 6 已实现 |
| `eval-report.md` | `eval/report.py` | ER1-ER4 | ✅ Phase 5 已实现 |
| `cli.md` | `agent/repl.py`, `agent/cli.py` | R1-R10 | ✅ P0+P1 已实现 |
| `compact.md` | `agent/compact.py`, `agent/loop.py` | CP1-CP4 | ✅ P0+P1 已实现 |
| `session.md` | `agent/session.py`, `agent/repl.py` | S1-S4 | ✅ P1 已实现 |
| `tasklist.md` | `agent/repl.py`, `agent/loop.py` | T1-T4 | ✅ P1 已实现 |
| `permissions.md` | `agent/repl.py`, `tools/context.py` | P1-P3 | ✅ P2 已实现 |
| `review.md` | `agent/repl.py`, `agent/diff.py`, `eval/judge.py` | RV1-RV4 | ✅ P2 已实现 |
| `multi-agent.md` | `agent/multi.py`, `agent/cli.py`, `agent/repl.py` | E1-E7 | ✅ Phase A 已实现 |
| `pm-mode.md` | `agent/pm.py`, `agent/cli.py` | P1-P10 | ✅ 个性化已实现 |
| `repomap.md` | `agent/repomap.py`, `agent/loop.py`, `agent/repl.py` | R1-R5 | ✅ 改进#1 已实现 |

每份 spec 对应的契约测试在 `tests/specs/test_<name>.py`，应在实现**之前**编写（先红后绿）。
