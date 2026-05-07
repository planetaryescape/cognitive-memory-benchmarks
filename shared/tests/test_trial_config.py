"""Tests for `load_trial_config` — Phase 0c JSON schema.

A trial config feeds both `lti_bench.py --config X.json` and
`ablation_runner.py --config X.json`. Tests assert the schema's
contract: surface routing, adapter passthrough, config_overrides
merge, base_decay_rates hoist, defaults on missing/empty.
"""

import json
from pathlib import Path

import pytest

from shared.trial_config import load_trial_config


# ---------------------------------------------------------------------------
# Defaults / robustness
# ---------------------------------------------------------------------------


def test_load_none_returns_empty_dict():
    """`--config` not passed ⇒ no kwargs ⇒ adapter gets full defaults."""
    assert load_trial_config(None) == {}


def test_load_empty_file_returns_empty_dict(tmp_path):
    """Empty file (zero bytes) is the JSON equivalent of "no overrides"
    so harnesses don't have to special-case the empty-file path."""
    p = tmp_path / "empty.json"
    p.write_text("")
    assert load_trial_config(p) == {}


def test_load_empty_object_returns_empty_dict(tmp_path):
    """`{}` is valid JSON and means "all defaults". Equivalent to
    omitting the flag — used by the 0g determinism baseline check."""
    p = tmp_path / "empty.json"
    p.write_text("{}")
    assert load_trial_config(p) == {}


# ---------------------------------------------------------------------------
# Surface routing
# ---------------------------------------------------------------------------


def test_load_surface_field_passes_through(tmp_path):
    """`"surface": "daemon"` reaches adapter as `surface="daemon"`."""
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"surface": "daemon"}))
    out = load_trial_config(p)
    assert out["surface"] == "daemon"


def test_load_no_surface_omits_key(tmp_path):
    """No `surface` field ⇒ key absent in output ⇒ adapter falls back
    to its default surface ("sdk"). The harness shouldn't have to know
    the default."""
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"adapter": {"deep_recall": True}}))
    out = load_trial_config(p)
    assert "surface" not in out


# ---------------------------------------------------------------------------
# Adapter kwargs passthrough
# ---------------------------------------------------------------------------


def test_load_adapter_block_kwargs_pass_through(tmp_path):
    """The `adapter` block's keys land directly as adapter kwargs.
    Lets a trial flip retrieval-time settings (deep_recall, rerank,
    graph_hops) without entering CognitiveMemoryConfig."""
    p = tmp_path / "cfg.json"
    p.write_text(
        json.dumps(
            {
                "adapter": {
                    "deep_recall": True,
                    "rerank": False,
                    "graph_hops": 2,
                }
            }
        )
    )
    out = load_trial_config(p)
    assert out["deep_recall"] is True
    assert out["rerank"] is False
    assert out["graph_hops"] == 2


# ---------------------------------------------------------------------------
# config_overrides
# ---------------------------------------------------------------------------


def test_load_config_overrides_passes_through(tmp_path):
    """The `config_overrides` block is the primary tuning surface — it
    lands as adapter `config_overrides=...` so any
    `CognitiveMemoryConfig` field can be flipped."""
    p = tmp_path / "cfg.json"
    p.write_text(
        json.dumps(
            {"config_overrides": {"retrieval_score_exponent": 0.5}}
        )
    )
    out = load_trial_config(p)
    assert out["config_overrides"] == {"retrieval_score_exponent": 0.5}


def test_load_base_decay_rates_top_level_merges_into_config_overrides(tmp_path):
    """Phase-0a integration: hoisted `base_decay_rates` lands inside
    `config_overrides["base_decay_rates"]` so the SDK's per-category β
    field receives it."""
    p = tmp_path / "cfg.json"
    p.write_text(
        json.dumps(
            {"base_decay_rates": {"semantic": 60.0, "episodic": 30.0}}
        )
    )
    out = load_trial_config(p)
    assert out["config_overrides"]["base_decay_rates"] == {
        "semantic": 60.0,
        "episodic": 30.0,
    }


def test_load_top_level_base_decay_rates_wins_over_nested(tmp_path):
    """Documented precedence: top-level `base_decay_rates` overrides
    a same-named entry under `config_overrides`. The hoisted form is
    the documented user surface; nested duplicates lose. Catches a
    naive merge that would let stale nested values silently win."""
    p = tmp_path / "cfg.json"
    p.write_text(
        json.dumps(
            {
                "config_overrides": {
                    "base_decay_rates": {"semantic": 999.0},
                },
                "base_decay_rates": {"semantic": 60.0},
            }
        )
    )
    out = load_trial_config(p)
    assert out["config_overrides"]["base_decay_rates"] == {"semantic": 60.0}


def test_load_combines_all_blocks_into_one_kwargs_dict(tmp_path):
    """End-to-end: a config exercising every block produces the
    expected adapter-ready kwargs dict."""
    p = tmp_path / "cfg.json"
    p.write_text(
        json.dumps(
            {
                "surface": "sdk",
                "adapter": {"deep_recall": True},
                "config_overrides": {"retrieval_score_exponent": 0.42},
                "base_decay_rates": {"semantic": 60.0},
            }
        )
    )
    out = load_trial_config(p)
    assert out == {
        "surface": "sdk",
        "deep_recall": True,
        "config_overrides": {
            "retrieval_score_exponent": 0.42,
            "base_decay_rates": {"semantic": 60.0},
        },
    }


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_load_array_raises(tmp_path):
    """Top-level JSON must be an object, not an array."""
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ValueError, match="object"):
        load_trial_config(p)


def test_load_invalid_adapter_block_raises(tmp_path):
    """`adapter` must be an object, not a string."""
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"adapter": "wrong"}))
    with pytest.raises(ValueError, match="adapter"):
        load_trial_config(p)
