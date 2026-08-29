"""Run a subset of BigCodeBench through our agent (single / judge-scored).

Usage:
    python tools/run_bigcodebench.py --limit 5            # pilot: verify + run 5
    python tools/run_bigcodebench.py --limit 30           # the benchmark subset
    python tools/run_bigcodebench.py --limit 30 --multi   # multi-agent pipeline

Per problem: repo/solution.py stub -> agent implements task_func -> hidden
unittest case passes -> PASS (LLM-judge scores quality too).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import Config  # noqa: E402
from eval.bigcodebench import load_bigcodebench  # noqa: E402
from eval.harness import run_task  # noqa: E402
from eval.report import render_markdown, summarize  # noqa: E402


def check_seeds(tasks) -> int:
    """Verify every stub's hidden tests FAIL before the agent runs (task validity)."""
    from eval.harness import _run_hidden_tests

    ok = 0
    for t in tasks:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            import shutil
            shutil.copytree(t.repo_seed, repo)
            if _run_hidden_tests(repo, t):
                print(f"  !! seed already passes: {t.id}")
            else:
                ok += 1
    print(f"seeds fail on {ok}/{len(tasks)} tasks (expect all)")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--model", default=None, help="defaults to cheap tier (flash) for cost")
    ap.add_argument("--multi", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-run already-completed problems")
    args = ap.parse_args()

    cfg = Config.from_env()
    from dataclasses import replace
    cfg = replace(cfg, max_steps=10, max_tool_calls=20, max_consecutive_failures=2,
                  no_progress_limit=2)
    tasks = load_bigcodebench(limit=args.start + args.limit, seed=42)[args.start:]
    model = args.model or cfg.model  # flash (cheap) unless overridden
    print(f"loaded {len(tasks)} BigCodeBench tasks; tier={model} (flash, bounded) multi={args.multi}")
    check_seeds(tasks)

    # resumable: persist each result to JSONL, skip already-done problems
    import json
    results_file = Path(Path(__file__).resolve().parents[1]) / "swe_work" / "bcb" / "results.jsonl"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if results_file.exists() and not args.force:
        for line in results_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[r["task_id"]] = r
    print(f"already done: {len(done)}")

    records = []
    for t in tasks:
        if t.id in done:
            r = done[t.id]
            records.append(r)
            print(f"\n=== {t.id} (cached) -> {'PASS' if r['passed'] else 'FAIL'} {r['tokens']} tok")
            continue
        print(f"\n=== {t.id} ===", flush=True)
        rec = run_task(t, cfg, model=model, multi=args.multi)
        r = {"task_id": t.id, "passed": rec.passed, "elapsed_s": rec.elapsed_s, "tokens": rec.tokens,
             "rubric": rec.rubric_scores}
        with results_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(r) + "\n")
        records.append(r)
        print(f"  {'PASS' if r['passed'] else 'FAIL'} elapsed={r['elapsed_s']:.1f}s tokens={r['tokens']}", flush=True)

    # render summary (records may be EvalRecord or dict — normalize)
    from eval.harness import EvalRecord

    def to_rec(r):
        if isinstance(r, EvalRecord):
            return r
        return EvalRecord(task_id=r["task_id"], passed=r["passed"], elapsed_s=r["elapsed_s"],
                          tokens=r["tokens"], rubric_scores=r.get("rubric", {}))
    summary = summarize([to_rec(r) for r in records])
    print("\n" + render_markdown(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
