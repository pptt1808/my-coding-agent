# context.md — 对话历史与上下文管理 (N7, B7)

职责：组织回填给模型的上下文。默认**全量携带**，超限时对最早轮次做摘要，并**截断大输出**（长文件/长命令 stdout），控制 token 且保证可解释。
接口：`History(max_tokens=...)`，`.append(msg)`、`.as_list()`、`.truncate_large_output(text, cap) -> str`、`.summarize_oldest()`。

行为：
- `truncate_large_output` 超过 `cap` 时截断头部并加 `... [truncated N chars]` 标记；
- 短文本原样返回；
- `as_list()` 返回副本，不暴露内部可变数组；
- T1 阶段：`summarize_oldest` 把最早消息压缩为摘要，使总 token 不超过 `max_tokens`。

验收标准（可自动验证，`tests/specs/test_context.py`）：
- CT1 `append` 保持消息顺序；
- CT2 长文本被截断且带省略标记；
- CT3 短文本原样返回；
- CT4 `as_list()` 返回副本（内部修改不影响外部）；
- CT5（T1）`summarize_oldest` 后历史 token 低于上限。
