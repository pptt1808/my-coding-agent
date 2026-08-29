"""Run real SWE-bench Verified instances through our agent (pilot + subset).

Usage:
    python tools/run_swebench.py --ids psf__requests-1142            # pilot one
    python tools/run_swebench.py --ids psf__requests-1142 psf__requests-2931

For each instance:
  1. clone the repo (cached under swe_work/, gitignored), checkout base_commit
  2. pip install -e the repo (so `import requests` works and its tests run)
  3. apply the SWE-bench test_patch (the FAIL_TO_PASS tests now exist & fail on base)
  4. run our agent (single or gated multi) with the issue text as the task
  5. grade: run the FAIL_TO_PASS tests; all pass -> PASS
Notes: heavy (clone + install + real test suite on Python 3.14); use a small subset.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import Config  # noqa: E402
from datasets import load_dataset  # noqa: E402

WORK = ROOT / "swe_work"  # gitignored cache for cloned repos


def _run(cmd, cwd=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")


def setup_repo(inst, workdir: Path) -> Path:
    """Clone repo @ base_commit, pip install -e, apply test_patch (isolated workdir)."""
    repo = inst["repo"]           # e.g. psf/requests
    base = inst["base_commit"]
    package = repo.split("/")[-1]
    clone_dir = WORK / package
    if not (clone_dir / ".git").exists():
        clone_dir.parent.mkdir(parents=True, exist_ok=True)
        # bypass any (possibly stale) git proxy config; direct https works on this host
        _run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "clone", "--quiet",
              f"https://github.com/{repo}.git", str(clone_dir)], timeout=1200)
    # checkout base_commit in the real clone (it has .git), THEN copy to workdir
    _run(["git", "checkout", "--quiet", base], cwd=clone_dir)
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(clone_dir, workdir, ignore=shutil.ignore_patterns(".git"))
    _run(["git", "checkout", "--quiet", base], cwd=workdir)
    _run([sys.executable, "-m", "pip", "install", "--quiet", "-e", str(workdir)], timeout=900)
    # apply the SWE test_patch via a temp patch file (avoids stdin-pipe issues)
    from eval.swebench import apply_patch
    apply_patch(inst.get("test_patch", ""), workdir)
    return workdir


def grade(inst, repo: Path) -> tuple[bool, str]:
    """Run FAIL_TO_PASS tests; all pass -> PASS."""
    fail_to_pass = inst.get("FAIL_TO_PASS", [])
    if not fail_to_pass:
        return False, "no FAIL_TO_PASS tests"
    proc = _run([sys.executable, "-m", "pytest", "-q", *fail_to_pass], cwd=repo, timeout=1800)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out[-600:]


def run_agent(cfg: Config, inst, repo: Path, *, multi: bool) -> tuple[str, int]:
    """Run our agent (or the gated multi pipeline) on the SWE-bench issue."""
    cfg2 = replace(cfg, workdir=repo)
    if multi:
        from agent.multi import orchestrate
        metrics: dict[str, dict] = {}
        answer, _ = orchestrate(cfg2, inst["problem_statement"], metrics=metrics)
        return answer, int(metrics.get("total_tokens", 0))
    from agent.loop import CodingAgent
    agent = CodingAgent(cfg2, model=cfg.eval_model_name)
    answer = agent.run(inst["problem_statement"])
    return answer, agent.total_tokens


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", default=["psf__requests-1142"], help="instance ids")
    ap.add_argument("--multi", action="store_true", help="use multi-agent pipeline")
    args = ap.parse_args()

    cfg = Config.from_env()
    ds = load_dataset("princeton-nlp/SWE-bench_Verified")["test"]
    by_id = {d["instance_id"]: d for d in ds}
    results = []
    for iid in args.ids:
        inst = by_id.get(iid)
        if not inst:
            print(f"unknown instance: {iid}")
            continue
        print(f"\n=== {iid} ({inst['repo']} @ {inst['base_commit'][:8]}) ===")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp) / "repo"
                setup_repo(inst, repo)
                start = time.monotonic()
                answer, tokens = run_agent(cfg, inst, repo, multi=args.multi)
                elapsed = time.monotonic() - start
                passed, detail = grade(inst, repo)
            print(f"  -> {'PASS' if passed else 'FAIL'}  elapsed={elapsed:.1f}s tokens={tokens}")
            results.append({"id": iid, "passed": passed, "elapsed_s": elapsed, "tokens": tokens})
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  -> ERROR {e}")
            results.append({"id": iid, "passed": False, "elapsed_s": 0.0, "tokens": 0})

    print("\n=== summary ===")
    for r in results:
        print(f"  {r['id']}: {'PASS' if r['passed'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
