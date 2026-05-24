#!/usr/bin/env python3
"""Recompute LoCoMo aggregates with corrected category labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shared.metrics import LOCOMO_CATEGORIES, aggregate_results


def relabel(payload: dict) -> dict:
    rows = payload.get("per_question") or []
    for row in rows:
        category = row.get("category")
        row["category_name"] = LOCOMO_CATEGORIES.get(category, "unknown")
    next_payload = dict(payload)
    next_payload["per_question"] = rows
    next_payload["aggregate"] = aggregate_results(rows)
    return next_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Existing LoCoMo result JSON")
    parser.add_argument("--output", required=True, help="Corrected output JSON")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    corrected = relabel(payload)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corrected, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
