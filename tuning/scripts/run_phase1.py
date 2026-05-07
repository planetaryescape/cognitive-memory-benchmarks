#!/usr/bin/env python3
"""Phase 1 OFAT (one-factor-at-a-time) sensitivity sweeps.

Reads a sweep spec (e.g. `tuning/spaces/phase1/sweeps.json`) and runs
each parameter sweep through `run_trial.py`. Aggregates results into
`tuning/runs/phase1_sensitivity.csv` so Phase 2's Optuna search space
can prune low-influence params.

Usage:
    python tuning/scripts/run_phase1.py \
        --spec tuning/spaces/phase1/sweeps.json \
        [--params retrieval_score_exponent direct_boost] \
        [--dry-run]

The script writes a temp trial config per (sweep, value) pair, invokes
`run_trial.py` with `--repeat <n_repeats_per_value>`, parses the
returned jsonl line, and appends a row to the CSV with columns:

    param_path,value,is_default,n_repeats,
    median.<key1>,stddev.<key1>,...

Cost note: at n_repeats=3 across the default 10 sweeps × 5 values =
~150 sub-runs ≈ 12.5 hours wall ≈ $7-10 on LTI-Bench. Phase 0g found
LTI-Bench at n=42 has ~1.5pp f1 stddev, which means the 2pp drop-gate
in the parent plan is barely above noise. Consider using LongMemEval-S
(500 questions, ~0.3pp expected stddev) for a sharper Phase 1 if API
budget allows; restructure sweeps.json's `benchmark` field accordingly.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_TRIAL = REPO_ROOT / "tuning" / "scripts" / "run_trial.py"
RUNS_DIR = REPO_ROOT / "tuning" / "runs"
CSV_PATH = RUNS_DIR / "phase1_sensitivity.csv"


def expand_dotted(path: str, value: Any) -> dict[str, Any]:
    """`base_decay_rates.semantic` → `{'base_decay_rates': {'semantic': X}}`.

    The trial config schema treats this as a config_overrides field.
    Top-level dotted keys nest naturally. Caller wraps the result in
    `{"config_overrides": ...}`.
    """
    parts = path.split(".")
    out: dict[str, Any] = {}
    cur = out
    for p in parts[:-1]:
        cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value
    return out


def write_trial_config(tmp_dir: Path, param_path: str, value: Any) -> Path:
    overrides = expand_dotted(param_path, value)
    cfg = {
        "_comment": f"Phase 1 OFAT sweep: {param_path}={value}",
        "surface": "sdk",
        "config_overrides": overrides,
    }
    p = tmp_dir / f"{param_path.replace('.', '_')}__{value}.json"
    p.write_text(json.dumps(cfg, indent=2))
    return p


def run_trial(
    config_path: Path,
    benchmark: str,
    phase: str,
    n_repeats: int,
    score_keys: list[str],
) -> dict[str, Any]:
    """Invoke run_trial.py and return the parsed jsonl row."""
    cmd = [
        sys.executable,
        str(RUN_TRIAL),
        "--benchmark",
        benchmark,
        "--config",
        str(config_path),
        "--phase",
        phase,
        "--repeat",
        str(n_repeats),
        "--score-keys",
        *score_keys,
        "--",
        "--quiet",
        "--judge-model",
        "gpt-4o-2024-08-06",
    ]
    # run_trial.py prints the final jsonl row to stdout; parse it.
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"run_trial failed (exit {proc.returncode}):\n"
            f"--- stdout ---\n{proc.stdout}\n"
            f"--- stderr ---\n{proc.stderr}"
        )
    last_line = proc.stdout.strip().splitlines()[-1]
    return json.loads(last_line)


def append_csv_row(
    spec_param: str,
    value: Any,
    default_value: Any,
    n_repeats: int,
    row: dict[str, Any],
    score_keys: list[str],
) -> None:
    is_first = not CSV_PATH.exists()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "a", newline="") as f:
        w = csv.writer(f)
        if is_first:
            header = ["param_path", "value", "is_default", "n_repeats", "trial_id"]
            for k in score_keys:
                header.extend([f"median.{k}", f"stddev.{k}"])
            w.writerow(header)
        out = [
            spec_param,
            json.dumps(value),
            value == default_value,
            n_repeats,
            row["trial_id"],
        ]
        for k in score_keys:
            out.extend([row["median"].get(k), row["stddev"].get(k)])
        w.writerow(out)


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 1 OFAT sensitivity sweeps")
    p.add_argument("--spec", required=True, help="Sweep spec JSON")
    p.add_argument(
        "--params",
        nargs="*",
        default=None,
        help="Optional subset of param_paths to run (default: all in spec)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the trials that would be run; do not invoke run_trial",
    )
    args = p.parse_args()

    spec = json.loads(Path(args.spec).read_text())
    benchmark = spec.get("benchmark", "lti")
    phase_tag = spec.get("phase_tag", "phase1_sensitivity")
    n_repeats = spec.get("n_repeats_per_value", 3)
    score_keys = spec.get("score_keys", ["overall.mean_f1"])

    sweeps = spec["sweeps"]
    if args.params:
        sweeps = [s for s in sweeps if s["param_path"] in args.params]
        if not sweeps:
            print(f"no sweeps matched --params {args.params}", file=sys.stderr)
            return 1

    total_trials = sum(len(s["values"]) for s in sweeps)
    print(
        f"sweep plan: {len(sweeps)} param(s), {total_trials} trials, "
        f"{n_repeats} sub-runs each = {total_trials * n_repeats} total sub-runs",
        file=sys.stderr,
    )

    if args.dry_run:
        for s in sweeps:
            for v in s["values"]:
                print(f"  {s['param_path']} = {v}")
        return 0

    with tempfile.TemporaryDirectory(prefix="phase1_") as tmp:
        tmp_dir = Path(tmp)
        for s in sweeps:
            param_path = s["param_path"]
            default = s["default"]
            for v in s["values"]:
                cfg_path = write_trial_config(tmp_dir, param_path, v)
                print(
                    f"\n=== {param_path} = {v} ({'default' if v == default else 'sweep'}) ===",
                    file=sys.stderr,
                )
                row = run_trial(cfg_path, benchmark, phase_tag, n_repeats, score_keys)
                append_csv_row(param_path, v, default, n_repeats, row, score_keys)
                print(
                    f"  trial={row['trial_id']} median={row['median']} stddev={row['stddev']}",
                    file=sys.stderr,
                )

    print(f"\nDone. Sensitivity CSV: {CSV_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
