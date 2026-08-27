# eval-harness.md — 评测 harness 运行 (Phase 5, B8/B9)

职责：在隔离环境跑一个任务并给出评分记录，模拟 SWE-bench：任务 → 干净环境 → 跑 agent → 收集改动 → 跑隐藏测试 → 判定 PASS/FAIL。
接口：`run_task(task: Task, workdir: str | None = None) -> EvalRecord`；`EvalRecord`（task_id / passed / rubric_scores / elapsed_s / tokens / trajectory）。

行为：
- 把 `repo_seed` 复制到**独立临时目录**（+ venv），agent 在其中完成任务；宿主席位不受污染；
- 全程记录轨迹（对话、工具调用、命令、结果、耗时、token）；
- 收集 agent 产物（diff / 最终工作区），应用后跑 `hidden_tests`：
  - 全部通过 → `passed=True`；
  - 有失败 → `passed=False`；
- T6 阶段：调用 `eval.judge` 填充 `rubric_scores`。

验收标准（可自动验证，`tests/specs/test_eval_harness.py`）：
- EH1 任务在独立临时目录运行（源 `repo_seed` 不被修改）；
- EH2 轨迹、耗时、token 被记录进 `EvalRecord`；
- EH3 隐藏测试全过 → `passed=True`，否则 `False`；
- EH4 隔离环境在任务结束后被清理。
