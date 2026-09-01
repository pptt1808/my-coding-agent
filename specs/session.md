# session.md — 会话持久化 (A2/P1)

职责：把会话（消息历史、模型、workdir、用量统计）保存到磁盘，支持中断后恢复。
接口：`agent/session.py`：`Session` dataclass；`save_session(session, workdir) -> Path`；`load_session(workdir, id) -> Session`；`list_sessions(workdir) -> list[Session]`；`new_session_id() -> str`。
存储位置：`<workdir>/.coding-agent/sessions/<id>.json`（该目录被 grep/工具跳过，不污染 agent 视野）。

行为：
- `/save [name]` 保存当前会话，id 为 name 或自动生成；
- `/resume` 无参时列出已保存会话并编号（供用户选择）；`/resume <n>` 按编号恢复；`/resume <name>` 按 id 恢复；恢复消息/模型/统计，workdir 不同时重建 agent（并保留 trace/tools 配置）；
- `/ls` 列出已保存会话（id、更新时间、消息数）；
- 保存内容包括 messages、model、workdir、steps、total/input/output tokens。

验收标准（`tests/specs/test_session.py`）：
- S1 `save_session` 写入 JSON，`load_session` 读回字段一致；
- S2 `list_sessions` 按时间倒序列出，坏文件跳过；
- S3 `load_session` 不存在的 id 抛 `FileNotFoundError`；
- S4 `/resume` 后历史与统计恢复（下一轮消息沿用保存的历史）。
