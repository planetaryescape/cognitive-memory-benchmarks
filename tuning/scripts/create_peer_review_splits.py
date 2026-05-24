#!/usr/bin/env python3
"""Create deterministic dev/test splits for the peer-review campaign.

LoCoMo is split by conversation, never by question. LongMemEval-S is
stratified by `(question_type, abstention)` so dev/test preserve task mix.

By default this writes only small provenance files. Add `--materialize` to
write full JSON benchmark files that can be passed directly to the existing
evaluation scripts.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "tuning" / "splits" / "peer_review_20260511"


def load_json(path: Path) -> Any:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def split_locomo(n_conversations: int, dev_count: int, seed: int) -> tuple[list[int], list[int]]:
    if not 0 < dev_count < n_conversations:
        raise ValueError("locomo dev count must be between 1 and n_conversations - 1")
    indices = list(range(n_conversations))
    random.Random(seed).shuffle(indices)
    dev = sorted(indices[:dev_count])
    test = sorted(indices[dev_count:])
    return dev, test


def split_longmemeval_ids(
    data: list[dict[str, Any]],
    dev_frac: float,
    seed: int,
) -> tuple[list[str], list[str]]:
    if not 0.0 < dev_frac < 1.0:
        raise ValueError("longmemeval dev fraction must be in (0, 1)")

    rng = random.Random(seed)
    strata: dict[tuple[str, bool], list[str]] = defaultdict(list)
    for item in data:
        question_id = item["question_id"]
        strata[(item["question_type"], "_abs" in question_id)].append(question_id)

    dev: list[str] = []
    test: list[str] = []
    for ids in strata.values():
        shuffled = list(ids)
        rng.shuffle(shuffled)
        n_dev = round(len(shuffled) * dev_frac)
        if len(shuffled) > 1:
            n_dev = min(max(1, n_dev), len(shuffled) - 1)
        dev.extend(shuffled[:n_dev])
        test.extend(shuffled[n_dev:])

    return sorted(dev), sorted(test)


def count_locomo_questions(data: list[dict[str, Any]], indices: list[int]) -> int:
    return sum(len(data[i].get("qa", [])) for i in indices)


def count_longmemeval_types(data: list[dict[str, Any]], ids: set[str]) -> dict[str, int]:
    return dict(Counter(item["question_type"] for item in data if item["question_id"] in ids))


def materialize_locomo(data: list[dict[str, Any]], indices: list[int]) -> list[dict[str, Any]]:
    return [data[i] for i in indices]


def materialize_longmemeval(data: list[dict[str, Any]], ids: set[str]) -> list[dict[str, Any]]:
    return [item for item in data if item["question_id"] in ids]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--locomo-data",
        default=str(REPO_ROOT / "locomo" / "data" / "locomo10.json"),
    )
    parser.add_argument(
        "--longmemeval-data",
        default=str(REPO_ROOT / "longmemeval" / "data" / "longmemeval_s_cleaned.json"),
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--seed", type=int, default=20260511)
    parser.add_argument("--locomo-dev-conversations", type=int, default=5)
    parser.add_argument("--longmemeval-dev-frac", type=float, default=0.4)
    parser.add_argument(
        "--materialize",
        action="store_true",
        help="Also write full split JSON data files",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing split directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.force:
        raise SystemExit(
            f"refusing to overwrite non-empty split directory: {out_dir} (use --force)"
        )

    locomo_path = Path(args.locomo_data)
    longmemeval_path = Path(args.longmemeval_data)
    locomo = load_json(locomo_path)
    longmemeval = load_json(longmemeval_path)

    locomo_dev, locomo_test = split_locomo(len(locomo), args.locomo_dev_conversations, args.seed)
    long_dev, long_test = split_longmemeval_ids(longmemeval, args.longmemeval_dev_frac, args.seed)
    long_dev_set = set(long_dev)
    long_test_set = set(long_test)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "notes": [
            "LoCoMo split unit is conversation; no questions from the same conversation cross dev/test.",
            "LongMemEval-S split is stratified by question_type and abstention flag.",
            "This is a clean protocol split, not a pristine benchmark: full "
            "benchmark results were already inspected before this split existed.",
        ],
        "locomo": {
            "source": str(locomo_path),
            "dev_conversation_indices": locomo_dev,
            "test_conversation_indices": locomo_test,
            "dev_conversations": len(locomo_dev),
            "test_conversations": len(locomo_test),
            "dev_questions_all_categories": count_locomo_questions(locomo, locomo_dev),
            "test_questions_all_categories": count_locomo_questions(locomo, locomo_test),
        },
        "longmemeval_s": {
            "source": str(longmemeval_path),
            "dev_question_ids_file": "longmemeval_s_dev_ids.json",
            "test_question_ids_file": "longmemeval_s_test_ids.json",
            "dev_questions": len(long_dev),
            "test_questions": len(long_test),
            "dev_by_type": count_longmemeval_types(longmemeval, long_dev_set),
            "test_by_type": count_longmemeval_types(longmemeval, long_test_set),
        },
        "materialized_files": {
            "written": bool(args.materialize),
            "locomo_dev": "locomo_dev.json",
            "locomo_test": "locomo_test.json",
            "longmemeval_s_dev": "longmemeval_s_dev.json",
            "longmemeval_s_test": "longmemeval_s_test.json",
        },
    }

    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "longmemeval_s_dev_ids.json", long_dev)
    write_json(out_dir / "longmemeval_s_test_ids.json", long_test)

    if args.materialize:
        write_json(out_dir / "locomo_dev.json", materialize_locomo(locomo, locomo_dev))
        write_json(out_dir / "locomo_test.json", materialize_locomo(locomo, locomo_test))
        write_json(
            out_dir / "longmemeval_s_dev.json",
            materialize_longmemeval(longmemeval, long_dev_set),
        )
        write_json(
            out_dir / "longmemeval_s_test.json",
            materialize_longmemeval(longmemeval, long_test_set),
        )

    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
