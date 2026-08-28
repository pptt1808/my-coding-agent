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
- R10 `/cost` 含 input/output/total token 信息；
- R11（流式）`chat`/`run` 默认流式输出：模型 token 到达即打印，最终回答不重复输出；`--no-stream` 可关闭；流式时工具调用轮次不输出文本；
- R12（指令菜单）输入 `/`（单独）显示全部可用命令；`/前缀` 唯一匹配时自动展开执行（如 `/comp`→`/compact`），多匹配提示歧义，未知命令列出可用命令；**全角 `／`（中文输入法）按 `/` 处理**；
- R13（输入气泡）`echo_input=True` 时，普通输入以带边框的"聊天框"回显（含"你"前缀），与 agent 输出区分；默认关闭，由 CLI 开启；
- R14（中断）`Ctrl+C`：提示符处按下 → 干净退出（不打印 traceback）；回合进行中按下 → 取消当前回合、丢弃部分输出并恢复回合前消息，回到提示符；`run` 模式按下 → 打印 interrupted 后以退出码 130 结束。
