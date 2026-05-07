"""Tests for `run_trial.py`'s aggregation logic.

Subprocess execution path is exercised by the 0g smoke run; the parts
that are pure-Python and worth pinning are: dotted-key value walk,
median + stddev computation, and the trial-id allocation. These all
feed directly into the determinism-gate decision (median-of-3 with
stddev < 1pp), so a regression here corrupts every subsequent trial
log.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Importable as a script-adjacent module.
sys.path.insert(0, str(Path(__file__).parent))

import run_trial  # noqa: E402


# ---------------------------------------------------------------------------
# _walk — dotted-key lookup into nested result dicts
# ---------------------------------------------------------------------------


def test_walk_returns_top_level_value():
    assert run_trial._walk({"composite": 0.87}, "composite") == 0.87


def test_walk_returns_nested_value():
    assert run_trial._walk({"score": {"composite": 0.87}}, "score.composite") == 0.87


def test_walk_returns_none_on_missing_key():
    assert run_trial._walk({"a": 1}, "b") is None


def test_walk_returns_none_when_walking_through_non_dict():
    # `score` exists but isn't a dict — `score.composite` must be None,
    # not crash. Guards against harness-output schema drift.
    assert run_trial._walk({"score": 0.5}, "score.composite") is None


# ---------------------------------------------------------------------------
# aggregate — median + stddev across sub-runs
# ---------------------------------------------------------------------------


def test_aggregate_single_run_has_zero_stddev():
    """One sub-run can't have a stddev; statistics.stdev requires n>=2.
    The test pins the fallback to 0.0 so determinism gates don't NaN."""
    runs = [{"composite": 0.872}]
    out = run_trial.aggregate(runs, ["composite"])
    assert out["median"]["composite"] == 0.872
    assert out["stddev"]["composite"] == 0.0


def test_aggregate_three_runs_computes_median_and_stddev():
    """The Phase 0g determinism gate: 3 runs, median + sample stddev.
    Sample stddev (n-1) so the gate is honest with small n."""
    runs = [{"composite": 0.870}, {"composite": 0.872}, {"composite": 0.874}]
    out = run_trial.aggregate(runs, ["composite"])
    assert out["median"]["composite"] == 0.872
    # sample stddev of [0.870, 0.872, 0.874] = 0.002
    assert abs(out["stddev"]["composite"] - 0.002) < 1e-9


def test_aggregate_skips_keys_not_present_in_any_run():
    """If a key never appears across any sub-run, it's silently
    omitted — better than crashing the trial loop on missing data."""
    runs = [{"composite": 0.5}, {"composite": 0.6}]
    out = run_trial.aggregate(runs, ["composite", "nonexistent"])
    assert "composite" in out["median"]
    assert "nonexistent" not in out["median"]


def test_aggregate_walks_nested_score_keys():
    """The harnesses emit results in different shapes; runs.jsonl's
    `score-keys` arg accepts dotted keys so callers can target either
    flat (`composite`) or nested (`by_category.single_hop`) values."""
    runs = [
        {"by_category": {"single_hop": 0.6}},
        {"by_category": {"single_hop": 0.7}},
    ]
    out = run_trial.aggregate(runs, ["by_category.single_hop"])
    assert abs(out["median"]["by_category.single_hop"] - 0.65) < 1e-9
