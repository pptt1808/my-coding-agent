# tasklist.md — /task 任务清单 (A3/P1)

职责：让 agent 维护显式 todo 列表（目标/当前子任务/完成项），长任务不迷失、进度对用户透明；清单注入每轮 system prompt，模型可见。
接口：`ReplSession` 维护 `todos: list[str]`；slash 命令 `/task add <text>`、`/task list`、`/task done <n>`、`/task clear`；每轮 system prompt 追加任务清单块。

行为：
- `/task add` 追加条目；
- `/task list` 编号显示；
- `/task done n` 删除第 n 条（视为完成）；
- `/task clear` 清空；
- 任务清单块在每轮通过 `run_turn(messages, extra_system=...)` 注入 system prompt。

验收标准（`tests/specs/test_tasklist.py`）：
- T1 `/task add` 后下一轮 system prompt 包含该条目；
- T2 `/task list` 显示全部条目；
- T3 `/task done 1` 删除第 1 条；
- T4 `/task clear` 清空清单。
