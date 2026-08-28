# cli.md — 交互式 REPL 与 slash 命令 (A1/P0)

职责：把一次性 `run` 升级为交互式会话：普通输入 = 新一轮任务（共享历史），`/` 开头 = 会话控制命令。
接口：`coding-agent chat [--model X] [--trace]`；`ReplSession(config, llm=..., model=...).handle(line) -> list[str]`。

行为：
- 普通行作为新用户消息加入历史并运行一轮 agent，返回最终回答（连续多轮共享历史）；
- slash 命令：`/help`、`/exit`、`/clear`、`/compact`、`/status`、`/model <name>`（P0）；
- P1 新增：`/save [name]`、`/resume <name>`、`/ls`（会话持久化）、`/task add|list|done|clear`（任务清单）、`/cost`（用量统计）；
- P2 新增：`/review`（自查改动 + judge 评分）、`/permissions [block <pattern>|reset]`（权限查看/调整）；`--tools read_file,edit_file`（工具按需裁剪，run 与 chat 均支持）；大输出改为**尾部优先**截断；
- `/compact`：用 LLM 把会话压成结构化摘要，历史被替换为摘要消息；
- `/status`：显示模型 / workdir / 步数 / token / 消息数；
- `/exit` 终止会话；未知命令给出帮助提示且不崩溃。

验收标准（`tests/specs/test_repl.py`）：
- R1 普通输入运行一轮并返回回答；
- R2 连续轮次保留历史（下一轮消息能看到上一轮内容）；
- R3 `/exit` 终止会话（running=False）；
- R4 `/clear` 清空历史（下一轮只含新消息）；
- R5 `/status` 含模型名与 token 信息；
- R6 `/compact` 后历史被摘要替换（下一轮首条消息含摘要）；
- R7 未知命令返回帮助提示且不崩溃；
- R8 `/model <name>` 切换后 `/status` 显示新模型名；
- R9 `/save name` + `/resume name` 恢复历史与统计（下一轮沿用保存的历史）；
- R10 `/cost` 含 input/output/total token 信息。
