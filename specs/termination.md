# termination.md — 循环终止条件 (N5, B11)

职责：组合多重阈值，确保 agent 循环**总会停止**，避免死循环/无限调工具/浪费 token。
接口：`Terminator(config).should_stop(state: LoopState, elapsed_s: float) -> bool`；`LoopState`（steps / tool_calls / consecutive_failures / done）。

行为：
- 达到任一条件即停：done、步数上限、工具调用数上限；
- T1 阶段还叠加：无实质进展（**完全相同的工具调用**：同工具+同参数，探索不同文件不算无进展）、连续失败阈值、超时；
- 默认按 B11 多重阈值组合，threshold 来自 `Config`。

验收标准（可自动验证，`tests/specs/test_termination.py`）：
- T1 `state.done=True` 时停止；
- T2 `steps >= max_steps` 时停止；
- T3 `tool_calls >= max_tool_calls` 时停止；
- T4（T1）连续失败达阈值时停止；
- T5（T1）重复相同工具调用（无进展）时停止；
- T6（T1）`elapsed_s` 超时停止。
