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
coding-agent run "fix the bug in src/util.py"   # full agent loop
```

## Tests
```bash
pytest                      # 46 contract tests (specs/tools/loop/parser/...)
```

## Status
Phase 1 (minimum closed loop) done:
- `agent/loop.py` — the full agent pipeline (LLM → parse → execute → feed back → terminate)
- `agent/llm.py` — OpenAI-compatible gateway client with NATIVE tool calling
- `tools/` — `read_file` / `write_file` / `bash` with workdir confinement + dangerous-command blacklist, text-fallback parsing, multi-threshold termination, context truncation/summarization
- 46 contract tests green (`pytest`); offline end-to-end demo: `python examples/demo_fake_agent.py`

Next: T1 robustness (edit_file/grep/glob tool set, richer error handling), then the eval harness (Phase 5).
