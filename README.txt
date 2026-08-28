编程智能体 coding-agent

【Git 仓库】
https://github.com/你的用户名/coding-agent   （提交前请替换为真实公开仓库地址）

【如何运行】
1. Python 3.11+，pip install -e ".[dev]"
2. cp .env.example .env，填入 API_KEY、BASE_URL、MODEL
3. 交互式使用：coding-agent chat
   命令：/help /clear /compact /status /cost /model /task /save /resume /review /permissions
4. 一次性任务：coding-agent run "修复 src/util.py 的 bug"
5. 自动评测：python -m eval tasks

【特色功能】
- 完全自研 agent 循环：上下文管理、工具定义与本地执行、模型输出解析、循环终止、错误处理均自行实现，未使用任何 agent 框架
- 工具集：read_file / write_file / edit_file / append_file / bash / list_dir / glob / grep，含工作目录围栏与危险命令黑名单
- 模型分层：开发用 flash、评测用 pro，OpenAI 兼容网关一键切换
- AI 可驱动自动评测：SWE-bench 式隐藏测试判定 + LLM-judge 质量评分 + 轨迹/耗时/token 报告
- 交互式会话：任务清单 /task、LLM 摘要压缩 /compact、会话持久化 /resume、自查 /review

【其它】
- 123 个契约测试全绿；6 级难度任务集（L1-L6）真实评测通过
- API key 仅存于未入库的 .env，不进入仓库
