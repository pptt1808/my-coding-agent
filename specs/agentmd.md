# agentmd.md — 持久项目上下文 (AGENT.md / PM_PROFILE.md) (#3)

职责：像 Claude Code 的 `CLAUDE.md` 一样，让 agent **读取项目/用户的持久约定**并注入上下文，避免重复交代：
- 通用循环读 `<workdir>/AGENT.md`（项目约定，注入为 `PROJECT CONVENTIONS (AGENT.md)`）；
- PM 模式读 `<workdir>/PM_PROFILE.md`（用户 PM 偏好：演示风格/受众默认/time-box，注入 persona）。
接口：`config.agent_md`/`agent_md_chars`；`agent/loop.py` run_turn 自动读取；`agent/pm.py` create 自动读取。

行为：
- 若文件存在，读取（上限 `agent_md_chars`）并追加到 system prompt / persona；
- 不存在则不影响；读取异常被吞（不阻塞）。

验收标准（`tests/specs/test_agentmd.py`）：
- M1 AGENT.md 存在 → system prompt 含 `PROJECT CONVENTIONS (AGENT.md)` + 其内容；
- M2 无 AGENT.md → 无该块；
- M3 超长 AGENT.md 被 `agent_md_chars` 截断；
- M4 PM_PROFILE.md → PmSession persona 含 `USER PM PROFILE` + 内容。
