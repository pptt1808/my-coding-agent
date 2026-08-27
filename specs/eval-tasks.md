# eval-tasks.md — 评测任务定义 (Phase 5)

职责：定义评测任务的数据结构与任务集加载，供 harness 运行与评分。
接口：`Task` dataclass（id / description / repo_seed / hidden_tests / baseline / rubric）；`load_tasks(tasks_dir: Path) -> list[Task]`。

行为：
- 一个任务 = 一个目录：`tasks/<id>/{repo/, DESCRIPTION.md, tests/, rubric.json?}`；
- `repo_seed` 为含种子代码的仓库；`hidden_tests` 为判定 PASS/FAIL 的测试；
- `rubric` 为可选 LLM-judge 维度说明（维度→描述）；
- 加载时字段缺失 → 抛出清晰错误，避免静默生成坏任务。

验收标准（可自动验证，`tests/specs/test_eval_tasks.py`）：
- EV1 `load_tasks` 每个任务目录加载一个 `Task`，字段齐全；
- EV2 缺少必填字段时报清晰错误；
- EV3 `rubric` 缺省为空 dict；
- EV4 `hidden_tests` 指向存在的测试文件/目录。
