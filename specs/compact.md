# compact.md — 会话压缩 (B1/P0)

职责：把长会话压成结构化摘要（目标 / 已确认事实 / 已完成 / 待做 / 下一步），对抗长会话上下文衰减；与启发式 `summarize_oldest`（自动兜底）互补。
接口：`summarize_conversation(llm, messages) -> str`；`CodingAgent.compact(messages) -> list[dict]`。

行为：
- 用 LLM 生成结构化摘要（非启发式截断）；
- compact 后历史被单个"摘要 user 消息"替换，可继续后续轮次；
- 空历史直接返回 `[]` 且**不调用 LLM**。

验收标准（`tests/specs/test_compact.py`）：
- CP1 `summarize_conversation` 返回 LLM 摘要文本；
- CP2 `compact` 后历史为单个含摘要的消息；
- CP3 空历史 `compact` 返回 `[]` 且 LLM 零调用。
