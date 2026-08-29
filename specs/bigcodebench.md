# bigcodebench.md — BigCodeBench 适配 (benchmark)

职责：把现代 (2024) BigCodeBench 代码生成题接入我们的评测 harness，作为**本机环境友好**（Python 3.14、纯标准库、无需重仓库）的可信代码基准。每道题 = 一个函数实现任务：`repo/solution.py`（签名+docstring 桩）+ `tests/test_solution.py`（`from solution import task_func` + 隐藏 unittest），agent 实现后隐藏测试通过即 PASS，并由 LLM-judge 打质量分。

接口：`eval/bigcodebench.py`：`load_bigcodebench(limit=30, seed=42, stdlib_only=True) -> list[Task]`；`tools/run_bigcodebench.py --limit N [--multi]`。

行为：
- 从 HF `bigcode/bigcodebench`（split v0.1.4）加载；
- 默认**只保留纯标准库**题目（`libs` 全在 stdlib 白名单，避免 numpy/pandas 等重依赖在 3.14 上装失败）；
- 每题生成 `repo/solution.py`（complete_prompt 桩）+ 隐藏测试（import task_func + unittest）；
- 种子桩**必失败**（函数体为空），保证任务有效；
- 判分 = 隐藏测试全过 → PASS；另加 LLM-judge。

验收标准（`tests/specs/test_bigcodebench.py`）：
- B1 种子桩加载后隐藏测试失败（任务有效）；
- B2 `_stdlib_only` 正确过滤掉含外部库的题；
- B3 `_make_task` 生成的 repo 有 solution.py 桩、hidden_tests 有 test_solution.py（含 `from solution import task_func`）；
- B4 `load_bigcodebench(limit=5)` 返回 5 个 Task，字段齐全。
