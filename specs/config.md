# config.md — 配置加载 (N1)

职责：从环境变量 / `.env` 读取 API key、网关 base_url、model、workdir 与循环限制，作为一切运行的起点。
接口：`Config.from_env(env_file: str | Path | None = None) -> Config`（frozen dataclass）。

行为：
- key 从 `API_KEY` 或 `OPENAI_API_KEY` 读取；
- 未提供 key 时抛出**清晰错误**（不静默使用空值）；
- 可选变量缺省时应用默认值；
- `workdir` 解析为绝对路径，约束 agent 只能在其中工作。

验收标准（可自动验证，`tests/specs/test_config.py` 已实现并转绿）：
- C1 从 `API_KEY` 或 `OPENAI_API_KEY` 读到 key；
- C2 无 key 时抛 `ValueError`（含 "API key" 提示）；
- C3 缺省时应用默认值（model=gpt-4o-mini、base_url=https://api.openai.com/v1、max_steps=25）；
- C4 `workdir` 解析后为绝对路径；
- C5 未设 `EVAL_MODEL` 时，评测模型回退到 `MODEL`（`eval_model_name == model`）；
- C6 设置 `EVAL_MODEL` 时，评测模型独立分层（`eval_model_name == EVAL_MODEL`）；
- C7（工作区）未显式指定时，`.env` 按 `<cwd>/.env` → `<包根>/.env` → `~/.coding-agent/.env` 顺序查找（`CODING_AGENT_ENV` 显式指定则只用它）；
- C8 `--workdir` 可显式覆盖工作区（`apply_workdir`），未指定时保持原配置。

模型分层：交互/开发走 `MODEL`（便宜档，如 deepseek-v4-flash），评测 harness 走 `EVAL_MODEL`
（强档，如 deepseek-v4-pro）；`LLMClient(model=...)` 可按层选择，CLI `run --model` 可临时覆盖。

工作区选择（与其他 coding agent 一致）：`cd <你的项目> && coding-agent chat` 即在该目录工作；
或从任意位置 `coding-agent chat --workdir <路径>` 显式指定。

> 信任边界：key 只允许来自环境变量/未入库 `.env`，**绝不写入仓库**（见 `.gitignore`）。
