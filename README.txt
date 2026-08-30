编程智能体 coding-agent

【Git 仓库】
https://github.com/pptt1808/my-coding-agent

【如何运行】
1. Python 3.11+，pip install -e ".[dev]"
2. cp .env.example .env，填入 API_KEY、BASE_URL、MODEL
3. 交互式：coding-agent chat（流式、气泡输入、输入 / 出菜单）
   命令：/help /clear /compact /status /cost /model /task /save /resume /review /undo /redo /explore /plan /codemap /permissions /skills /skill /pm
4. 一次性：coding-agent run "修复 src/util.py 的 bug"；多 agent：--explore
5. PM 演示模式：chat 里输入 /pm 激活（/vision /story /mvp /validate /polish /pitch，同一 agent）
6. 自动评测：python -m eval tasks；BigCodeBench：python tools/run_bigcodebench.py --limit 30

【特色功能】
- 完全自研 agent 循环：上下文管理、工具定义与本地执行、模型输出解析、循环终止、错误处理均自行实现，未使用任何 agent 框架
- 工具集：read/write/edit/append/bash/list_dir/glob/grep，含工作目录围栏与危险命令黑名单
- 模型分层：开发用 flash、评测用 pro，OpenAI 兼容网关一键切换；token 预算上限 + 自动压缩（Claude Code 式）+ API 重试
- AI 可驱动自动评测：SWE-bench 式隐藏测试 + LLM-judge 质量分 + 成本/耗时/token 报告（6 级梯度任务 + BigCodeBench 40%）
- Aider 式 repo-map（代码符号地图）+ AGENT.md 项目约定 + /undo 检查点
- **PM 演示模式**：澄清门→spec→确认→最小可运行→validate 反馈→story/pitch，四件产品交付物（个人原创）

【其它】
- 179 个契约测试全绿；36+ 条提交；spec-driven（先 spec→契约测试→实现）
- API key 仅存于未入库的 .env，不进入仓库
