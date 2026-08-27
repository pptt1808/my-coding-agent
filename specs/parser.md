# parser.md — 模型输出/工具调用解析 (N4)

职责：把模型一轮输出解析为可执行的工具调用。**优先走原生 tool calling**；若厂商/网关返回畸形或纯文本，回退到正则/JSON 解析（B10）。
接口：`parse_tool_calls(result: LLMResult) -> list[ToolCall]`；`parse_tool_call_from_text(text: str) -> ToolCall | None`。

行为：
- 原生路径：直接透传 `LLMResult.tool_calls`；
- 文本兜底：从模型文本中扫出工具块（如 `<!-- TOOL name=... args={...} -->` 或 JSON）解析；
- 参数解析成 `dict`，类型为字符串/数值等原生类型；
- 无法解析 → 返回 `None` 或抛 `ModelOutputError`（不崩溃循环，见 errors.md）。

验收标准（可自动验证，`tests/specs/test_parser.py`）：
- P1 原生路径正确透传结构化 tool calls；
- P2 文本兜底成功解析单个工具调用（name + arguments dict）；
- P3 畸形/不可解析文本返回 `None` 或抛 `ModelOutputError`；
- P4 解析出的 arguments 为正确类型的 dict。
