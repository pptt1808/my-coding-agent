# tasks/ — automated evaluation task set

Each task is a directory:
```
tasks/<task-id>/
  repo/          # starter repository (seed code)
  DESCRIPTION.md # what the agent must do (the problem statement)
  tests/         # hidden tests run to judge PASS/FAIL
  rubric.json    # optional LLM-judge dimensions
```

## Difficulty gradient
| task | 难度 | 考察点 |
|---|---|---|
| `fix_add_bug` | L1 易 | 单行 bug 修复（读写+测试闭环） |
| `implement_fib` | L2 中 | 函数实现 + 边界 |
| `refactor_rename` | L3 中 | 跨文件重命名 / 一致性修改 |
| `lru_cache` | L4 中高 | 数据结构实现（LRU，O(1)，recency 语义） |
| `parser_calc` | L5 高 | 解析器算法（优先级/括号/左结合/异常） |
| `first_occurrence` | L6 极高 | 微妙边界 bug（二分查找首个出现） |

