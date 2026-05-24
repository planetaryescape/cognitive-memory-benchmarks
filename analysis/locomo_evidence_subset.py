#!/usr/bin/env python3
"""Create a deterministic LoCoMo evidence-labeling subset."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATEGORY_NAMES = {
    1: "multi-hop",
    2: "temporal",
    3: "open-domain",
    4: "single-hop",
    5: "adversarial",
}

DEFAULT_QUOTAS = {
    "multi-hop": 40,
    "temporal": 30,
    "single-hop": 15,
    "open-domain": 15,
}


def load_original_indices(manifest_path: str | Path | None) -> list[int] | None:
    if manifest_path is None:
        return None
    manifest = json.loads(Path(manifest_path).read_text())
    return manifest.get("locomo", {}).get("test_conversation_indices")


def resolve_dialog_texts(conversation: dict[str, Any]) -> dict[str, str]:
    conv_data = conversation.get("conversation", {})
    texts: dict[str, str] = {}
    session_keys = sorted(
        [
            key
            for key in conv_data
            if key.startswith("session_")
            and not key.endswith(("_date_time", "_observation", "_summary"))
        ],
        key=lambda key: int(key.split("_")[1]),
    )
    for session_key in session_keys:
        for turn in conv_data.get(session_key, []):
            dia_id = turn.get("dia_id")
            text = turn.get("text")
            if dia_id and text:
                texts[str(dia_id)] = str(text)
    return texts


def resolve_evidence_texts(evidence_ids: list[Any], dialog_texts: dict[str, str]) -> list[str]:
    evidence_texts = []
    for raw_evidence_id in evidence_ids:
        evidence_id = str(raw_evidence_id).strip()
        if evidence_id in dialog_texts:
            evidence_texts.append(dialog_texts[evidence_id])
            continue
        for dia_id, text in dialog_texts.items():
            if evidence_id in dia_id or dia_id in evidence_id:
                evidence_texts.append(text)
                break
    return evidence_texts


def iter_evidence_questions(
    data: list[dict[str, Any]],
    original_indices: list[int] | None = None,
) -> list[dict[str, Any]]:
    questions = []
    for conv_index, conversation in enumerate(data):
        dialog_texts = resolve_dialog_texts(conversation)
        original_conv_index = (
            original_indices[conv_index]
            if original_indices and conv_index < len(original_indices)
            else None
        )
        for question_index, qa in enumerate(conversation.get("qa", [])):
            category = int(qa.get("category", 0))
            if category not in (1, 2, 3, 4):
                continue
            evidence_ids = qa.get("evidence") or []
            evidence_texts = resolve_evidence_texts(evidence_ids, dialog_texts)
            if not evidence_texts:
                continue
            questions.append(
                {
                    "conv_index": conv_index,
                    "original_conv_index": original_conv_index,
                    "question_index": question_index,
                    "category": category,
                    "category_name": CATEGORY_NAMES[category],
                    "question": str(qa.get("question", "")),
                    "answer": str(qa.get("answer", "")),
                    "evidence_ids": [str(eid) for eid in evidence_ids],
                    "evidence_texts": evidence_texts,
                }
            )
    return questions


def parse_quotas(values: list[str] | None) -> dict[str, int]:
    if not values:
        return dict(DEFAULT_QUOTAS)
    quotas: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("quotas must use category=count")
        category, count = value.split("=", 1)
        category = category.strip()
        if category not in DEFAULT_QUOTAS:
            raise ValueError(f"unknown quota category: {category}")
        quotas[category] = int(count)
    return quotas


def select_subset(
    questions: list[dict[str, Any]],
    quotas: dict[str, int],
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        by_category[question["category_name"]].append(question)

    selected = []
    for category, quota in quotas.items():
        candidates = list(by_category[category])
        rng.shuffle(candidates)
        selected.extend(candidates[: min(quota, len(candidates))])

    selected.sort(
        key=lambda row: (
            row["category"],
            row["conv_index"],
            row["question_index"],
        )
    )
    return [dict(row, subset_index=index) for index, row in enumerate(selected)]


def build_subset(
    *,
    data_path: str | Path,
    manifest_path: str | Path | None,
    quotas: dict[str, int],
    seed: int,
) -> dict[str, Any]:
    data = json.loads(Path(data_path).read_text())
    original_indices = load_original_indices(manifest_path)
    candidates = iter_evidence_questions(data, original_indices)
    selected = select_subset(candidates, quotas, seed)
    counts = Counter(row["category_name"] for row in selected)
    candidate_counts = Counter(row["category_name"] for row in candidates)
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "data_source": str(data_path),
        "manifest_source": str(manifest_path) if manifest_path else None,
        "seed": seed,
        "quotas": quotas,
        "candidate_counts": dict(sorted(candidate_counts.items())),
        "category_counts": dict(sorted(counts.items())),
        "selected_count": len(selected),
        "questions": selected,
    }


def write_markdown(payload: dict[str, Any], output: str | Path) -> None:
    lines = [
        "# LoCoMo Evidence Labeling Subset",
        "",
        f"Data: `{payload['data_source']}`",
        f"Seed: `{payload['seed']}`",
        f"Selected questions: `{payload['selected_count']}`",
        "",
        "Use this file to label which retrieved memories contain enough evidence to answer each question.",
        "",
    ]
    for question in payload["questions"]:
        evidence = "\n".join(
            f"- `{eid}`: {text}"
            for eid, text in zip(question["evidence_ids"], question["evidence_texts"])
        )
        lines.extend(
            [
                f"## {question['subset_index']}. {question['category_name']} c{question['conv_index']} q{question['question_index']}",
                "",
                f"Question: {question['question']}",
                "",
                f"Answer: {question['answer']}",
                "",
                "Evidence:",
                evidence,
                "",
            ]
        )
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--quota", action="append", default=None, help="category=count")
    parser.add_argument("--seed", type=int, default=20260514)
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown", default=None)
    args = parser.parse_args()

    payload = build_subset(
        data_path=args.data,
        manifest_path=args.manifest,
        quotas=parse_quotas(args.quota),
        seed=args.seed,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.markdown:
        write_markdown(payload, args.markdown)
    print(json.dumps({k: payload[k] for k in ("selected_count", "category_counts", "candidate_counts")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
