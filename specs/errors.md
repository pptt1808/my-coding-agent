# errors.md — 错误处理 (N6)

职责：统一承接工具异常、模型输出畸形、超时与重试，把失败以"安全文本"回填给模型，**绝不让循环因错误崩溃**。
接口：`AgentError`（基类）、`ToolError(msg)`、`ModelOutputError`、`TimeoutError`。

行为：
- `ToolError` 携带可安全回填给模型的 `message`；
- 输出无法解析 → `ModelOutputError`；
- 命令超时 → `TimeoutError`；
- 工具层错误由 `tools.registry.dispatch` 捕获并转成字符串结果（见 tools.md），不向上传播打断循环。

验收标准（可自动验证，`tests/specs/test_errors.py`）：
- E1 `ToolError.message` 可回填为文本；
- E2 `ModelOutputError` 用于不可解析输出；
- E3 `TimeoutError` 用于超时；
- E4 `dispatch` 捕获工具内部异常并返回错误字符串，不抛出。
