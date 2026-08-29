# pm-mode.md — 产品经理演示开发模式（个性化）

职责：为 vibe-coding 演示场景提供**产品思维**的开发模式（我们自己的原创整合，无开源可抄）。agent 扮演"产品型 demo 建造者"：先澄清产品问题（给谁看/证明什么/爽点），做**最小可运行** demo，打磨 demo 时刻，并交付**四件产品交付物**（spec/story/可运行 demo/pitch），而不是只给代码。
接口：`coding-agent pm`（PM persona 交互 + `/vision /story /mvp /polish /pitch`）；`agent/pm.py`：`PmSession.create(config, ...)`、`turn(line)`、`run_step(step, task)`；交付物写 `<workdir>/demo/{DEMO_SPEC, DEMO_SCRIPT, PITCH}.md` 与 demo 代码。

行为：
- **Clarify**：`/vision` 让 agent 先问用户 1-3 个最关键产品问题（受众/要证明什么/爽点），回答后写 `demo/DEMO_SPEC.md`（Vision/Audience/Key claim/Demo moment/Acceptance）；
- **Story**：`/story` 写 30 秒叙事（问题→方案→回报）→ `demo/DEMO_SCRIPT.md`；
- **MVP**：`/mvp` 在 workspace 支架**最小可运行** demo（外部依赖打桩/fake，不过度工程），并把它跑起来 → demo 代码 + 短 README；
- **Polish**：`/polish` 打磨 happy path 丝滑，不增功能；
- **Pitch**：`/pitch` 写 `demo/PITCH.md`（价值主张/爽点/局限/下一步）；
- **护栏**：time-box、禁止过度工程（不上架构/CI/为测而测）、外部依赖打桩、每步可运行可展示。

验收标准（`tests/specs/test_pm_mode.py`）：
- P1 PM_PERSONA 含产品思维关键词（audience/MVP/demo/avoid over-engineering）；
- P2 `/vision` 写出 `demo/DEMO_SPEC.md`（含 Vision/Audience/Demo moment/Demo moment?），step 说明含"Ask the user..."；
- P3 `/story` 写出 `demo/DEMO_SCRIPT.md`；
- P4 `/pitch` 写出 `demo/PITCH.md`；
- P5 `/mvp` 在 workdir/demo 下产出可运行物（含 README 或代码）；不过度工程提示在 persona 里；
- P6 未知 step 返回提示、不崩溃；`PmSession.turn` 走 PM persona。
