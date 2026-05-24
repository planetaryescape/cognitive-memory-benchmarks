from __future__ import annotations

import pytest

import paired_locomo_delta


def result(rows):
    return {"per_question": rows}


def test_paired_metric_summary_positive_delta_and_win_loss_tie():
    full_rows = paired_locomo_delta.question_map(
        result(
            [
                {"conv_index": 0, "question_index": 0, "category": 1, "f1": 1.0},
                {"conv_index": 0, "question_index": 1, "category": 1, "f1": 0.5},
                {"conv_index": 0, "question_index": 2, "category": 1, "f1": 0.25},
            ]
        )
    )
    control_rows = paired_locomo_delta.question_map(
        result(
            [
                {"conv_index": 0, "question_index": 0, "category": 1, "f1": 0.5},
                {"conv_index": 0, "question_index": 1, "category": 1, "f1": 0.5},
                {"conv_index": 0, "question_index": 2, "category": 1, "f1": 0.75},
            ]
        )
    )

    summary = paired_locomo_delta.paired_metric_summary(
        full_rows,
        control_rows,
        "multi-hop",
        n_boot=100,
        seed=1,
        alpha=0.05,
        tie_tolerance=1e-12,
    )

    assert summary["n_questions"] == 3
    assert summary["delta_mean"] == pytest.approx(0.0)
    assert summary["wins"] == 1
    assert summary["losses"] == 1
    assert summary["ties"] == 1


def test_question_map_excludes_adversarial_category():
    rows = paired_locomo_delta.question_map(
        result(
            [
                {"conv_index": 0, "question_index": 0, "category": 4, "f1": 0.2},
                {"conv_index": 0, "question_index": 1, "category": 5, "f1": 1.0},
            ]
        )
    )

    assert list(rows) == [(0, 0)]


def test_parse_row_spec_requires_label_and_path():
    assert paired_locomo_delta.parse_row_spec("Vector=run/result.json") == (
        "Vector",
        "run/result.json",
    )
    with pytest.raises(ValueError):
        paired_locomo_delta.parse_row_spec("run/result.json")
