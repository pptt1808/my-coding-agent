# agent-loop.md — Agent 循环 (N2)

职责：最核心引擎。按序执行 `system prompt + history → LLM → 解析 tool call → 本地执行 → 结果回填 → 判断终止 → 循环`，直到完成或达到终止条件。
接口：`CodingAgent(config).run(task: str) -> str`；`build_system_prompt(workdir: str) -> str`。

行为：
- `run()` 返回 agent 的最终答案（字符串）；
- 工具调用经 `tools.registry.dispatch` 执行，结果以文本回填进历史；
- 每步检查 `termination`，满足即停止；
- 工具出错时**回填错误信息**（不中断循环，见 errors.md）；
- `build_system_prompt` 明确约束 agent 仅在其 workdir 内活动。

验收标准（可自动验证，`tests/specs/test_agent_loop.py`）：
- L1 `run()` 对可完成任务执行完整循环并返回非空答案；
- L2 工具被调用且结果回填到下一步消息；
- L3 满足终止条件（done/步数上限）时循环停止；
- L4 `build_system_prompt` 包含 workdir；
- L5 工具内部错误被转成回填文本，循环不崩溃。
