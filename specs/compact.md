# compact.md — 会话压缩 (B1/P0, B2/P1)

职责：把长会话压成结构化摘要（目标 / 已确认事实 / 已完成 / 待做 / 下一步），对抗长会话上下文衰减；与启发式 `summarize_oldest`（自动兜底）互补。
接口：`summarize_conversation(llm, messages) -> str`；`CodingAgent.compact(messages) -> list[dict]`；`config.auto_compact_at_tokens`（>0 开启自动压缩）。

行为：
- 用 LLM 生成结构化摘要（非启发式截断）；
- compact 后历史被单个"摘要 user 消息"替换，可继续后续轮次；
- 空历史直接返回 `[]` 且**不调用 LLM**；
- **自动 compact（P1）**：循环中 token 估算超过 `auto_compact_at_tokens` 阈值时自动触发 compact，替换后续上下文。

验收标准（`tests/specs/test_compact.py`）：
- CP1 `summarize_conversation` 返回 LLM 摘要文本；
- CP2 `compact` 后历史为单个含摘要的消息；
- CP3 空历史 `compact` 返回 `[]` 且 LLM 零调用；
- CP4（P1）`auto_compact_at_tokens` 开启时，循环内历史会被自动压缩（后续 LLM 调用看到 `[compacted conversation]` 开头的历史）。
