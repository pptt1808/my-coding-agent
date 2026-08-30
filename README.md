# coding-agent

A self-hosted **coding agent** (Claude Code / Codex style): it talks to an
LLM, autonomously reads/writes files and runs commands to complete a coding
task — plus an **AI-driven automated evaluation harness** that objectively
grades whether it actually succeeded (our differentiator).

> 依据《软件工程专业推免项目：构建编程智能体》题目开发。完整路线图与设计说明见 `开发文档.md`；组件规格见 `specs/`；契约测试见 `tests/specs/`。

## Layout
```
agent/        agent engine: loop, LLM client, parser, history, termination, errors
tools/        local tool definitions + execution (read/write/bash/...)
eval/         automated evaluation harness (tasks, judge, report)
specs/        spec-driven: component specs + acceptance criteria
tests/specs/  contract tests (written BEFORE implementation)
tasks/        the eval task set (repo seed + hidden tests)
examples/     demo scripts
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate   # win: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # then fill in your API key (never commit .env)
```

## Run
```bash
coding-agent config         # print resolved configuration
coding-agent run "fix the bug in src/util.py"          # one-shot (dev tier MODEL)
coding-agent run "..." --model deepseek-v4-pro         # override tier
coding-agent chat            # interactive REPL (streaming, chat-bubble, type "/" for menu; /undo /redo /codemap ...)
coding-agent pm              # PM demo mode (vibe-coding: /vision /story /mvp /validate /polish /pitch)
python examples/live_smoke.py [--model deepseek-v4-pro]  # live e2e smoke (needs .env key)
coding-agent run "..." --explore   # force a cheap read-only explore subagent first (gated)
python tools/run_bigcodebench.py --limit 30   # BigCodeBench subset (env-friendly benchmark)
```

## Tests
```bash
pytest                      # 184 contract tests (specs/tools/loop/eval/repl/compact/session/tasklist/permissions/review/multi-agent/pm-mode/repomap/agentmd/skills/cli/...)
```

## Evaluation task set (difficulty gradient)
```bash
python -m eval tasks                        # run all 6 tasks (eval tier)
python -m eval tasks --task parser_calc     # run one task
```
L1 fix_add_bug → L2 implement_fib → L3 refactor_rename → L4 lru_cache → L5 parser_calc → L6 first_occurrence.
Gradient runs found real issues (now fixed): Windows cmd heredoc/`find` incompatibility → bash schema + system prompt now tell the model the platform (parser_calc: 283.9s/163k tokens → 171.6s/131k tokens).

## Automated evaluation
```bash
python -m eval tasks                     # batch eval, eval tier (EVAL_MODEL)
python -m eval tasks --model deepseek-v4-flash   # compare tiers
```

## Status
Phase 1 (minimum closed loop) done + verified against a REAL model:
- `agent/loop.py` — the full agent pipeline (LLM → parse → execute → feed back → terminate)
- `agent/llm.py` — OpenAI-compatible gateway client with NATIVE tool calling
- Model layering: `MODEL` (dev, e.g. deepseek-v4-flash) vs `EVAL_MODEL` (eval, e.g. deepseek-v4-pro), `LLMClient(model=...)` / `run --model` to pick a tier
- `tools/` — `read_file` / `write_file` / `edit_file` / `append_file` / `bash` / `list_dir` / `glob` / `grep` (T1 set) with workdir confinement + dangerous-command blacklist, text-fallback parsing, multi-threshold termination, context truncation/summarization
- 79 contract tests green (`pytest`); offline demo: `python examples/demo_fake_agent.py`
- **Live smoke PASS** (real DeepSeek key, both flash & pro): fix-bug task → read → **edit_file** → verify via pytest → final answer
- **Eval harness (Phase 5)**: `tasks/` task set (repo seed + hidden tests) → isolated temp-dir runs → hidden-test PASS/FAIL grading → markdown report. Real run: **2/2 PASS on both tiers** (pro avg 11.6s/8.5k tokens, flash avg 5.7s/6.6k tokens)
- **LLM-judge (Phase 6)**: rubric scoring of quality dimensions tests can't catch (correctness/quality/minimal). Real run showed `minimal=2.0` — the judge penalized a whole-file rewrite vs a minimal edit
- **Interactive REPL + /compact (P0 of the iteration plan)**: `coding-agent chat` — slash commands `/help /exit /clear /compact /status /model`; LLM-summary conversation compaction; live-verified (status → create+run file → status → compact → exit)
- **P1 iteration**: `/save` `/resume` `/ls` session persistence (`.coding-agent/sessions/`), `/task` todo list injected into the system prompt, auto-compact (config `AUTO_COMPACT_AT_TOKENS`), `/cost` input/output token split — live-verified end to end
- **P2 iteration**: `/review` (diff since session start + tests + LLM judge), `/permissions [block|reset]`, `--tools` tool whitelist, tail-first output truncation — plus a **real fix**: no-progress now requires identical (tool+args) repetition, so exploring different files no longer kills the loop
- **Multi-turn real demo** (`python examples/demo_multi_turn.py`, needs key): a multi-file project (bug + missing function + missing CLI flag + test suite) completed over 3 interactive turns — fix/implement/feature all landed, 7/7 tests pass, `/review` judge scored 5/5/5/5
- **Multi-agent (gated)**: cheap read-only explore subagent (`should_explore`: off/auto/always, deterministic zero-cost gate) + planner + parallel fan-out; A/B on a 47-file task showed **multi-agent is NOT worth it** (+283% tokens), so it's off by default with high thresholds (data-driven decision)
- **Cost control (grounded)**: auto-compact window (Claude Code) is ON by default, `MAX_TOTAL_TOKENS` budget (AgentBudget), API retry, resumable runs — a runaway case went 126k→73k tokens
- **improve #1-#3 (grounded in mature projects)**: Aider-style **repo-map** (ast symbol map, cached, injected), **/undo /redo** checkpoints, **AGENT.md** + **PM_PROFILE** persistent project context (CLAUDE.md-style)
- **PM demo mode (our differentiator)**: clarify-gate (one question at a time) → DEMO_SPEC → user confirm → lean MVP → /validate feedback → story/pitch; four clean product artifacts; anti-pollution (embedded-doc extraction + retry + warn-on-meta)
- **Benchmarks**: 6-level gradient tasks (L1-L6) + `large_task` multi-module all PASS; **BigCodeBench 30-problem subset = 40%** (env-friendly, cost-controlled); SWE-bench adapter ready

## Submission deliverables (Phase 7)
- `README.txt` — 提交说明（仓库地址占位、如何运行、特色功能；≤1000 汉字，当前 259 汉字）
- `视频脚本.md` — 2 分钟演示视频时间轴（coding agent + PM 演示模式）
- `面试自辩材料.md` — 为什么这样运转：四个自研点+踩坑、评测体系、尖锐问题预答、数据证据
- `评审证据`：`BENCHMARK_RESULTS.md`（BigCodeBench 40%）、`合规复查.md`（逐条核对题目规则）、`改进方向对比.md`（vs 成熟开源）

> 提交前必做：① 把公开仓库地址填入 README.txt；② 录制视频时隐藏一切 API key；③ 截止后不再推送新提交。
