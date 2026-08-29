# pm-mode.md — 产品经理演示开发模式（个性化）

职责：为 vibe-coding 演示场景提供**产品思维**的开发模式（我们自己的原创整合，无开源可抄）。agent 扮演"产品型 demo 建造者"：先澄清产品问题（给谁看/证明什么/爽点），做**最小可运行** demo，打磨 demo 时刻，并交付**四件产品交付物**（spec/story/可运行 demo/pitch），而不是只给代码。
接口：`coding-agent pm`（PM persona 交互 + `/vision /story /mvp /polish /pitch`）；`agent/pm.py`：`PmSession.create(config, ...)`、`turn(line)`、`run_step(step, task)`；交付物写 `<workdir>/demo/{DEMO_SPEC, DEMO_SCRIPT, PITCH}.md` 与 demo 代码。

行为：
- **分阶段 + 关卡（gate）**：`/mvp`/`/story`/`/pitch` 在无 spec 时**拒绝**（必须先 `/vision` 对齐）；persona 强制"先澄清（一次一问）→ 写 spec → 用户确认 → 才建"，不跳步；
- **Clarify**：`/vision` 让 agent 先问用户 1-3 个最关键产品问题（受众/要证明什么/爽点），回答后写 `demo/DEMO_SPEC.md`（Vision/Audience/Key claim/Demo moment/Acceptance）；
- **Story**：`/story` 写 30 秒叙事 → `demo/DEMO_SCRIPT.md`；
- **MVP**：`/mvp` 在 workspace 支架**最小可运行** demo（外部依赖打桩/fake，不过度工程），并把它跑起来；
- **Validate**：`/validate` 运行 demo 给用户看、问一条改进意见（真反馈循环）；
- **Pitch**：`/pitch` 写 `demo/PITCH.md`（价值主张/爽点/局限/下一步）；
- **产物抗污染**：`vision/story/pitch` 步骤提示词要求"只输出产物 markdown 正文、零前言"；若回复被判为**元信息**（`_looks_like_meta`：含 "all set / nothing new" 等，或极短且非 markdown），**强制重写**一次，避免把对话式话术写进产物；
- **护栏**：time-box、禁止过度工程（不上架构/CI/为测而测）、外部依赖打桩、每步可运行可展示。

验收标准（`tests/specs/test_pm_mode.py`）：
- P1 PM_PERSONA 含产品思维关键词（audience/MVP/demo/avoid over-engineering）；
- P2 `/vision` 写出 `demo/DEMO_SPEC.md`；
- P3/P4 `/story`、`/pitch` 写出对应产物（在 spec 存在后）；
- P5 `/mvp` 无 spec 时**拒绝构建**（gate）；spec 存在后构建；
- P6 未知 step 容错、`turn` 走 PM persona；
- P7 元信息回复 → 强制重写 → 产物为干净正文；
- P8 干净回复 → 不额外重写。
