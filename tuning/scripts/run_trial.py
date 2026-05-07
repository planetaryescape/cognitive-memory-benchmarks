#!/usr/bin/env python3
"""Run one tuning trial: invoke a benchmark with a JSON config, capture
output, append a structured one-liner to `tuning/runs/runs.jsonl`.

Usage:
    python tuning/scripts/run_trial.py \
        --benchmark lti \
        --config tuning/spaces/smoke_alpha_0_5.json \
        --phase phase0_smoke \
        [--surface sdk|daemon] \
        [--repeat 3]

`--repeat N` runs the trial N times for the median-of-N determinism
gate (Phase 0g). Each sub-run is logged separately under
`tuning/runs/<trial_id>/run-<i>/` and the runs.jsonl line carries
sub_runs[], median, stddev.

Designed for Phase 0+ tuning loops. The script is the only place
that knows about the runs.jsonl line schema — Optuna studies
written in Phase 2+ will call this same entrypoint.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "tuning" / "runs"
RUNS_JSONL = RUNS_DIR / "runs.jsonl"


# Map benchmark name → invocation. Each entry is (module, output-arg-name).
# Module is run via `python -m`; the harness writes its result JSON to
# the path passed via the output arg.
BENCHMARKS: dict[str, tuple[str, str]] = {
    "lti": ("lti.lti_bench", "--output"),
    "ablation": ("analysis.ablation_runner", "--output"),
}


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def next_trial_id(benchmark: str) -> str:
    """Find the next free `<benchmark>-NNNN` slot under tuning/runs/."""
    existing = [
        p.name
        for p in RUNS_DIR.iterdir()
        if p.is_dir() and p.name.startswith(f"{benchmark}-")
    ]
    nums = []
    for name in existing:
        suffix = name.removeprefix(f"{benchmark}-")
        if suffix.isdigit():
            nums.append(int(suffix))
    n = max(nums, default=0) + 1
    return f"{benchmark}-{n:04d}"


def run_one(
    benchmark: str,
    config_path: str | None,
    surface: str | None,
    out_dir: Path,
    extra_args: list[str],
) -> dict[str, Any]:
    """Run a single sub-run. Returns the parsed harness output JSON."""
    module, output_flag = BENCHMARKS[benchmark]
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "result.json"
    cmd = [sys.executable, "-m", module, output_flag, str(result_path)]
    if config_path:
        cmd.extend(["--config", str(config_path)])
    if surface:
        cmd.extend(["--surface", surface])
    cmd.extend(extra_args)

    stdout_log = out_dir / "stdout.log"
    stderr_log = out_dir / "stderr.log"
    t0 = time.time()
    with open(stdout_log, "w") as so, open(stderr_log, "w") as se:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            stdout=so,
            stderr=se,
            check=False,
            env={**os.environ},
        )
    elapsed = time.time() - t0

    if proc.returncode != 0:
        raise RuntimeError(
            f"{benchmark} exited {proc.returncode}; see {stderr_log}"
        )
    if not result_path.exists():
        raise RuntimeError(
            f"{benchmark} succeeded but did not write {result_path}"
        )
    with open(result_path) as f:
        result = json.load(f)
    result["_wall_seconds"] = elapsed
    return result


def aggregate(sub_runs: list[dict[str, Any]], score_keys: list[str]) -> dict[str, dict[str, float]]:
    """Compute median + stddev for each score key across sub-runs.

    Returns: {"median": {key: val}, "stddev": {key: val}}.
    Stddev is the sample standard deviation (n-1). With n=1, stddev is 0.
    """
    median: dict[str, float] = {}
    stddev: dict[str, float] = {}
    for key in score_keys:
        vals = []
        for r in sub_runs:
            v = _walk(r, key)
            if v is not None:
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    pass
        if not vals:
            continue
        median[key] = statistics.median(vals)
        stddev[key] = statistics.stdev(vals) if len(vals) >= 2 else 0.0
    return {"median": median, "stddev": stddev}


def _walk(d: dict[str, Any], dotted: str) -> Any:
    """Pull a value out of nested dicts using dotted keys."""
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def append_log(line: dict[str, Any]) -> None:
    RUNS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(RUNS_JSONL, "a") as f:
        f.write(json.dumps(line, default=str) + "\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Run one tuning trial")
    p.add_argument("--benchmark", required=True, choices=sorted(BENCHMARKS))
    p.add_argument("--config", default=None, help="Trial JSON config")
    p.add_argument(
        "--surface",
        choices=["sdk", "daemon"],
        default=None,
        help="Override the trial config's surface",
    )
    p.add_argument("--phase", required=True, help="Phase tag (phase0_smoke, phase1_sensitivity, ...)")
    p.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Sub-runs per trial (median-of-N for determinism gate)",
    )
    p.add_argument(
        "--score-keys",
        nargs="+",
        default=["overall_f1", "composite"],
        help="Dotted keys to aggregate across sub-runs",
    )
    p.add_argument(
        "--",
        dest="separator",
        nargs="?",
        help="Use -- to pass remaining args to the harness",
    )
    args, extra_args = p.parse_known_args()
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]

    trial_id = next_trial_id(args.benchmark)
    trial_dir = RUNS_DIR / trial_id
    trial_dir.mkdir(parents=True, exist_ok=True)

    config_blob = (
        json.loads(Path(args.config).read_text())
        if args.config and Path(args.config).exists()
        else {}
    )

    sub_runs: list[dict[str, Any]] = []
    for i in range(args.repeat):
        sub_dir = trial_dir / f"run-{i:02d}"
        result = run_one(
            args.benchmark,
            args.config,
            args.surface,
            sub_dir,
            extra_args,
        )
        sub_runs.append(result)

    agg = aggregate(sub_runs, args.score_keys)

    line = {
        "trial_id": trial_id,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "benchmark": args.benchmark,
        "surface": args.surface or config_blob.get("surface") or "sdk",
        "config": config_blob,
        "sub_runs_count": len(sub_runs),
        "median": agg["median"],
        "stddev": agg["stddev"],
        "git_sha": git_sha(),
        "wall_seconds": sum(r.get("_wall_seconds", 0.0) for r in sub_runs),
    }
    append_log(line)
    print(json.dumps(line, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
