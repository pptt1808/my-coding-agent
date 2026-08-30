# repomap.md — Aider 式代码库地图 (#1)

职责：用 `ast` 把代码库的**符号（类/函数/方法）**做成一页**紧凑代码地图**，缓存后注入 agent 的系统上下文——让模型**不用重读全库**就知道结构（参考 [Aider Repository Map](https://aider.chat/docs/repomap.html)）。
接口：`agent/repomap.py`：`build_repo_map(workdir, max_chars) -> str`；`code_map(workdir, max_chars) -> str`（按内容指纹缓存于 workdir/.coding-agent/repomap.txt）；`config.code_map`/`code_map_chars`；REPL `/codemap`。

行为：
- 遍历 `.py` 文件，AST 解析出顶层 `class`/`def` + 类内 `method`（含参数签名），按 `<file> -> symbols` 组织；
- 纯文本、`max_chars` 上限超长截断；跳过噪声目录（.git/__pycache__/.venv/demo 等）；
- 缓存按**文件 mtime+size 指纹**失效重建，避免每轮重解析；
- 注入：`run_turn` 在 system prompt 追加 `CODE MAP (...)` 块；`/codemap` 查看。

验收标准（`tests/specs/test_repomap.py`）：
- R1 `build_repo_map` 提取 .py 的类/函数/方法（含签名）；
- R2 超过 `max_chars` 被截断并带标记；
- R3 跳过噪声目录（.venv/demo）；非 .py 文件不进入符号表；
- R4 `code_map` 缓存：首次构建、未变更时二次调用不重解析（内容一致）；
- R5 注入：`CodingAgent` 的 system prompt 含 `CODE MAP` 块（`code_map=True` 时）。
