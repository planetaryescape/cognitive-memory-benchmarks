from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import merge_trial_configs  # noqa: E402


def test_merge_configs_merges_nested_adapter_and_overrides(tmp_path):
    base = tmp_path / "base.json"
    ablation = tmp_path / "ablation.json"
    base.write_text(
        """
        {
          "surface": "sdk",
          "adapter": {"deep_recall": true, "graph_hops": 1},
          "config_overrides": {
            "direct_boost": 0.1,
            "base_decay_rates": {"semantic": 240.0},
            "decay_floors": {"core": 0.6}
          }
        }
        """
    )
    ablation.write_text(
        """
        {
          "adapter": {"graph_hops": 0},
          "config_overrides": {
            "direct_boost": 0.0,
            "base_decay_rates": {"episodic": 30.0},
            "decay_floors": {"regular": 0.0}
          }
        }
        """
    )

    merged = merge_trial_configs.merge_configs([base, ablation])

    assert merged["surface"] == "sdk"
    assert merged["adapter"] == {"deep_recall": True, "graph_hops": 0}
    assert merged["config_overrides"]["direct_boost"] == 0.0
    assert merged["config_overrides"]["base_decay_rates"] == {
        "semantic": 240.0,
        "episodic": 30.0,
    }
    assert merged["config_overrides"]["decay_floors"] == {
        "core": 0.6,
        "regular": 0.0,
    }
