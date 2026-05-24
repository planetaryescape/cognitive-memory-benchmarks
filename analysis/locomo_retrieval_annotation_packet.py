#!/usr/bin/env python3
"""Build a manual annotation packet from LoCoMo retrieval results."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QuestionKey = tuple[int, int]


def parse_row_spec(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError("row specs must be LABEL=PATH")
    label, path = spec.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label or not path:
        raise ValueError("row specs must include both label and path")
    return label, path


def result_question_map(path: str | Path) -> dict[QuestionKey, dict[str, Any]]:
    payload = json.loads(Path(path).read_text())
    rows = {}
    for row in payload.get("per_question") or []:
        rows[(int(row.get("conv_index", 0)), int(row.get("question_index", 0)))] = row
    return rows


def build_packet(
    *,
    subset_path: str | Path,
    row_specs: list[str],
    top_k: int,
) -> dict[str, Any]:
    subset = json.loads(Path(subset_path).read_text())
    row_maps = []
    for spec in row_specs:
        label, path = parse_row_spec(spec)
        row_maps.append((label, path, result_question_map(path)))

    items = []
    for question in subset["questions"]:
        key = (int(question["conv_index"]), int(question["question_index"]))
        rows = []
        for label, path, question_map in row_maps:
            result = question_map.get(key)
            retrieved = []
            if result:
                retrieved = [
                    {
                        "rank": rank,
                        "text": text,
                        "covers_evidence_ids": [],
                        "annotation_notes": "",
                    }
                    for rank, text in enumerate(
                        result.get("retrieved_contents", [])[:top_k],
                        start=1,
                    )
                ]
            rows.append(
                {
                    "label": label,
                    "source": path,
                    "prediction": result.get("prediction") if result else None,
                    "f1": result.get("f1") if result else None,
                    "retrieved": retrieved,
                }
            )
        items.append({**question, "rows": rows})

    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "subset_source": str(subset_path),
        "top_k": top_k,
        "annotation_instructions": [
            "For each retrieved memory, add evidence IDs it fully or partially supports to covers_evidence_ids.",
            "Use the evidence_ids listed on the question; leave the list empty for irrelevant memories.",
            "Complete-evidence recall is satisfied when the union of covered IDs contains every evidence_id for the question.",
        ],
        "items": items,
    }


def write_markdown(packet: dict[str, Any], output: str | Path) -> None:
    lines = [
        "# LoCoMo Retrieval Evidence Annotation Packet",
        "",
        f"Subset: `{packet['subset_source']}`",
        f"Top-k shown: `{packet['top_k']}`",
        "",
        "Annotate by editing the JSON packet, not this Markdown summary.",
        "",
    ]
    for item in packet["items"]:
        lines.extend(
            [
                f"## {item['subset_index']}. {item['category_name']} c{item['conv_index']} q{item['question_index']}",
                "",
                f"Question: {item['question']}",
                "",
                f"Answer: {item['answer']}",
                "",
                "Evidence:",
            ]
        )
        for evidence_id, text in zip(item["evidence_ids"], item["evidence_texts"]):
            lines.append(f"- `{evidence_id}`: {text}")
        lines.append("")
        for row in item["rows"]:
            lines.extend(
                [
                    f"### {row['label']}",
                    "",
                    f"Prediction: {row['prediction']}",
                    "",
                ]
            )
            for retrieved in row["retrieved"]:
                lines.append(f"{retrieved['rank']}. {retrieved['text']}")
            lines.append("")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", required=True)
    parser.add_argument("--row", action="append", default=[], help="LABEL=path/to/result.json")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown", default=None)
    args = parser.parse_args()

    packet = build_packet(subset_path=args.subset, row_specs=args.row, top_k=args.top_k)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")
    if args.markdown:
        write_markdown(packet, args.markdown)
    print(json.dumps({"items": len(packet["items"]), "top_k": packet["top_k"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
