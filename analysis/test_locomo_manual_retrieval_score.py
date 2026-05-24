from __future__ import annotations

import pytest

import locomo_manual_retrieval_score


def test_score_item_row_computes_recall_complete_and_mrr():
    item = {"evidence_ids": ["D1:1", "D1:2"]}
    row = {
        "retrieved": [
            {"rank": 1, "covers_evidence_ids": []},
            {"rank": 2, "covers_evidence_ids": ["D1:1"]},
            {"rank": 3, "covers_evidence_ids": ["D1:2"]},
        ]
    }

    scores = locomo_manual_retrieval_score.score_item_row(item, row, [2, 3])

    assert scores["mrr"] == pytest.approx(0.5)
    assert scores["recall@2"] == pytest.approx(0.5)
    assert scores["complete@2"] == 0.0
    assert scores["recall@3"] == 1.0
    assert scores["complete@3"] == 1.0


def test_score_packet_groups_by_label_and_category():
    packet = {
        "items": [
            {
                "subset_index": 0,
                "conv_index": 0,
                "question_index": 0,
                "category_name": "multi-hop",
                "evidence_ids": ["D1:1"],
                "rows": [
                    {
                        "label": "Full",
                        "retrieved": [{"rank": 1, "covers_evidence_ids": ["D1:1"]}],
                    }
                ],
            }
        ]
    }

    payload = locomo_manual_retrieval_score.score_packet(packet, [1])

    assert payload["rows"][0]["overall"]["recall@1"] == 1.0
    assert payload["rows"][0]["by_category"]["multi-hop"]["complete@1"] == 1.0
