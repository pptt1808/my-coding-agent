# 多 Agent 协作方案（先探索后实现的设计）

> 目标：像 Codex 那样，在复杂/大型项目下**先用便宜模型做"检索/探索 agent"收集项目详情**，再交给主力 agent 干活——省 token、加快上下文就位、提高准确率。
> 约束：题目禁止 agent 框架/SDK，因此整套多 agent 层也**必须自研**（复用我们已有的 agent 循环、工具注册、评测 harness）。

## 1. 开源实现参考

### 1.1 Codex（OpenAI）
- **官方 Subagents**：https://developers.openai.com/codex/subagents —— 一次主任务可派生出多个子 agent，各自有独立上下文与工具，最终汇总；**Web 端有后台 agent 在跑**（多人并行 fan-out）。
- **Codex CLI 源码**（Rust，7 万+ star）：用"orchestrator + 子任务 + 结果汇总"的结构。
- 借鉴点：**子 agent 独立上下文 + 主 agent 只收汇总结果**（不吞全部原始 context）。

### 1.2 Claude Code
- **Sub-agents**：https://code.claude.com/docs/zh-CN/sub-agents —— 自定义子 agent，可指定**独立模型**与**作用域（特定文件/目录）**；用于"把子任务外包给更便宜/更专注的 agent"。
- **Orchestrator-Workers 模式**（cookbook）：https://platform.claude.com/cookbook/patterns-agents-orchestrator-workers —— **Planner 拆解任务 → Workers 并行执行 → 汇总**。
- **Pre-Execution Codebase Exploration**（agentpatterns）：https://raw.githubusercontent.com/agentpatterns-ai/website/refs/heads/main/workflows/pre-execution-codebase-exploration.md —— **执行前先探索代码库**的专有工作流，正是我们要的。
- 借鉴点：子 agent 可换模型、可限定范围；**先探索→再实现**是官方实践。

### 1.3 OpenCode
- **Agents 与 Subagents**：https://github.com/wesammustafa/opencode-primer/blob/main/docs/agents.md —— agent 支持角色/权限/按需裁剪工具，易 fan-out。
- 借鉴点：**子 agent 的工具白名单**（探索 agent 只给只读工具）。

### 1.4 成本/效率实践（"便宜模型"论）
- **advisor-driven-dev**：https://github.com/PUSHINGSQUARES/advisor-driven-dev —— "Opus 规划、便宜模型执行，成本降 60-80%"。
- **Suber-Agent-Team**：https://github.com/stephenpham68/Suber-Agent-Team —— 把子 agent 外包给 Haiku 等便宜模型，20-100 并行 fan-out。
- **FastContext**（论文）：https://huggingface.co/papers/2606.14066 —— 专门训练"代码库探索器"模型。
- 借鉴点：**探索/执行用便宜档（我们已有 flash/pro 分层），正是这项设计的成本基础**。

### 1.5 一个必须正视的反例
- **Deep Agentic Search vs Semantic Search**：https://codex.danielvaughan.com/2026/08/13/deep-agentic-search-vs-semantic-search-repository-code-qa-codex-cli-subagent-delegation-context-rot/ —— 指出**把探索外包给子 agent 可能更贵且找到得更少**（相比语义检索）。所以我们的探索 agent 必须**便宜、设步数上限、只回传蒸馏后的简短摘要**，且对**小项目**默认不启用（开销不划算）。

## 2. 方案设计（自研，复用现有组件）

> **最高优先约束：subagent（探索/规划）绝不无谓启动。** 参考 Codex 反例（小项目派探索 agent 更贵更少），
> 默认**关闭**，只在"确定值得"时才启用；每次启用都有明确依据，且**可被测试断言"不该启用的场景绝不启用"**。

### 2.0 ★ 启动时机与门控（`should_explore`，不浪费任何模型调用）

```
should_explore(config, task, repo_stats) :
  1) 显式覆盖优先:
       --explore      → True      (用户强制开启)
       --no-explore   → False     (用户强制关闭)
  2) AUTO_EXPLORE 配置:
       off(默认)      → False
       always         → True
       auto           → 进入启发式判断(仅当 repo 足够"大/复杂"):
           repo_stats.n_files >= 200       (EXPLORE_MIN_FILES)
           or repo_stats.loc      >= 20000 (EXPLORE_MIN_LOC)
           or repo_stats.top_level_modules >= 6  (EXPLORE_MIN_MODULES)
        任一满足 → True，否则 False
```

- **成本原则**：`repo_stats` 用一次性 `os.walk` 统计（文件数/LOC/顶层模块数），**零模型调用**、零 token、毫秒级——绝不为"判断要不要探索"再花钱；
- **小/中仓库 → 恒不探索**，直接单 agent 干，避免开销倒挂；
- **A/B 实测（大任务 `large_task`，47 文件/7 模块，pro 档）**：单 agent 30.4s/23.5k tokens，多 agent（fan-out+planner）53.2s/**89.9k tokens**，结果均为 PASS、judge 5/5/5/5——**多 agent 对中量仓库是负收益**（+283% token / +75% 时间）。据此把默认阈值**调严**（min_files 50→200、min_loc 5000→20000、min_modules 3→6、fanout 4→8），该 47 文件任务不再触发；
- **可测试**：`should_explore` 契约测试——小仓库返回 False（无须子 agent）、大仓库返回 True、`--explore`/`--no-explore` 覆盖优先级、`AUTO_EXPLORE=auto/off/always` 三态；
- 配置项均走环境变量（`AUTO_EXPLORE`、`EXPLORE_MIN_FILES`、`EXPLORE_MIN_LOC`、`EXPLORE_MIN_MODULES`、`EXPLORE_MODEL`、`EXPLORE_MAX_STEPS`、`EXPLORE_BRIEF_CHARS`），阈值可调。

### 2.0.1 探索 agent 自身的"有界性"（防止它失控）
- 只读工具白名单（read/list/glob/grep）+ 非写工具；
- 步数上限 `EXPLORE_MAX_STEPS=6`；简报长度上限 `EXPLORE_BRIEF_CHARS=1500`；
- 短时任务（如"只看这个符号在哪定义"）不进入多 agent，直接用现有单 agent 的 grep/read。

### 2.0.2 运行时兜底
- 若 implement 发现 brief 不够用（如找不到关键文件），**回退到自己的探索**（现有工具自带），不阻塞、不二次派 agent；
- 探索失败（超时/空返回）→ 直接降级为单 agent 模式，任务照常执行。

### 2.1 核心链路：`探索 → 简报 → 实现 → (审查)`
```
主任务
  → EXPLORE(探索 agent, 便宜档 flash, 只读工具, 步数上限)
      → 产出【项目简报 brief】(结构/关键文件/相关代码位置/约定/可疑点, ≤~1500 字符)
  → PLANNER (可选, 用 brief+任务 生成 todo, 复用已实现的 /task 清单注入)
  → IMPLEMENT(主力 agent, 强档 pro, system prompt 注入 brief + todo)
      → 只改该改的地方，不再重头探索
  → REVIEW (复用已实现的 /review + LLM-judge 评分)
```

### 2.2 三个新增"Agent 角色"（都是同一个 CodingAgent 的实例，只是参数不同）
| 角色 | 模型档 | 工具白名单 | 步数上限 | 输出 |
|---|---|---|---|---|
| explore | flash（config.explore_model） | read_file / list_dir / glob / grep（**只读**） | 5-8 | 字符串 brief |
| planner | flash/pro | 无工具（纯推理，或仅写 todo） | 1-3 | todo 列表 |
| implement | pro（主力，默认） | 全量 8 工具 | 常规 | 最终改动 |

- 全部基于现有 `CodingAgent(config, model=..., tools=..., trace=...)`；explore/planner 是"**同构不同配置**的 agent 实例"——天然自研、无框架。
- **手写缓存/复用**：explore 不是无限跑，而是在一个独立子进程/隔离上下文里跑，**只把 brief 文本交回**给主 agent，主 agent 的上下文不会被原始文件输出撑爆（这正是 Codex "只收汇总"的原因）。

### 2.3 编排层（新模块 `agent/multi.py`）
- `Orchestrator(config, ...)`：
  1. 可选 `explore(task, brief_callback)` —— 用便宜档跑只读探索，收集 brief；
  2. 可选 `plan(task, brief)` —— 生成/注入 todo；
  3. `implement(task, brief, todo)` —— 主力 agent，system_prompt 里加"项目简报"块（用法类似现有 `extra_system` 注入任务清单）；
  4. 返回结果 + 各子 agent 的元信息（每个用了哪档模型、几步、多少 token、耗时）→ 喂给评测报告。
- **并行探索（进阶）**：大项目按顶层模块 fan-out 多个 explore agent（read-only 安全），参考 Suber-Agent-Team——属 Phase B。

### 2.4 与现有系统的整合
- **CLI**：`coding-agent run "task" --explore`（可选，大项目建议开）；或新增 `coding-agent plan "task"` 只返回 brief；`--model` 控制 implement 档。
- **REPL**：新增 `/explore`（跑探索并把 brief 注入当前会话上下文）、`/plan`；让用户手动先行探索。
- **评测 harness**：`eval/harness.py` 可加 `use_orchestrator` 开关；**用大任务对比单 agent vs 多 agent 的成本/时间/质量**（最有说服力的证据）。
- **开关**：默认对"小仓库"关闭（文件数/代码行阈值），避免 2.5 说的反例（小项目探索反而更贵）。

### 2.5 关键设计点（答辩可讲）
1. **为什么 cheap-first**：探索只读、琐碎、量大，用 flash 便宜档；实现用 pro 强档——成本由模型分层承担（advisor-driven-dev 的 60-80% 降本同理）。
2. **为什么只回传 brief**：原始 file 输出会撑爆主 agent 上下文（context rot）；蒸馏成 1500 字简报，主 agent 心智更聚焦。
3. **为什么工具白名单**：探索 agent 只给只读工具，杜绝误写；安全性由"工具围栏"复用。
4. **为什么默认关闭、按规模开启**：**subagent 的启动时机是第一约束**——小仓库派探索 agent 是负收益（更贵更少，见 Codex 反例）；只有 repo 跨过规模阈值、或用户显式要求时才启用；且判断本身零成本（一次性 walk 统计，不调模型）。
5. **诚实边界**：探索 agent 不一定找全；implement 保留回退能力，探索失败即降级单 agent。

## 3. 落地路线
- **Phase A（推荐先做，最高性价比）**：`explore → brief 注入 implement` 的单向串联 + `/explore` + `--explore`；用现有的 L3-L6 任务 + 一个新的大任务做 A/B 对比（单 agent vs 多 agent 的成本/时间/评测通过率/LLM-judge 分）。
- **Phase B**：`planner` 拆解 + `/plan`；并行多探索 agent fan-out（大仓库）。
- **Phase C**：supervisor 式——implement 在循环中**动态派生子 agent**（新增一个 `delegate` 工具），进入子 agent 处理特定子任务再回填。最接近 Codex 完整形态，但复杂，留作最后。

## 4. 需要你确认的决策点
1. explore 默认模型：flash（快省）/ 可配置（`EXPLORE_MODEL`）；
2. 是否默认开启：小项目关、大项目开（需要一个阈值，如文件数 > 50 或行数 > 5000）；
3. Phase A 先做串联+brief，还是直接上 planner 拆解；
4. 是否要并行 fan-out（Phase B）。
