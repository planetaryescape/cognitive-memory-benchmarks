#!/usr/bin/env python3
"""Phase 5: full LoCoMo head-to-head between v0.4 and v0.5 SDK defaults.

10 conversations × 2 candidates = 20 runs. Per-candidate, runs 10
shards in parallel (one process per conv via --start-from i
--max-conversations i+1). Two candidates run sequentially to keep
OpenAI API rate-limit pressure manageable.

Usage:
    python tuning/scripts/run_phase5.py \
        [--data locomo/data/locomo10.json] \
        [--out tuning/runs/phase5/]

Cost: ~$50 per candidate × 2 = ~$100. Wall: ~3.5h per candidate
sequential = ~7h total. Laptop must stay awake.

Gated on Phase 4 results — only runs if Phase 4 conv0 showed
v0.5 ≥ v0.4 + 1pp F1.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO_ROOT / "locomo" / "data" / "locomo10.json"
DEFAULT_OUT = REPO_ROOT / "tuning" / "runs" / "phase5"
SPACE_DIR = REPO_ROOT / "tuning" / "spaces" / "phase4"  # reuse phase 4 configs

CANDIDATES = [
    ("v04_baseline", SPACE_DIR / "v04_baseline.json"),
    ("v05_tuned", SPACE_DIR / "v05_tuned.json"),
]

PRODUCTION_FLAGS = [
    "--prompt-mode", "mem0",
    "--dual-perspective",
    "--deep-recall",
    "--rerank", "--rerank-factor", "3",
    "--top-k", "60",
    "--use-judge",
    "--model", "gpt-4o-mini",
]


def run_shard(conv_index: int, config_path: Path, out_path: Path, data_path: Path) -> subprocess.Popen:
    """Spawn locomo_eval for a single conversation as a background process.

    Uses --start-from i --max-conversations i+1 to run only conv i.
    Returns the Popen handle so the caller can wait + check exit codes.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = out_path.with_suffix(".log")
    cmd = [
        sys.executable,
        "-m",
        "locomo.locomo_eval",
        "--data", str(data_path),
        "--config", str(config_path),
        "--start-from", str(conv_index),
        "--max-conversations", str(conv_index + 1),
        "--output", str(out_path),
        "--quiet",
        *PRODUCTION_FLAGS,
    ]
    log_fh = open(log_path, "w")
    return subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env={"PYTHONPATH": str(REPO_ROOT), **__import__("os").environ},
    )


def aggregate_per_conv(candidate_dir: Path) -> dict[str, Any]:
    """Sum + weight-average per-conv results into a single bench-level
    aggregate. Mirrors the merge step from CR-A."""
    per_conv = []
    total_q, total_correct, total_f1_weighted = 0, 0, 0.0

    for i in range(10):
        conv_path = candidate_dir / f"conv{i}.json"
        if not conv_path.exists():
            print(f"  WARN: missing {conv_path}", file=sys.stderr)
            continue
        d = json.loads(conv_path.read_text())
        agg = d.get("aggregate", {}).get("overall", {})
        n = agg.get("num_questions", 0)
        f1 = agg.get("mean_f1", 0.0)
        llm = agg.get("llm_accuracy")
        per_conv.append({"conv": i, "n_questions": n, "mean_f1": f1, "llm_accuracy": llm})
        total_q += n
        total_f1_weighted += f1 * n
        if llm is not None:
            total_correct += int(round(llm * n))

    overall_f1 = total_f1_weighted / total_q if total_q else 0.0
    overall_llm = total_correct / total_q if total_q else 0.0
    return {
        "per_conv": per_conv,
        "overall": {
            "num_questions": total_q,
            "mean_f1": overall_f1,
            "llm_accuracy": overall_llm,
        },
    }


def run_candidate(name: str, config_path: Path, out_dir: Path, data_path: Path) -> dict[str, Any]:
    """Run one candidate across all 10 conversations in parallel.
    Waits for all shards to finish before returning."""
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {name}: spawning 10 parallel conv shards ===", file=sys.stderr)
    procs = []
    t0 = time.time()
    for i in range(10):
        out_path = out_dir / f"conv{i}.json"
        p = run_shard(i, config_path, out_path, data_path)
        procs.append((i, p))
        print(f"  spawned conv{i} (pid {p.pid})", file=sys.stderr)

    print(f"\n  waiting for all 10 shards to finish…", file=sys.stderr)
    failures = []
    for i, p in procs:
        rc = p.wait()
        if rc != 0:
            failures.append((i, rc))
            print(f"  conv{i} FAILED (exit {rc})", file=sys.stderr)
        else:
            print(f"  conv{i} done", file=sys.stderr)

    elapsed = time.time() - t0
    print(f"\n  {name} wall: {elapsed:.0f}s", file=sys.stderr)

    if failures:
        raise RuntimeError(f"{name}: {len(failures)} shards failed: {failures}")

    aggregate = aggregate_per_conv(out_dir)
    aggregate_path = out_dir / "aggregate.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2))
    print(f"  wrote {aggregate_path}", file=sys.stderr)
    print(
        f"  overall F1: {aggregate['overall']['mean_f1']:.4f}  "
        f"LLM acc: {aggregate['overall']['llm_accuracy']:.4f}  "
        f"(n_questions={aggregate['overall']['num_questions']})",
        file=sys.stderr,
    )
    return aggregate


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--candidate",
        choices=[c[0] for c in CANDIDATES] + ["all"],
        default="all",
        help="Run a single candidate or both (default: all)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data_path = Path(args.data)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    candidates = [c for c in CANDIDATES if args.candidate in (c[0], "all")]
    print(
        f"Phase 5: {len(candidates)} candidate(s) × 10 convs each. "
        f"Production flags: {' '.join(PRODUCTION_FLAGS)}",
        file=sys.stderr,
    )

    if args.dry_run:
        for name, cfg in candidates:
            print(f"  would run {name} (config {cfg})", file=sys.stderr)
        return 0

    results: dict[str, Any] = {}
    for name, cfg in candidates:
        candidate_dir = out_root / name
        results[name] = run_candidate(name, cfg, candidate_dir, data_path)

    # Cross-candidate summary
    if len(results) == 2:
        v04 = results.get("v04_baseline", {}).get("overall", {})
        v05 = results.get("v05_tuned", {}).get("overall", {})
        if v04 and v05:
            f1_delta = v05["mean_f1"] - v04["mean_f1"]
            llm_delta = v05["llm_accuracy"] - v04["llm_accuracy"]
            summary = {
                "v04_f1": v04["mean_f1"],
                "v05_f1": v05["mean_f1"],
                "f1_delta_pp": f1_delta * 100,
                "v04_llm_acc": v04["llm_accuracy"],
                "v05_llm_acc": v05["llm_accuracy"],
                "llm_acc_delta_pp": llm_delta * 100,
                "n_questions": v04["num_questions"],
                "verdict": (
                    "v0.5 ships valid" if f1_delta >= 0.005
                    else "no signal" if abs(f1_delta) < 0.005
                    else "v0.5 REGRESSES — investigate"
                ),
            }
            (out_root / "summary.json").write_text(json.dumps(summary, indent=2))
            print(f"\n=== Phase 5 summary ===", file=sys.stderr)
            print(json.dumps(summary, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
