#!/usr/bin/env python3
"""Phase 2.5: per-question variance analysis across LTI-Bench sub-runs.

The Phase 2 sweep produced a bimodal fitness landscape — ~70% of
trials at f1≈0.65, ~30% at f1≈0.62 — with no clean parameter
explanation for the cluster split. Hypothesis: the gap is driven
by LLM-judge noise on a small set of *marginal questions* whose
answer is plausibly-but-not-definitely correct, so the judge flips
between trials.

This script aggregates the per-question records across all matching
result.json files and ranks each unique question by "how often the
judge flipped across (trial × sub-run) replicates." Questions where
the judge said CORRECT in some replicates and INCORRECT in others
are the ones moving the composite. Stable questions (always correct
or always wrong) don't.

Outputs:
- `tuning/runs/phase2.5/question_variance.csv` — one row per
  unique question. Columns: subscore, question, n_replicates,
  correct_rate, flip_count, f1_mean, f1_stddev.
- stdout summary: top-N most-variable questions with their text +
  estimated contribution to composite-variance.

Usage:
    python tuning/scripts/analyze_question_variance.py \
        [--glob 'tuning/runs/lti-*/run-*/result.json'] \
        [--top 15] \
        [--out tuning/runs/phase2.5/question_variance.csv]

Designed to be re-runnable. Cheap (no API). Matching is by
(subscore, question, expected) tuple — the bench is deterministic
so the question set is fixed across trials.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GLOB = "tuning/runs/lti-*/run-*/result.json"
DEFAULT_OUT = REPO_ROOT / "tuning" / "runs" / "phase2.5" / "question_variance.csv"


def collect_per_question(path: Path) -> list[dict[str, Any]]:
    """Read one result.json and emit one record per question."""
    with open(path) as f:
        data = json.load(f)
    detailed = data.get("detailed") or {}
    out: list[dict[str, Any]] = []
    for subscore, qs in detailed.items():
        if not isinstance(qs, list):
            continue
        for q in qs:
            if not isinstance(q, dict):
                continue
            out.append(
                {
                    "subscore": subscore,
                    "question": q.get("question", ""),
                    "expected": q.get("expected", ""),
                    "f1": float(q.get("f1", 0.0)),
                    "correct": bool(q.get("correct", False)),
                    "trial_path": str(path.relative_to(REPO_ROOT)),
                }
            )
    return out


def aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group per-question records and compute variance stats."""
    by_q: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        key = (r["subscore"], r["question"])
        by_q[key].append(r)

    rows = []
    for (subscore, question), reps in by_q.items():
        correct_count = sum(1 for r in reps if r["correct"])
        n = len(reps)
        f1s = [r["f1"] for r in reps]
        # Flip count: how many transitions between correct/incorrect
        # in trial order. A stable question has 0 flips. A noisy
        # question has many.
        flips = sum(1 for a, b in zip(reps, reps[1:]) if a["correct"] != b["correct"])
        rows.append(
            {
                "subscore": subscore,
                "question": question,
                "expected": reps[0]["expected"],
                "n_replicates": n,
                "correct_count": correct_count,
                "correct_rate": correct_count / n if n else 0.0,
                "flip_count": flips,
                "flip_rate": flips / max(1, n - 1),
                "f1_mean": statistics.mean(f1s) if f1s else 0.0,
                "f1_stddev": statistics.stdev(f1s) if len(f1s) >= 2 else 0.0,
            }
        )
    return rows


def variance_score(row: dict[str, Any]) -> float:
    """A single 'how marginal is this question' scalar.

    A question that's always-correct or always-wrong has score 0.
    A question that's exactly 50/50 across replicates has the max
    contribution to composite variance — score = 1.

    correct_rate * (1 - correct_rate) peaks at 0.25 when rate=0.5;
    we rescale to [0, 1] for readability.
    """
    p = row["correct_rate"]
    return 4 * p * (1 - p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glob", default=DEFAULT_GLOB)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    paths = [Path(p) for p in glob.glob(str(REPO_ROOT / args.glob))]
    if not paths:
        print(f"no result.json files matched {args.glob}", file=sys.stderr)
        return 1

    print(f"scanning {len(paths)} result.json files…", file=sys.stderr)
    records: list[dict[str, Any]] = []
    for p in paths:
        records.extend(collect_per_question(p))
    print(f"  {len(records)} per-question records", file=sys.stderr)

    rows = aggregate(records)
    rows.sort(key=variance_score, reverse=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "subscore",
                "question",
                "expected",
                "n_replicates",
                "correct_count",
                "correct_rate",
                "flip_count",
                "flip_rate",
                "f1_mean",
                "f1_stddev",
                "variance_score",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow({**r, "variance_score": round(variance_score(r), 4)})
    print(f"wrote {out} ({len(rows)} questions)", file=sys.stderr)

    # Stdout summary
    n_marginal = sum(1 for r in rows if 0 < r["correct_rate"] < 1)
    n_stable = len(rows) - n_marginal
    print(f"\nstable (always correct or always wrong): {n_stable}/{len(rows)}")
    print(f"marginal (judge flips at least once):    {n_marginal}/{len(rows)}\n")

    print(f"top {args.top} most-marginal questions (variance_score = 4p(1-p)):\n")
    for r in rows[: args.top]:
        if variance_score(r) == 0:
            break
        v = variance_score(r)
        print(
            f"  [{r['subscore']}] correct_rate={r['correct_rate']:.2f} "
            f"({r['correct_count']}/{r['n_replicates']}) "
            f"flips={r['flip_count']} variance={v:.3f}"
        )
        print(f"    Q: {r['question']}")
        print(f"    A: {r['expected']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
