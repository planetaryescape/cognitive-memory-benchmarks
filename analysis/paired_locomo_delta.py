#!/usr/bin/env python3
"""Paired LoCoMo Full-minus-control delta summaries.

This script compares completed LoCoMo ``result.json`` files question by
question. Positive deltas mean the full system scored higher than the control.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


CATEGORIES = {
    "overall": None,
    "multi-hop": 1,
    "temporal": 2,
    "open-domain": 3,
    "single-hop": 4,
}


QuestionKey = tuple[int, int]


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("cannot percentile an empty sample")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def bootstrap_mean_ci(
    values: list[float],
    n_boot: int,
    seed: int,
    alpha: float,
) -> dict[str, float | int]:
    if not values:
        raise ValueError("no values to bootstrap")
    rng = random.Random(seed)
    n = len(values)
    boots = []
    for _ in range(n_boot):
        boots.append(mean([values[rng.randrange(n)] for _ in range(n)]))
    return {
        "mean": mean(values),
        "ci_low": percentile(boots, alpha / 2),
        "ci_high": percentile(boots, 1 - alpha / 2),
        "n_units": n,
        "n_boot": n_boot,
        "alpha": alpha,
    }


def load_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def question_map(result: dict[str, Any]) -> dict[QuestionKey, dict[str, Any]]:
    rows: dict[QuestionKey, dict[str, Any]] = {}
    for row in result.get("per_question") or []:
        category = int(row.get("category", 5))
        if category > 4:
            continue
        key = (int(row.get("conv_index", 0)), int(row.get("question_index", 0)))
        rows[key] = row
    return rows


def metric_keys(rows: dict[QuestionKey, dict[str, Any]], metric: str) -> set[QuestionKey]:
    if metric not in CATEGORIES:
        raise ValueError(f"unknown metric/category: {metric}")
    category = CATEGORIES[metric]
    if category is None:
        return set(rows)
    return {key for key, row in rows.items() if int(row.get("category", 5)) == category}


def paired_metric_summary(
    full_rows: dict[QuestionKey, dict[str, Any]],
    control_rows: dict[QuestionKey, dict[str, Any]],
    metric: str,
    *,
    n_boot: int,
    seed: int,
    alpha: float,
    tie_tolerance: float,
) -> dict[str, Any]:
    keys = sorted(metric_keys(full_rows, metric) & metric_keys(control_rows, metric))
    if not keys:
        return {
            "n_questions": 0,
            "missing_from_control": len(metric_keys(full_rows, metric)),
            "full_mean_f1": None,
            "control_mean_f1": None,
            "delta_mean": None,
            "delta_ci_low": None,
            "delta_ci_high": None,
            "wins": 0,
            "losses": 0,
            "ties": 0,
        }

    full_scores = [float(full_rows[key]["f1"]) for key in keys]
    control_scores = [float(control_rows[key]["f1"]) for key in keys]
    deltas = [full - control for full, control in zip(full_scores, control_scores)]
    ci = bootstrap_mean_ci(deltas, n_boot=n_boot, seed=seed, alpha=alpha)

    wins = sum(1 for delta in deltas if delta > tie_tolerance)
    losses = sum(1 for delta in deltas if delta < -tie_tolerance)
    ties = len(deltas) - wins - losses
    missing = len(metric_keys(full_rows, metric) - set(control_rows))

    return {
        "n_questions": len(keys),
        "missing_from_control": missing,
        "full_mean_f1": mean(full_scores),
        "control_mean_f1": mean(control_scores),
        "delta_mean": ci["mean"],
        "delta_ci_low": ci["ci_low"],
        "delta_ci_high": ci["ci_high"],
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "n_boot": ci["n_boot"],
        "alpha": ci["alpha"],
    }


def category_counts(full_rows: dict[QuestionKey, dict[str, Any]], metrics: list[str]) -> dict[str, int]:
    return {metric: len(metric_keys(full_rows, metric)) for metric in metrics}


def parse_row_spec(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError("row specs must be LABEL=PATH")
    label, path = spec.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label or not path:
        raise ValueError("row specs must include both label and path")
    return label, path


def analyze(
    full_path: str,
    row_specs: list[str],
    *,
    metrics: list[str],
    n_boot: int,
    seed: int,
    alpha: float,
    tie_tolerance: float,
) -> dict[str, Any]:
    full_result = load_result(full_path)
    full_rows = question_map(full_result)
    rows = []
    for index, row_spec in enumerate(row_specs):
        label, path = parse_row_spec(row_spec)
        control_rows = question_map(load_result(path))
        rows.append(
            {
                "label": label,
                "source": path,
                "metrics": {
                    metric: paired_metric_summary(
                        full_rows,
                        control_rows,
                        metric,
                        n_boot=n_boot,
                        seed=seed + index,
                        alpha=alpha,
                        tie_tolerance=tie_tolerance,
                    )
                    for metric in metrics
                },
            }
        )
    return {
        "full_source": full_path,
        "metrics": metrics,
        "category_counts": category_counts(full_rows, metrics),
        "rows": rows,
    }


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def format_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Paired LoCoMo architecture-control deltas",
        "",
        f"Full result: `{payload['full_source']}`",
        "",
        "Positive deltas are `Full - Control`.",
        "",
    ]
    for metric in payload["metrics"]:
        lines.extend(
            [
                f"## {metric}",
                "",
                "| Control | n | Full F1 | Control F1 | Delta | 95% CI | W/L/T |",
                "| --- | ---: | ---: | ---: | ---: | --- | ---: |",
            ]
        )
        for row in payload["rows"]:
            stats = row["metrics"][metric]
            ci = f"[{fmt(stats['delta_ci_low'])}, {fmt(stats['delta_ci_high'])}]"
            wlt = f"{stats['wins']}/{stats['losses']}/{stats['ties']}"
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["label"],
                        fmt(stats["n_questions"]),
                        fmt(stats["full_mean_f1"]),
                        fmt(stats["control_mean_f1"]),
                        fmt(stats["delta_mean"]),
                        ci,
                        wlt,
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", required=True, help="Full-system LoCoMo result.json")
    parser.add_argument(
        "--row",
        action="append",
        default=[],
        help="Control row as LABEL=path/to/result.json. Repeatable.",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=["overall", "multi-hop", "temporal"],
        choices=sorted(CATEGORIES),
    )
    parser.add_argument("--n-boot", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260514)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--tie-tolerance", type=float, default=1e-12)
    parser.add_argument("--output", default=None, help="Write JSON summary here")
    parser.add_argument("--markdown", default=None, help="Write Markdown summary here")
    args = parser.parse_args()

    payload = analyze(
        args.full,
        args.row,
        metrics=args.metrics,
        n_boot=args.n_boot,
        seed=args.seed,
        alpha=args.alpha,
        tie_tolerance=args.tie_tolerance,
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n")
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(format_markdown(payload) + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
