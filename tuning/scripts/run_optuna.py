#!/usr/bin/env python3
"""Phase 2 Bayesian optimization (Optuna) over the high-influence
parameters surfaced by Phase 1.

Usage:
    python tuning/scripts/run_optuna.py \
        --space tuning/spaces/phase2/space.json \
        [--n-trials 50] \
        [--resume]

Each Optuna trial writes a temp config, calls `run_trial.py` with
`--repeat n_repeats_per_trial`, parses the returned jsonl row, applies
the weighted fitness function from the space file, and reports the
scalar to Optuna. The study persists to
`tuning/runs/phase2/<study_name>.db` (SQLite) so you can resume after
interruption and inspect post-hoc with `optuna-dashboard`.

Designed to read whatever Phase 1 wrote — `tuning/spaces/phase2/space.json`
captures the search space declaratively, including the fitness
weights. Phase 6 (ship) reads the top trial from the study.db.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_TRIAL = REPO_ROOT / "tuning" / "scripts" / "run_trial.py"
RUNS_DIR = REPO_ROOT / "tuning" / "runs" / "phase2"


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
    """Merge src into dst; nested dicts recurse, leaves are replaced."""
    for k, v in src.items():
        if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def walk(d: dict[str, Any], dotted: str) -> Any:
    """Pull a value out of nested dicts by dotted key."""
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def fitness_from_row(row: dict[str, Any], weights: dict[str, float]) -> float:
    """Apply the weighted composite to a run_trial.py jsonl row's median.

    Median (not mean) so a single outlier sub-run doesn't tank the
    fitness. Caller's `n_repeats_per_trial` controls how many sub-runs
    feed the median; n=3 is the floor per Phase 0g.
    """
    medians = row["median"]
    score = 0.0
    total_weight = 0.0
    for key, w in weights.items():
        v = medians.get(key)
        if v is None:
            # Sub-score missing from this run — skip + reweight.
            continue
        score += w * float(v)
        total_weight += w
    if total_weight == 0:
        raise RuntimeError("fitness weights produced no valid scores")
    # Renormalize so missing sub-scores don't bias toward zero.
    return score / total_weight


def make_objective(
    space: dict[str, Any],
    fitness_weights: dict[str, float],
    benchmark: str,
    phase_tag: str,
    n_repeats: int,
    score_keys: list[str],
):
    search_space = space["search_space"]

    def objective(trial: Any) -> float:
        # Build per-trial config_overrides from the search-space sample.
        overrides: dict[str, Any] = {}
        for path, spec in search_space.items():
            if path == "_comment":
                continue
            kind = spec["type"]
            if kind == "float":
                v = trial.suggest_float(path, spec["low"], spec["high"])
            elif kind == "int":
                v = trial.suggest_int(path, spec["low"], spec["high"])
            elif kind == "categorical":
                v = trial.suggest_categorical(path, spec["choices"])
            else:
                raise RuntimeError(f"unknown search-space type {kind!r}")
            deep_merge(overrides, expand_dotted(path, v))

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, prefix="optuna_"
        ) as tmp:
            cfg = {
                "_comment": f"Optuna trial {trial.number}",
                "surface": "sdk",
                "config_overrides": overrides,
            }
            json.dump(cfg, tmp)
            cfg_path = Path(tmp.name)

        try:
            cmd = [
                sys.executable,
                str(RUN_TRIAL),
                "--benchmark",
                benchmark,
                "--config",
                str(cfg_path),
                "--phase",
                phase_tag,
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
                # Optuna can prune failed trials; raise so it does.
                raise RuntimeError(
                    f"trial {trial.number} run_trial failed (exit {proc.returncode}):\n"
                    f"{proc.stderr[-2000:]}"
                )
            row = json.loads(proc.stdout.strip().splitlines()[-1])
            score = fitness_from_row(row, fitness_weights)
            # Stash the trial-id + sub-scores in Optuna user_attrs for
            # post-hoc analysis without re-parsing run_trial output.
            trial.set_user_attr("trial_id", row["trial_id"])
            trial.set_user_attr("sub_scores", row["median"])
            trial.set_user_attr("stddev", row["stddev"])
            return score
        finally:
            cfg_path.unlink(missing_ok=True)

    return objective


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 2 Optuna tuning")
    p.add_argument("--space", required=True, help="Phase 2 space JSON")
    p.add_argument(
        "--n-trials",
        type=int,
        default=None,
        help="Override the spec's n_trials (useful for short test runs)",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Continue an existing study (default: fail if study exists)",
    )
    args = p.parse_args()

    import optuna  # noqa: PLC0415  — keep import lazy so --help doesn't require optuna

    space = json.loads(Path(args.space).read_text())
    study_name = space["study_name"]
    n_trials = args.n_trials or space.get("n_trials", 50)
    n_repeats = space.get("n_repeats_per_trial", 3)
    benchmark = space.get("benchmark", "lti")
    phase_tag = space.get("phase_tag", "phase2_optuna")
    weights = space["fitness"]["weights"]
    score_keys = space.get("score_keys", list(weights.keys()))

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{RUNS_DIR / f'{study_name}.db'}"
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        direction="maximize",
        load_if_exists=args.resume,
    )

    print(
        f"study={study_name} storage={storage} n_trials={n_trials} "
        f"n_repeats={n_repeats} benchmark={benchmark}",
        file=sys.stderr,
    )
    obj = make_objective(space, weights, benchmark, phase_tag, n_repeats, score_keys)
    study.optimize(obj, n_trials=n_trials, show_progress_bar=False)

    print("\n=== best trial ===", file=sys.stderr)
    print(f"  fitness:   {study.best_value:.4f}", file=sys.stderr)
    print(f"  params:    {study.best_params}", file=sys.stderr)
    print(
        f"  sub-scores: {study.best_trial.user_attrs.get('sub_scores')}",
        file=sys.stderr,
    )
    print(f"  trial_id:  {study.best_trial.user_attrs.get('trial_id')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
