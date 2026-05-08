"""Tests for `run_optuna.py`'s pure-Python helpers.

Subprocess + Optuna integration is exercised by the actual Phase 2
sweep; the parts worth pinning here are the fitness aggregation and
the dotted-key config expansion that drives every trial's overrides.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import run_optuna  # noqa: E402


# ---------------------------------------------------------------------------
# expand_dotted + deep_merge — config_overrides assembly
# ---------------------------------------------------------------------------


def test_expand_dotted_top_level_key():
    assert run_optuna.expand_dotted("direct_boost", 0.15) == {"direct_boost": 0.15}


def test_expand_dotted_nested_key():
    """The headline Phase 0a-sdk feature: base_decay_rates is a dict
    keyed by category. Optuna sample arrives as a flat float; the
    runner must rebuild the nested config_overrides shape."""
    assert run_optuna.expand_dotted("base_decay_rates.semantic", 240.0) == {
        "base_decay_rates": {"semantic": 240.0}
    }


def test_expand_dotted_three_level_key():
    """Defensive — current SDK has at most two-level paths, but the
    helper shouldn't lock that in."""
    assert run_optuna.expand_dotted("a.b.c", 1) == {"a": {"b": {"c": 1}}}


def test_deep_merge_combines_disjoint_top_level_keys():
    a = {"direct_boost": 0.1}
    b = {"associative_boost": 0.05}
    run_optuna.deep_merge(a, b)
    assert a == {"direct_boost": 0.1, "associative_boost": 0.05}


def test_deep_merge_combines_nested_keys_without_clobbering_siblings():
    """If trial samples both base_decay_rates.semantic and
    base_decay_rates.episodic, the merge must produce a single
    `base_decay_rates` dict with both keys — not overwrite."""
    a = {"base_decay_rates": {"semantic": 240.0}}
    b = {"base_decay_rates": {"episodic": 30.0}}
    run_optuna.deep_merge(a, b)
    assert a == {"base_decay_rates": {"semantic": 240.0, "episodic": 30.0}}


def test_deep_merge_src_wins_on_leaf_collision():
    a = {"base_decay_rates": {"semantic": 120.0}}
    b = {"base_decay_rates": {"semantic": 240.0}}
    run_optuna.deep_merge(a, b)
    assert a == {"base_decay_rates": {"semantic": 240.0}}


# ---------------------------------------------------------------------------
# walk + fitness_from_row
# ---------------------------------------------------------------------------


def test_walk_returns_nested_value():
    assert run_optuna.walk({"summary": {"decay_trivial": {"mean_f1": 0.6}}},
                           "summary.decay_trivial.mean_f1") == 0.6


def test_walk_returns_none_on_missing_key():
    assert run_optuna.walk({"summary": {}}, "summary.decay_trivial.mean_f1") is None


def test_fitness_weighted_composite_matches_hand_calc():
    """Spec: 0.20*decay + 0.30*core + 0.30*revival + 0.10*assoc + 0.10*ctx.
    With all sub-scores at 1.0, fitness must be 1.0 (perfect score
    means perfect fitness — the renormalization preserves the
    interpretation)."""
    row = {
        "median": {
            "summary.decay_trivial.mean_f1": 1.0,
            "summary.core_persistence.mean_f1": 1.0,
            "summary.revival.mean_f1": 1.0,
            "summary.associative.mean_f1": 1.0,
            "summary.contextual_retention.mean_f1": 1.0,
        }
    }
    weights = {
        "summary.decay_trivial.mean_f1": 0.20,
        "summary.core_persistence.mean_f1": 0.30,
        "summary.revival.mean_f1": 0.30,
        "summary.associative.mean_f1": 0.10,
        "summary.contextual_retention.mean_f1": 0.10,
    }
    assert abs(run_optuna.fitness_from_row(row, weights) - 1.0) < 1e-9


def test_fitness_with_known_per_score_values():
    """Hand-calc: 0.20*0.5 + 0.30*0.6 + 0.30*0.7 + 0.10*0.8 + 0.10*0.9
    = 0.10 + 0.18 + 0.21 + 0.08 + 0.09 = 0.66. With sum-of-weights=1.0
    no renormalization needed."""
    row = {
        "median": {
            "summary.decay_trivial.mean_f1": 0.5,
            "summary.core_persistence.mean_f1": 0.6,
            "summary.revival.mean_f1": 0.7,
            "summary.associative.mean_f1": 0.8,
            "summary.contextual_retention.mean_f1": 0.9,
        }
    }
    weights = {
        "summary.decay_trivial.mean_f1": 0.20,
        "summary.core_persistence.mean_f1": 0.30,
        "summary.revival.mean_f1": 0.30,
        "summary.associative.mean_f1": 0.10,
        "summary.contextual_retention.mean_f1": 0.10,
    }
    assert abs(run_optuna.fitness_from_row(row, weights) - 0.66) < 1e-9


def test_fitness_renormalizes_when_sub_score_missing():
    """If a sub-score is missing (older harness output, schema drift),
    the contributing weights are summed and the partial total
    renormalized — so the fitness still reads as a [0,1] composite
    across whatever sub-scores were available, not biased toward zero."""
    row = {
        "median": {
            "summary.decay_trivial.mean_f1": 1.0,
            "summary.core_persistence.mean_f1": 1.0,
            # revival, associative, contextual missing
        }
    }
    weights = {
        "summary.decay_trivial.mean_f1": 0.20,
        "summary.core_persistence.mean_f1": 0.30,
        "summary.revival.mean_f1": 0.30,
        "summary.associative.mean_f1": 0.10,
        "summary.contextual_retention.mean_f1": 0.10,
    }
    # Only 0.20 + 0.30 = 0.50 in weights matched. (0.20*1 + 0.30*1) / 0.50 = 1.0.
    assert abs(run_optuna.fitness_from_row(row, weights) - 1.0) < 1e-9


def test_fitness_raises_when_no_sub_score_present():
    """Defensive — if every weighted key is missing, the contributing
    weight is zero and we'd be dividing by zero. Raise instead so the
    Optuna trial reports an error, not NaN."""
    import pytest

    row = {"median": {"unrelated.metric": 0.5}}
    weights = {"summary.decay_trivial.mean_f1": 1.0}
    with pytest.raises(RuntimeError, match="weights produced no valid"):
        run_optuna.fitness_from_row(row, weights)
