#!/usr/bin/env python3
"""Score manually annotated LoCoMo retrieval evidence packets."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def covered_ids(row: dict[str, Any], k: int) -> set[str]:
    covered = set()
    for retrieved in row.get("retrieved", [])[:k]:
        for evidence_id in retrieved.get("covers_evidence_ids", []) or []:
            covered.add(str(evidence_id))
    return covered


def reciprocal_rank(row: dict[str, Any]) -> float:
    for retrieved in row.get("retrieved", []):
        if retrieved.get("covers_evidence_ids"):
            return 1.0 / float(retrieved.get("rank", 0) or 1)
    return 0.0


def score_item_row(item: dict[str, Any], row: dict[str, Any], k_values: list[int]) -> dict[str, float]:
    evidence_ids = {str(evidence_id) for evidence_id in item.get("evidence_ids", [])}
    if not evidence_ids:
        raise ValueError("cannot score item without evidence_ids")
    scores: dict[str, float] = {"mrr": reciprocal_rank(row)}
    for k in k_values:
        covered = covered_ids(row, k)
        scores[f"recall@{k}"] = len(evidence_ids & covered) / len(evidence_ids)
        scores[f"complete@{k}"] = 1.0 if evidence_ids <= covered else 0.0
    return scores


def summarize(scores: list[dict[str, float]], k_values: list[int]) -> dict[str, float | int]:
    payload: dict[str, float | int] = {"n_questions": len(scores)}
    payload["mrr"] = mean([score["mrr"] for score in scores])
    for k in k_values:
        payload[f"recall@{k}"] = mean([score[f"recall@{k}"] for score in scores])
        payload[f"complete@{k}"] = mean([score[f"complete@{k}"] for score in scores])
    return payload


def score_packet(packet: dict[str, Any], k_values: list[int]) -> dict[str, Any]:
    by_label: dict[str, list[dict[str, float]]] = defaultdict(list)
    by_label_category: dict[str, dict[str, list[dict[str, float]]]] = defaultdict(lambda: defaultdict(list))
    per_question = []

    for item in packet.get("items", []):
        for row in item.get("rows", []):
            scores = score_item_row(item, row, k_values)
            label = row["label"]
            category = item["category_name"]
            by_label[label].append(scores)
            by_label_category[label][category].append(scores)
            per_question.append(
                {
                    "subset_index": item["subset_index"],
                    "conv_index": item["conv_index"],
                    "question_index": item["question_index"],
                    "category_name": category,
                    "label": label,
                    **scores,
                }
            )

    rows = []
    for label, label_scores in by_label.items():
        rows.append(
            {
                "label": label,
                "overall": summarize(label_scores, k_values),
                "by_category": {
                    category: summarize(category_scores, k_values)
                    for category, category_scores in sorted(by_label_category[label].items())
                },
            }
        )
    return {"k_values": k_values, "rows": rows, "per_question": per_question}


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def write_markdown(payload: dict[str, Any], output: str | Path) -> None:
    k_values = payload["k_values"]
    headers = ["Row", "n", "MRR"]
    for k in k_values:
        headers.extend([f"Recall@{k}", f"Complete@{k}"])
    lines = [
        "# LoCoMo Manual Retrieval Evidence Scores",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] + ["---:"] * (len(headers) - 1)) + " |",
    ]
    for row in payload["rows"]:
        overall = row["overall"]
        values = [row["label"], overall["n_questions"], overall["mrr"]]
        for k in k_values:
            values.extend([overall[f"recall@{k}"], overall[f"complete@{k}"]])
        lines.append("| " + " | ".join(fmt(value) for value in values) + " |")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", help="Annotated packet JSON")
    parser.add_argument("--k-values", nargs="+", type=int, default=[10, 20])
    parser.add_argument("--output", default=None)
    parser.add_argument("--markdown", default=None)
    args = parser.parse_args()

    packet = json.loads(Path(args.packet).read_text())
    payload = score_packet(packet, args.k_values)
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n")
    if args.markdown:
        write_markdown(payload, args.markdown)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
