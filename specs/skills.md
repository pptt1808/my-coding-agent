# skills.md — Skill 系统 (Claude Agent Skills 式，自研)

职责：让 agent 拥有**可扩展、按需发现+加载**的能力包（skill），参照 Claude Agent Skills（`skills/<name>/SKILL.md`，YAML frontmatter name/description + 简短正文）。区别于硬编码的 slash 命令/工具——skill 是**用户可投放**的指令包。
接口：`agent/skills.py`：`discover_skills(workdir) -> [{name, description, path, dir}]`；`load_skill(workdir, name) -> str|None`；`skills_catalog_block(workdir) -> str`（发现目录）；`Skill` 工具（`skills_tool.skill`）；REPL `/skills`、`/skill <name>`；`config.skills`（默认开）。

行为：
- 扫描 `<workdir>/skills/` 与 `~/.coding-agent/skills/` 下的 `<name>/SKILL.md`；
- 解析 frontmatter（name/description）；正文为指令；
- 发现：system prompt 注入 `Available skills ...` 目录 + 暴露 `Skill(name)` 工具；模型遇匹配任务自动加载；
- 手动：`/skills` 列出，`/skill <name>` 把正文载入上下文；
- `Skill` 工具加载成功返回 `[skill:<name>]\n<body>`，未找到返回错误。

验收标准（`tests/specs/test_skills.py`）：
- S1 解析 frontmatter：`discover_skills` 返回 name/description；
- S2 `load_skill` 按名返回正文；不存在返回 None；
- S3 `skills_catalog_block` 列出 skill 目录；
- S4 `Skill` 工具：命中返回正文、未命中返回错误（不崩溃）；
- S5 无 skills/ 目录时目录块为空、`Skill` 未命中返回错误。
