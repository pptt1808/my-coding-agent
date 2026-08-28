# multi-agent.md — 多 agent 编排与探索 subagent (Phase A)

职责：像 Codex 那样，在**必要**时先用便宜、只读的**探索 subagent** 收集项目详情（brief），再注入主力 agent，避免主 agent 重头探索与上下文膨胀。
**最高优先约束：subagent 的启动时机——没必要时绝不启用。**

接口：`agent/multi.py`：`collect_repo_stats(workdir) -> RepoStats`；`should_explore(config, stats=None, explicit=0) -> bool`；`run_explore(config, task, llm=None, trace=False) -> str`（brief）；`orchestrate(config, task, ...) -> (answer, brief|None)`。`coding-agent run "task" [--explore|--no-explore]`；REPL `/explore`。

行为：
- `should_explore` 决断（确定性、零模型调用）：
  - `explicit=+1`（--explore）强制开；`explicit=-1`（--no-explore）强制关；
  - `AUTO_EXPLORE=off`（默认）→ 恒 False；`always` → 恒 True；`auto` → 仅当 repo 越过规模阈值（文件数/LOC/顶层模块数）；
- `run_explore`：便宜档（`explore_model_name`），**只读**工具白名单（read/list/glob/grep，write/edit/bash 被拦），步数上限 `explore_max_steps`，简报 ≤ `explore_brief_chars`；
- `orchestrate`：仅当 `should_explore` 为真才派探索 subagent；探索失败 → 降级单 agent；主力 agent 的 system prompt 注入 `brief_block(brief)`（而非原始文件输出）。

验收标准（`tests/specs/test_multi_agent.py`）：
- E1 小仓库（默认 off）→ `should_explore` False，`orchestrate` 不派探索 subagent、无额外模型调用；
- E2 大仓库（`auto`）→ `should_explore` True；
- E3 `--explore` / `--no-explore` 覆盖优先级最高；
- E4 `AUTO_EXPLORE=off/always/auto` 三态；
- E5 探索 agent 只读：write_file/edit_file/bash 工具被拦截（回填"not enabled"），不修改文件；
- E6 简报有界（≤ `explore_brief_chars`）；
- E7 主力 agent 收到的是 brief 块（`PROJECT BRIEF ...`），而非原始文件 dump。

### Phase B（planner + 并行 fan-out，均默认关）
- `parse_todos(text) -> list[str]`：把 planner 的数字/符号输出解析为 todo 列表（≤10，去编号）；
- `plan_block(todos)`：`PLAN (from the planner subagent ...)` 块；
- `run_planner(config, task, brief, llm=None, trace=False) -> list[str]`：cheap planner（无工具纯推理），brief+task → todo；
- `parallel_explore(config, task, modules=None, llms=None, trace=False) -> str`：每个顶层模块一个只读 explore agent（`workdir=<repo>/<module>`），线程并发，合并为有界 brief；
- `orchestrate`：`PARALLEL_EXPLORE=auto/always` 且顶层模块数 ≥ `explore_fanout_min_modules` → fan-out；`AUTO_PLAN=auto/always` → 注入 `plan_block`；二者都默认 off。

验收标准（追加）：
- P1 `parse_todos` 去编号/符号，≤10 条；
- P2 `run_planner`（假 LLM 返回编号列表）→ todo；`plan_block` 含 `PLAN` 头；
- P3 `orchestrate` 开 `auto_plan` 时，implement 的 system prompt 同时含 `PROJECT BRIEF` 与 `PLAN` 块；
- F1 `parallel_explore` 为每个顶层模块产出一个带 `[模块名]` 标签的 brief，合并后有界；
- F2 `orchestrate` 开 `parallel_explore=auto` 且模块数达标时走 fan-out（多模块标签）；不达标时仍走单 explore。
