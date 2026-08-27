# spec-driven 目录规范

> Spec-driven 只约束我们开发 agent 工程本身（决策 B13），不约束 agent 运行时。

`specs/*.md` 定义每个组件/功能的规格与可自动验证的验收标准（即"spec 即 oracle"）。
`tests/specs/*.py` 是与之**一一对应**、且在实现**之前**写好的契约测试（先红后绿）。

开发循环：**Spec → 契约测试（先写）→ 实现 → 验证 → 回归**。

约定：
- 一份 spec 对应一个 `tests/specs/test_*.py`。
- 验收标准尽量写成可自动判定（pytest / 隐藏测试），减少凭感觉验收。
- 与上层自动评测系统分工见 `开发文档.md` §6.4：`tests/specs/` 验证组件实现正确性，`eval/` 验证 agent 能否解决真实任务。
