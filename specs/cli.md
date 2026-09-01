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
- R9 `/save [name]` 保存、`/resume` 列出并编号选择（或 `/resume <id>` / `/resume <n>`）恢复历史与统计（下一轮沿用保存的历史）；
- R10 `/cost` 含 input/output/total token 信息；
- R11（流式）`chat`/`run` 默认流式输出：模型 token 到达即打印，最终回答不重复输出；`--no-stream` 可关闭；流式时工具调用轮次不输出文本；
- R12（指令菜单 / 补全）`/` 作为**真实字符**回显；交互编辑器采用**整屏重绘**（同 prompt_toolkit / OpenCode 之法）：每次按键从稳定原点半屏重绘，仅在**当前输入以 `/` 开头**时，在输入行下方画出**补全候选**（按已输入前缀过滤，覆盖全部 COMMANDS，含 PM 六条 `/vision /story /mvp /validate /polish /pitch`），否则不画；**画完把光标移回输入行文本末尾**（用 ANSI 上移），保证后续输入/退格始终作用于 `/` 之后而不是候选列表。因此删除 `/` → 下一帧菜单自动消失；回车提交命令前也先收起菜单。`/前缀` 唯一匹配时自动展开执行（如 `/comp`→`/compact`），多匹配提示歧义，未知命令列出可用命令；**全角 `／`（中文输入法）按 `/` 处理**；
- R13（输入气泡）`echo_input=True` 时，普通输入以带边框的"聊天框"回显（含"你"前缀），与 agent 输出区分；默认关闭，由 CLI 开启；交互模式下气泡**替换**提示符处已回显的那行输入（即同一句输入只显示一次，被气泡就地承载），普通消息在 Enter 时清掉该行，指令（`/`）保留正常换行；
- R15（粘贴多行输入）交互读取器区分"粘贴突发"与"主动回车"：单独的 `\n` 永不作为提交，始终作为输入的一部分收集；`\r` 后用**单字符前瞻**判断——若紧随 `\n`（CRLF 粘贴换行）则合并为单个 `\n` 继续收集，否则（无后续字符）才是"真正的回车"提交。前瞻带极短等待（≤12ms），避免粘贴瞬间 `kbhit()` 抖动误判，从而保证从文档/`TASK.md` 粘贴多行任务会作为**一条**输入交给 agent，而不是每行提交一次；
- R14（中断）`Ctrl+C`：提示符处按下 → 干净退出（不打印 traceback）；回合进行中按下 → 取消当前回合、丢弃部分输出并恢复回合前消息，回到提示符；`run` 模式按下 → 打印 interrupted 后以退出码 130 结束；
- U1 `/undo` 将工作目录回滚到上一回合前（快照）；U2 `/redo` 重新应用；U3 多次 undo 逐级回退；U4 undo 移除 agent 新建的文件（恢复被删文件）。
