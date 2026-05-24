from __future__ import annotations

import locomo_evidence_subset


def test_iter_evidence_questions_resolves_dialog_texts():
    data = [
        {
            "conversation": {
                "session_1": [
                    {"dia_id": "D1:1", "text": "Maria likes aerial yoga."},
                    {"dia_id": "D1:2", "text": "John likes kickboxing."},
                ]
            },
            "qa": [
                {
                    "question": "What does Maria like?",
                    "answer": "aerial yoga",
                    "category": 1,
                    "evidence": ["D1:1"],
                },
                {
                    "question": "Adversarial?",
                    "answer": "unknown",
                    "category": 5,
                    "evidence": ["D1:2"],
                },
            ],
        }
    ]

    questions = locomo_evidence_subset.iter_evidence_questions(data, [2])

    assert len(questions) == 1
    assert questions[0]["original_conv_index"] == 2
    assert questions[0]["evidence_texts"] == ["Maria likes aerial yoga."]


def test_select_subset_respects_quotas_and_seed():
    questions = [
        {"category": 2, "category_name": "multi-hop", "conv_index": 0, "question_index": idx}
        for idx in range(5)
    ]
    selected = locomo_evidence_subset.select_subset(
        questions,
        {"multi-hop": 3},
        seed=1,
    )

    assert len(selected) == 3
    assert [row["subset_index"] for row in selected] == [0, 1, 2]


def test_parse_quotas_defaults_and_overrides():
    assert locomo_evidence_subset.parse_quotas(None)["multi-hop"] == 40
    assert locomo_evidence_subset.parse_quotas(["temporal=7"]) == {"temporal": 7}
