from __future__ import annotations

import json

import locomo_retrieval_annotation_packet


def test_build_packet_includes_retrieved_annotation_slots(tmp_path):
    subset = {
        "questions": [
            {
                "subset_index": 0,
                "conv_index": 0,
                "question_index": 2,
                "category_name": "multi-hop",
                "question": "Who?",
                "answer": "Maria",
                "evidence_ids": ["D1:1"],
                "evidence_texts": ["Maria likes yoga."],
            }
        ]
    }
    result = {
        "per_question": [
            {
                "conv_index": 0,
                "question_index": 2,
                "prediction": "Maria",
                "f1": 1.0,
                "retrieved_contents": ["Maria likes yoga.", "John likes running."],
            }
        ]
    }
    subset_path = tmp_path / "subset.json"
    result_path = tmp_path / "result.json"
    subset_path.write_text(json.dumps(subset))
    result_path.write_text(json.dumps(result))

    packet = locomo_retrieval_annotation_packet.build_packet(
        subset_path=subset_path,
        row_specs=[f"Full={result_path}"],
        top_k=1,
    )

    retrieved = packet["items"][0]["rows"][0]["retrieved"]
    assert retrieved == [
        {
            "rank": 1,
            "text": "Maria likes yoga.",
            "covers_evidence_ids": [],
            "annotation_notes": "",
        }
    ]


def test_parse_row_spec():
    assert locomo_retrieval_annotation_packet.parse_row_spec("Full=run/result.json") == (
        "Full",
        "run/result.json",
    )
