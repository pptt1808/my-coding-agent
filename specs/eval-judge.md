# eval-judge.md — LLM 裁判 / rubric 评分 (Phase 6, B8)

职责：对确定性测试覆盖不到的质量维度（代码质量、是否贴题、是否最小改动、是否符合约定）用 LLM-as-judge 打分，作为主观补充。
接口：`score(trajectory: str, final_diff: str, rubric: dict[str, str]) -> dict[str, float]`。

行为：
- 提示词给出任务、agent 轨迹、最终改动 → 要求 judge 对 rubric 每个维度打 0–5 分并附一句话理由；
- 返回"维度→分数"字典；
- 可再聚合为整体分。

验收标准（可自动验证，`tests/specs/test_eval_judge.py`）：
- EJ1 每个 rubric 维度返回一个 0–5 分；
- EJ2 含整体 grade 与一句话理由；
- EJ3 维度缺失时跳过或返回中性分，不崩溃；
- EJ4 空 rubric 返回空分数表。
