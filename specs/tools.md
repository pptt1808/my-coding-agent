# tools.md — local tools (N3)

职责：定义并本地执行 agent 可用的工具；返回字符串结果以安全回填给模型。

## read_file
- 接口：`read_file(path: str) -> str`
- 行为：
  - `path` 相对/绝对路径均可（须解析到安全 workdir 内）；
  - 文件不存在 → 返回明确错误文本，**不抛异常崩溃**；
  - 超长文件 → 截断，加 `... [truncated N chars]` 标记。
- 验收标准（可自动验证）：
  - A1 正常读文件返回全文；
  - A2 读不存在的文件返回错误文本且不崩溃；
  - A3 超长文件被截断且带省略标记。

## write_file
- 接口：`write_file(path: str, content: str) -> str`
- 行为：写入（覆盖）文件并返回简短确认。
- 验收标准（可自动验证）：
  - B1 写入后文件内容正确；
  - B2 返回非空确认字符串。

## bash
- 接口：`bash(command: str) -> str`
- 行为：带超时执行命令，捕获 stdout/stderr（截断），超时/失败返回干净错误文本；遵守危险命令黑名单（B4）。
- 验收标准（可自动验证）：
  - C1 正常命令返回其输出；
  - C2 失败命令返回错误文本且不崩溃；
  - C3 超时命令被终止并返回超时错误；
  - C4 危险命令（如 `rm -rf /`）被拦截。

> 契约测试：`tests/specs/test_tools.py`（Phase 1 实现 file_ops/shell 时补 A1-C4）。
