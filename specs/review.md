# review.md — /review 自查改动 (D1/P2)

职责：让 agent 自查本会话内的改动：计算 diff → 跑测试 → 复用 LLM-judge 打质量分，提交前把关。
接口：`ReplSession` 命令 `/review`；`agent/diff.py`：`collect_diff(before: dict[str,str], after: dict[str,str]) -> str`（或 `collect_diff_dirs(before_dir, after_dir)`）；会话开始时对 workdir 做文件快照。

行为：
- 快照与当前工作区差异 → diff 文本；
- 无改动时提示"nothing to review"；
- 有 pytest 测试时先跑测试并报告结果；
- judge 按默认 rubric（correctness/quality/minimal）打分并给出理由。

验收标准（`tests/specs/test_review.py`）：
- RV1 有改动时 `/review` 输出包含改动文件信息；
- RV2 `/review` 输出含 judge 分数；
- RV3 无改动时输出 nothing to review；
- RV4 `collect_diff` 正确产出新旧内容的 unified diff。
