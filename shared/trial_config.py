"""Load + normalize a tuning-trial JSON config into adapter kwargs.

A trial config is the single source of truth for one parameter-tuning
experiment. Both `lti_bench.py` and `ablation_runner.py` consume it via
`--config FILE`. The JSON schema (Phase 0c, see
`~/.claude/plans/now-create-a-plan-validated-yao.md`):

    {
      "surface": "sdk" | "daemon",
      "adapter": {
        "deep_recall": true,
        "rerank": false,
        "dual_perspective": true,
        "graph_hops": 1
      },
      "config_overrides": {
        "retrieval_score_exponent": 0.5,
        "direct_boost": 0.15,
        "decay_model": "power"
      },
      "base_decay_rates": {
        "semantic": 60,
        "episodic": 30
      }
    }

`surface` is top-level so it can drive harness routing without entering
the `CognitiveMemoryConfig` constructor. `base_decay_rates` is hoisted
top-level so a tuning loop can flip β_c without nesting under
`config_overrides` — the loader merges it into `config_overrides` here.

Empty/missing file ⇒ empty trial config (adapter gets all defaults).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_trial_config(path: str | Path | None) -> dict[str, Any]:
    """Read a trial JSON config and return adapter-ready kwargs.

    Returns a dict with keys subset of:
      - `surface`: "sdk" | "daemon"
      - `config_overrides`: dict for `CognitiveMemoryConfig` fields
      - plus any keys under `adapter`: forwarded to the adapter
        constructor (e.g. `deep_recall`, `rerank`, `graph_hops`).

    `path is None` or empty file or `{}` ⇒ empty dict (adapter defaults).
    """
    if path is None:
        return {}
    raw = Path(path).read_text().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(
            f"trial config at {path} must be a JSON object, got {type(data).__name__}"
        )

    out: dict[str, Any] = {}

    # Surface routing: opt-in, defaulted by the adapter.
    surface = data.get("surface")
    if surface is not None:
        out["surface"] = surface

    # Adapter-level kwargs are forwarded verbatim. `dual_perspective`,
    # `deep_recall`, `rerank`, `graph_hops`, `decay_model`, etc. — these
    # are existing `CognitiveMemoryAdapter.__init__` kwargs.
    adapter_kwargs = data.get("adapter") or {}
    if not isinstance(adapter_kwargs, dict):
        raise ValueError(
            f"trial config 'adapter' must be an object, got {type(adapter_kwargs).__name__}"
        )
    out.update(adapter_kwargs)

    # Build `config_overrides` from two sources: the explicit
    # `config_overrides` block (free-form CognitiveMemoryConfig fields)
    # plus the hoisted `base_decay_rates` shorthand. They merge into one
    # dict that the adapter splats into the config constructor.
    config_overrides: dict[str, Any] = dict(data.get("config_overrides") or {})
    if not isinstance(config_overrides, dict):
        raise ValueError(
            f"trial config 'config_overrides' must be an object, got "
            f"{type(config_overrides).__name__}"
        )

    base_decay_rates = data.get("base_decay_rates")
    if base_decay_rates is not None:
        if not isinstance(base_decay_rates, dict):
            raise ValueError(
                f"trial config 'base_decay_rates' must be an object, got "
                f"{type(base_decay_rates).__name__}"
            )
        # Merge atop any base_decay_rates already inside config_overrides.
        # Top-level wins because the hoisted form is the documented user
        # surface; nesting it under config_overrides is for completeness.
        merged = dict(config_overrides.get("base_decay_rates") or {})
        merged.update(base_decay_rates)
        config_overrides["base_decay_rates"] = merged

    if config_overrides:
        out["config_overrides"] = config_overrides

    return out
