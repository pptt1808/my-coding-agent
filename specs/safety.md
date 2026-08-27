# safety.md — 权限与安全模型 (B4, T2)

职责：约束 agent 只能影响其 workdir，并拦截危险命令，防止破坏宿主或泄露凭据。优先"目录白名单 + 危险命令黑名单"，docker 沙箱留作后期增强。
接口：`tools.shell` 在 `bash()` 内检查命令；`tools.file_ops` 的路径统一解析到 workdir 内。

行为：
- 解析路径必须落在 workdir 内（防 `..` / 绝对路径逃逸）；
- 危险命令黑名单（如 `rm -rf /`、`git push --force`、`sudo` 等）直接拦截并返回错误；
- 黑名单可配置（`config` / 环境变量）；
- 可选：交互模式逐命令确认（T2）。

验收标准（可自动验证，`tests/specs/test_safety.py`）：
- S1 危险命令（如 `rm -rf /`）被拦截并返回明确错误；
- S2 路径解析逃逸 workdir（`../`、绝对路径）被拒绝；
- S3 黑名单可由配置扩展；
- S4（可选交互模式）逐命令确认时会提示。
