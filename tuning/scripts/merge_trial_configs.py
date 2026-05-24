#!/usr/bin/env python3
"""Merge trial-config JSON files left-to-right.

Use this to create ablation configs that start from the frozen tuned winner
and then apply one ablation delta. Later files win on scalar collisions;
`adapter`, `config_overrides`, `base_decay_rates`, and `decay_floors` merge
recursively.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MERGE_KEYS = {"adapter", "config_overrides", "base_decay_rates", "decay_floors"}


def deep_merge(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if key == "_comment":
            continue
        if key in MERGE_KEYS and isinstance(dst.get(key), dict) and isinstance(value, dict):
            deep_merge(dst[key], value)
        else:
            dst[key] = value
    return dst


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def merge_configs(paths: list[Path]) -> dict[str, Any]:
    merged: dict[str, Any] = {"_comment": "Merged trial config"}
    sources = []
    for path in paths:
        sources.append(str(path))
        deep_merge(merged, load_config(path))
    merged["_sources"] = sources
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "configs",
        nargs="+",
        help="Config files, applied left-to-right",
    )
    parser.add_argument("--output", required=True, help="Merged config path")
    args = parser.parse_args()

    merged = merge_configs([Path(p) for p in args.configs])
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    print(json.dumps(merged, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
