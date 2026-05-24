from __future__ import annotations

import bootstrap_ci
import pytest


def test_locomo_question_values_skip_category_5():
    result = {
        "per_question": [
            {"category": 1, "f1": 0.25},
            {"category": 4, "f1": 0.75},
            {"category": 5, "f1": 1.0},
        ]
    }

    assert bootstrap_ci.locomo_question_values(result) == [0.25, 0.75]


def test_locomo_conversation_values_group_by_original_conv_index():
    result = {
        "per_question": [
            {"conv_index": 2, "category": 1, "f1": 0.2},
            {"conv_index": 2, "category": 1, "f1": 0.4},
            {"conv_index": 7, "category": 1, "f1": 0.9},
        ]
    }

    assert bootstrap_ci.locomo_conversation_values(result) == pytest.approx([0.3, 0.9])


def test_longmemeval_task_values_average_per_question_type():
    result = {
        "per_question": [
            {"question_type": "a", "correct": True},
            {"question_type": "a", "correct": False},
            {"question_type": "b", "correct": True},
        ]
    }

    assert bootstrap_ci.longmemeval_task_values(result) == [0.5, 1.0]


def test_bootstrap_mean_ci_contains_mean_and_unit_count():
    ci = bootstrap_ci.bootstrap_mean_ci([0.0, 1.0], n_boot=100, seed=1, alpha=0.05)
    assert ci["mean"] == 0.5
    assert ci["n_units"] == 2
    assert ci["ci_low"] <= ci["mean"] <= ci["ci_high"]
