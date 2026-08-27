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
- C4 `workdir` 解析后为绝对路径。

> 信任边界：key 只允许来自环境变量/未入库 `.env`，**绝不写入仓库**（见 `.gitignore`）。
