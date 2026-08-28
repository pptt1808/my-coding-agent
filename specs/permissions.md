# permissions.md — 权限查看与调整 (C3/P2)

职责：让用户在会话中查看/扩展安全黑名单与工作目录围栏（静态黑名单的交互补充）。
接口：`ReplSession` 命令 `/permissions`（显示 workdir + 黑名单）、`/permissions block <pattern>`（会话内追加黑名单）、`/permissions reset`（恢复默认黑名单）；通过 `tools.context.configure(extra_blacklist=...)` 实现。

行为：
- 显示当前 workdir 与危险命令黑名单；
- `block` 追加模式（仅本会话生效）；
- `reset` 恢复默认黑名单。

验收标准（`tests/specs/test_permissions.py`）：
- P1 `/permissions` 显示 workdir 与黑名单；
- P2 `block` 后 bash 执行该模式命令被拦截；
- P3 `reset` 后拦截失效（恢复默认）。
