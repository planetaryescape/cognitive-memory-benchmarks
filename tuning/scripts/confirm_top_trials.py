#!/usr/bin/env python3
"""Phase 2.5 step 3: re-run the top-K Optuna trials at higher n.

The Phase 2 sweep produced a bimodal fitness landscape where most
of the variance is judge noise on 3 marginal questions (see
`tuning/runs/phase2.5/question_variance.csv`). Trials within
~3pp fitness of each other can be reordered just by which side of
the marginal-judge coin they landed on.

This script picks the top-K trials from the Optuna study and
re-runs each one at higher n (default 5 sub-runs each instead of
the original 3), then reports whether the rank order holds.

Decision rule for Phase 6 (ship):
- If the original top-1 stays top-1 across 5 sub-runs, it's a
  defensible default.
- If rank order shuffles arbitrarily within the top-K, ship the
  config closest to current defaults — there's no real winner.

Usage:
    python tuning/scripts/confirm_top_trials.py \
        [--study-db tuning/runs/phase2/lti-phase2.db] \
        [--top-k 5] \
        [--repeats 5] \
        [--out tuning/runs/phase2.5/top_k_confirmation.csv]

Cost note: top-k=5 × repeats=5 = 25 sub-runs × ~5min × ~$0.10 ≈
~$2.50, ~2.1h wall. Cheaper than re-running the full Phase 2 (~$15)
and answers the question Phase 2 by itself can't.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_TRIAL = REPO_ROOT / "tuning" / "scripts" / "run_trial.py"
DEFAULT_STUDY = REPO_ROOT / "tuning" / "runs" / "phase2" / "lti-phase2.db"
DEFAULT_OUT = REPO_ROOT / "tuning" / "runs" / "phase2.5" / "top_k_confirmation.csv"


def expand_dotted(path: str, value: Any) -> dict[str, Any]:
    """`base_decay_rates.semantic` → `{'base_decay_rates': {'semantic': X}}`."""
    parts = path.split(".")
    out: dict[str, Any] = {}
    cur = out
    for p in parts[:-1]:
        cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value
    return out


def deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for k, v in src.items():
        if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def trial_to_overrides(trial: Any) -> dict[str, Any]:
    """Reconstruct the config_overrides dict from an Optuna trial's
    suggested params. Mirrors what run_optuna.py does at trial-build
    time so the re-run uses the exact same shape."""
    overrides: dict[str, Any] = {}
    for path, value in trial.params.items():
        deep_merge(overrides, expand_dotted(path, value))
    return overrides


def run_trial(
    config_path: Path,
    benchmark: str,
    phase: str,
    n_repeats: int,
    score_keys: list[str],
) -> dict[str, Any]:
    """Invoke run_trial.py and return the parsed jsonl row.
    Reused from run_optuna.py-style invocation for consistency."""
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
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"run_trial failed (exit {proc.returncode}):\n{proc.stderr[-2000:]}"
        )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def fitness_from_row(row: dict[str, Any], weights: dict[str, float]) -> float:
    """Match run_optuna.py's fitness — weighted composite, renormalised
    if any sub-score is missing."""
    medians = row["median"]
    score = 0.0
    total_weight = 0.0
    for key, w in weights.items():
        v = medians.get(key)
        if v is None:
            continue
        score += w * float(v)
        total_weight += w
    if total_weight == 0:
        raise RuntimeError("fitness weights produced no valid scores")
    return score / total_weight


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--study-db", default=str(DEFAULT_STUDY))
    ap.add_argument("--study-name", default="lti-phase2")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--phase-tag", default="phase2_5_top_k_confirm")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--space",
        default=str(REPO_ROOT / "tuning" / "spaces" / "phase2" / "space.json"),
        help="Phase 2 space JSON (used for fitness weights + score_keys)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the top-K trials we'd re-run; do not invoke run_trial",
    )
    args = ap.parse_args()

    import optuna  # noqa: PLC0415  — keep import lazy

    space = json.loads(Path(args.space).read_text())
    weights = space["fitness"]["weights"]
    score_keys = space.get("score_keys", list(weights.keys()))
    benchmark = space.get("benchmark", "lti")

    study = optuna.load_study(
        study_name=args.study_name, storage=f"sqlite:///{args.study_db}"
    )
    completed = [
        t for t in study.trials if t.state.name == "COMPLETE" and t.value is not None
    ]
    if not completed:
        print("no completed trials in study", file=sys.stderr)
        return 1

    completed.sort(key=lambda t: t.value, reverse=True)
    top = completed[: args.top_k]

    print(
        f"loaded {len(completed)} completed trials; selecting top {len(top)}",
        file=sys.stderr,
    )
    for i, t in enumerate(top, 1):
        print(
            f"  #{i}: phase2_trial={t.number} fitness={t.value:.4f} "
            f"params={t.params}",
            file=sys.stderr,
        )

    if args.dry_run:
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    csv_rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="confirm_") as tmp:
        tmp_dir = Path(tmp)
        for rank, t in enumerate(top, 1):
            overrides = trial_to_overrides(t)
            cfg = {
                "_comment": f"Phase 2.5 top-K confirmation: phase2 trial #{t.number}",
                "surface": "sdk",
                "config_overrides": overrides,
            }
            cfg_path = tmp_dir / f"top{rank:02d}.json"
            cfg_path.write_text(json.dumps(cfg, indent=2))

            print(
                f"\n=== confirming rank {rank} (phase2 trial #{t.number}, "
                f"original fitness {t.value:.4f}) ===",
                file=sys.stderr,
            )
            row = run_trial(
                cfg_path, benchmark, args.phase_tag, args.repeats, score_keys
            )
            confirmed_fitness = fitness_from_row(row, weights)
            print(
                f"  confirmed: trial_id={row['trial_id']} fitness={confirmed_fitness:.4f} "
                f"delta={confirmed_fitness - t.value:+.4f}",
                file=sys.stderr,
            )

            csv_rows.append(
                {
                    "rank_phase2": rank,
                    "phase2_trial_number": t.number,
                    "phase2_fitness": t.value,
                    "confirm_trial_id": row["trial_id"],
                    "confirmed_fitness": confirmed_fitness,
                    "delta": confirmed_fitness - t.value,
                    **{f"params.{k}": v for k, v in t.params.items()},
                    **{f"confirm_median.{k}": v for k, v in row["median"].items()},
                    **{f"confirm_stddev.{k}": v for k, v in row["stddev"].items()},
                }
            )

    fieldnames = sorted({k for r in csv_rows for k in r.keys()})
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in csv_rows:
            w.writerow(r)

    print(f"\nwrote {out}", file=sys.stderr)

    # Stdout summary: did rank order hold?
    print("\n=== rank stability check ===", file=sys.stderr)
    confirmed_sorted = sorted(csv_rows, key=lambda r: r["confirmed_fitness"], reverse=True)
    for new_rank, r in enumerate(confirmed_sorted, 1):
        old_rank = r["rank_phase2"]
        marker = "" if new_rank == old_rank else f"  (was #{old_rank})"
        print(
            f"  new #{new_rank}: phase2 trial {r['phase2_trial_number']} "
            f"confirmed_fitness={r['confirmed_fitness']:.4f}"
            + marker,
            file=sys.stderr,
        )

    rank_changes = sum(
        1
        for new_rank, r in enumerate(confirmed_sorted, 1)
        if new_rank != r["rank_phase2"]
    )
    print(
        f"\nrank changes: {rank_changes}/{len(csv_rows)}", file=sys.stderr
    )
    if rank_changes >= len(csv_rows) // 2:
        print(
            "→ verdict: top-K is noise-equivalent. Phase 6 should ship "
            "the config closest to existing defaults among the top-K.",
            file=sys.stderr,
        )
    else:
        print(
            "→ verdict: rank is stable enough to trust the top trial as "
            "a Phase 6 default candidate.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
