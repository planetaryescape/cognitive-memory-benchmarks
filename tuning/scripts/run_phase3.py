#!/usr/bin/env python3
"""Phase 3: decay-shape cross-check on Phase 2 winners.

Per the parent plan §3, Phase 3 runs each of the top-K Phase 2 configs
through a different distribution (LoCoMo conv0) and drops any candidate
whose cross-check score is more than 5pp below its LTI-Bench fitness —
that's overfitting to LTI-Bench's specific question set.

LoCoMo conv0 is a more substantive bench than LTI-Bench (full 1540-QA
benchmark — we just run conv0 = ~105 questions, much larger sample
than LTI's 42). If a Phase 2 winner holds up here, the win is
distribution-robust. If it collapses, it was LTI-specific noise.

Usage:
    python tuning/scripts/run_phase3.py \
        --data locomo/data/locomo10.json \
        [--top-k 5] \
        [--study-db tuning/runs/phase2/lti-phase2.db] \
        [--out tuning/runs/phase3/cross_check.csv]

Cost: K=5 × ~30 min/conv × ~$0.50 ≈ ~$2.50, ~2.5h.
Cheaper than Phase 5 (full LoCoMo, ~$10) and answers the
overfitting question with one conversation.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STUDY = REPO_ROOT / "tuning" / "runs" / "phase2" / "lti-phase2.db"
DEFAULT_DATA = REPO_ROOT / "locomo" / "data" / "locomo10.json"
DEFAULT_OUT = REPO_ROOT / "tuning" / "runs" / "phase3" / "cross_check.csv"


def expand_dotted(path: str, value: Any) -> dict[str, Any]:
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
    overrides: dict[str, Any] = {}
    for path, value in trial.params.items():
        deep_merge(overrides, expand_dotted(path, value))
    return overrides


def run_locomo_for_config(
    cfg_path: Path,
    data_path: Path,
    out_path: Path,
    model: str,
) -> dict[str, Any]:
    """Invoke locomo_eval.py --config with --max-conversations 1 (conv0
    only). Returns the parsed result.json."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "locomo.locomo_eval",
        "--data",
        str(data_path),
        "--config",
        str(cfg_path),
        "--output",
        str(out_path),
        "--max-conversations",
        "1",
        "--quiet",
        "--model",
        model,
        "--prompt-mode",
        "official",
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={"PYTHONPATH": str(REPO_ROOT), **__import__("os").environ},
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"locomo_eval failed (exit {proc.returncode}):\n"
            f"--- stdout ---\n{proc.stdout[-1500:]}\n"
            f"--- stderr ---\n{proc.stderr[-1500:]}"
        )
    if not out_path.exists():
        raise RuntimeError(
            f"locomo_eval finished but did not write {out_path}"
        )
    return json.loads(out_path.read_text())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--study-db", default=str(DEFAULT_STUDY))
    ap.add_argument("--study-name", default="lti-phase2")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the top-K trials we'd cross-check; do not invoke locomo_eval",
    )
    args = ap.parse_args()

    import optuna  # noqa: PLC0415

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
        f"Phase 3 cross-check: {len(top)} configs from {args.study_name} "
        f"on LoCoMo conv0 ({args.data})",
        file=sys.stderr,
    )
    for i, t in enumerate(top, 1):
        print(
            f"  #{i}: phase2_trial={t.number} fitness={t.value:.4f} {t.params}",
            file=sys.stderr,
        )

    if args.dry_run:
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    artifacts_root = out.parent / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)

    csv_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="phase3_") as tmp:
        tmp_dir = Path(tmp)
        for rank, t in enumerate(top, 1):
            cfg = {
                "_comment": f"Phase 3 cross-check: phase2 trial #{t.number}",
                "surface": "sdk",
                "config_overrides": trial_to_overrides(t),
            }
            cfg_path = tmp_dir / f"top{rank:02d}.json"
            cfg_path.write_text(json.dumps(cfg, indent=2))

            artifact = artifacts_root / f"top{rank:02d}_phase2trial{t.number}.json"
            print(
                f"\n=== rank {rank} (phase2 trial #{t.number}, "
                f"LTI-Bench fitness {t.value:.4f}) ===",
                file=sys.stderr,
            )
            t0 = time.time()
            result = run_locomo_for_config(
                cfg_path, Path(args.data), artifact, args.model
            )
            elapsed = time.time() - t0

            # locomo_eval writes {"aggregate": {"overall": {"mean_f1": ...,
            # "num_questions": ..., "llm_accuracy": ...}, ...}, "per_question": [...]}
            overall_f1 = (
                result.get("aggregate", {}).get("overall", {}).get("mean_f1")
                or result.get("summary", {}).get("overall_f1")  # back-compat
                or result.get("overall_f1")
                or 0.0
            )
            delta = overall_f1 - t.value  # NB: different metrics, but
                                          # >5pp drop is the gate
            print(
                f"  LoCoMo conv0 F1: {overall_f1:.4f}  "
                f"delta vs LTI-fitness: {delta:+.4f}  "
                f"({elapsed:.0f}s)",
                file=sys.stderr,
            )
            csv_rows.append(
                {
                    "rank": rank,
                    "phase2_trial": t.number,
                    "phase2_lti_fitness": t.value,
                    "phase3_locomo_f1": overall_f1,
                    "delta": delta,
                    "wall_seconds": elapsed,
                    **{f"params.{k}": v for k, v in t.params.items()},
                }
            )

    fieldnames = sorted({k for r in csv_rows for k in r.keys()})
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in csv_rows:
            w.writerow(r)

    # Verdict: drop any candidate whose LoCoMo F1 is > 5pp below LTI fitness.
    # NB: these are different metrics on different distributions; the 5pp gate
    # is a sanity check from the parent plan, not a strict apples-to-apples
    # comparison. A surviving candidate is "robust enough" — not "better".
    print(f"\n=== Phase 3 verdict ===", file=sys.stderr)
    survivors = [r for r in csv_rows if r["delta"] >= -0.05]
    dropped = [r for r in csv_rows if r["delta"] < -0.05]
    print(f"survivors: {len(survivors)}/{len(csv_rows)}", file=sys.stderr)
    if dropped:
        print(f"dropped (>5pp drop, likely LTI-overfitting):", file=sys.stderr)
        for r in dropped:
            print(
                f"  phase2_trial={r['phase2_trial']} "
                f"LTI={r['phase2_lti_fitness']:.4f} "
                f"LoCoMo={r['phase3_locomo_f1']:.4f}",
                file=sys.stderr,
            )
    print(f"\nwrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
