#!/usr/bin/env python3
"""Bootstrap confidence intervals for benchmark result JSON files."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("cannot percentile an empty sample")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def bootstrap_mean_ci(
    values: list[float],
    n_boot: int,
    seed: int,
    alpha: float,
) -> dict[str, float]:
    if not values:
        raise ValueError("no values to bootstrap")
    rng = random.Random(seed)
    boots = []
    n = len(values)
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boots.append(mean(sample))
    return {
        "mean": mean(values),
        "ci_low": percentile(boots, alpha / 2),
        "ci_high": percentile(boots, 1 - alpha / 2),
        "n_units": n,
        "n_boot": n_boot,
        "alpha": alpha,
    }


def infer_metric(result: dict[str, Any]) -> str:
    per_question = result.get("per_question") or []
    if per_question and "f1" in per_question[0]:
        return "locomo-f1"
    if per_question and "correct" in per_question[0]:
        return "longmemeval-accuracy"
    if "per_conv" in result:
        return "locomo-f1"
    raise ValueError("could not infer metric; pass --metric")


def locomo_question_values(result: dict[str, Any]) -> list[float]:
    values = []
    for row in result.get("per_question") or []:
        category = row.get("category")
        if category is not None and int(category) > 4:
            continue
        if "f1" in row:
            values.append(float(row["f1"]))
    return values


def locomo_conversation_values(result: dict[str, Any]) -> list[float]:
    if "per_conv" in result:
        return [float(row["mean_f1"]) for row in result["per_conv"]]

    groups: dict[int, list[float]] = defaultdict(list)
    for row in result.get("per_question") or []:
        category = row.get("category")
        if category is not None and int(category) > 4:
            continue
        if "f1" in row:
            groups[int(row.get("conv_index", 0))].append(float(row["f1"]))
    return [mean(vals) for vals in groups.values() if vals]


def longmemeval_question_values(result: dict[str, Any]) -> list[float]:
    return [1.0 if row.get("correct") else 0.0 for row in result.get("per_question") or []]


def longmemeval_task_values(result: dict[str, Any]) -> list[float]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in result.get("per_question") or []:
        groups[row["question_type"]].append(1.0 if row.get("correct") else 0.0)
    return [mean(vals) for vals in groups.values() if vals]


def extract_values(result: dict[str, Any], metric: str, unit: str) -> list[float]:
    if metric == "auto":
        metric = infer_metric(result)
    if metric == "locomo-f1" and unit == "question":
        return locomo_question_values(result)
    if metric == "locomo-f1" and unit == "conversation":
        return locomo_conversation_values(result)
    if metric == "longmemeval-accuracy" and unit == "question":
        return longmemeval_question_values(result)
    if metric == "longmemeval-accuracy" and unit == "task":
        return longmemeval_task_values(result)
    raise ValueError(f"unsupported metric/unit combination: {metric}/{unit}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", help="Benchmark result JSON")
    parser.add_argument(
        "--metric",
        choices=["auto", "locomo-f1", "longmemeval-accuracy"],
        default="auto",
    )
    parser.add_argument(
        "--unit",
        choices=["question", "conversation", "task"],
        default="question",
    )
    parser.add_argument("--n-boot", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260511)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = json.loads(Path(args.result).read_text())
    values = extract_values(result, args.metric, args.unit)
    ci = bootstrap_mean_ci(values, args.n_boot, args.seed, args.alpha)
    payload = {
        "source": args.result,
        "metric": infer_metric(result) if args.metric == "auto" else args.metric,
        "unit": args.unit,
        **ci,
    }

    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
