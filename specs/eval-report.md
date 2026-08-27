# eval-report.md — 报告聚合 (Phase 5, B8)

职责：把一批 `EvalRecord` 聚合成可读报告（通过率、平均耗时、token 数、各维度分数），供复盘与演示。
接口：`summarize(records: list[EvalRecord]) -> dict[str, object]`；`render_markdown(summary) -> str`。

行为：
- `summarize` 计算通过率、平均耗时、平均 token、每题 PASS/FAIL、各 rubric 维度均分；
- `render_markdown` 输出 markdown 表格/段落报告。

验收标准（可自动验证，`tests/specs/test_eval_report.py`）：
- ER1 聚合含通过率、平均耗时、平均 token；
- ER2 含每题判定的明细；
- ER3 含 rubric 维度均分；
- ER4 `render_markdown` 产出含这些数值的 markdown。
