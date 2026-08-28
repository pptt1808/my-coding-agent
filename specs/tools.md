# tools.md — local tools (N3)

职责：定义并本地执行 agent 可用的工具；返回字符串结果以安全回填给模型。

## read_file
- 接口：`read_file(path: str) -> str`
- 行为：
  - `path` 相对/绝对路径均可（须解析到安全 workdir 内）；
  - 文件不存在 → 返回明确错误文本，**不抛异常崩溃**；
  - 超长文件 → 截断，**保留尾部关键信息**（错误/结果通常在末尾），加省略标记。
- 验收标准（可自动验证）：
  - A1 正常读文件返回全文；
  - A2 读不存在的文件返回错误文本且不崩溃；
  - A3 超长文件被截断且带省略标记；
  - A3b（P2）截断后**尾部内容保留**（关键信息不丢）。

## write_file
- 接口：`write_file(path: str, content: str) -> str`
- 行为：写入（覆盖）文件并返回简短确认。
- 验收标准（可自动验证）：
  - B1 写入后文件内容正确；
  - B2 返回非空确认字符串。

## bash
- 接口：`bash(command: str) -> str`
- 行为：带超时执行命令，捕获 stdout/stderr，超时/失败返回干净错误文本；遵守危险命令黑名单（B4）；**超长输出尾部优先**截断（错误/结果通常在末尾）。
- 验收标准（可自动验证）：
  - C1 正常命令返回其输出；
  - C2 失败命令返回错误文本且不崩溃；
  - C3 超时命令被终止并返回超时错误；
  - C4 危险命令（如 `rm -rf /`）被拦截；
  - C4b（P2）超长输出截断后保留尾部。

## list_dir（T1）
- 接口：`list_dir(path: str = ".") -> str`
- 行为：列出目录条目（相对 workdir 解析），目录以 `/` 后缀；不存在 → 错误文本。
- 验收标准：
  - L1 返回目录内的条目（含子目录）；
  - L2 目录不存在返回错误文本且不崩溃；
  - L3 路径逃逸 workdir 被拒绝。

## glob（T1）
- 接口：`glob(pattern: str) -> str`
- 行为：按 pattern（如 `**/*.py`）在 workdir 内匹配，逐行返回匹配路径；无匹配 → `(no matches)`。
- 验收标准：
  - G1 匹配到文件并逐行返回；
  - G2 无匹配返回 `(no matches)`；
  - G3 pattern 含 `..` 逃逸被拒绝。

## grep（T1）
- 接口：`grep(pattern: str, path: str = ".") -> str`
- 行为：在 workdir 内（文件或目录递归）按正则搜索，返回 `path:line: 内容`；无匹配 → `(no matches)`；坏正则 → 错误文本；跳过缓存/隐藏目录。
- 验收标准：
  - GR1 返回 `path:line: content` 格式的匹配行；
  - GR2 无匹配返回 `(no matches)`；
  - GR3 坏正则返回错误文本且不崩溃；
  - GR4 只搜索 workdir 内。

## append_file（T1）
- 接口：`append_file(path: str, content: str) -> str`
- 行为：追加内容到文件（不存在则创建），返回确认。
- 验收标准：
  - AP1 追加后文件内容正确；
  - AP2 文件不存在时创建并写入。

## edit_file（T1）
- 接口：`edit_file(path: str, old: str, new: str, replace_all: bool = False) -> str`
- 行为：在 workdir 内文件中做精确文本替换（默认只替换第一处，`replace_all=True` 替换全部）；`old` 未找到 → 错误文本；其余内容保持不变。
- 验收标准：
  - ED1 默认只替换第一处，其余内容不变；
  - ED2 `old` 未找到返回错误文本；
  - ED3 `replace_all=True` 替换所有出现；
  - ED4 修改后文件整体内容正确；
  - ED5 路径逃逸 workdir 被拒绝。

> 契约测试：`tests/specs/test_tools.py`（read_file A1-A3 / write_file B1-B2 / bash C1-C4 + T1 L/G/GR/AP/ED）。
