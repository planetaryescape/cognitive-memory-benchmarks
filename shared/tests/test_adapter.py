"""Tests for CognitiveMemoryAdapter — Phase 0b additions.

Each test is one vertical slice. RED → 5-question gate → GREEN. See
`~/.claude/plans/now-create-a-plan-validated-yao.md` Stage 0b.

The adapter is the only injection point a tuning trial uses to flip
arbitrary `CognitiveMemoryConfig` fields per-run. Two surfaces:

- `surface="sdk"` (default, fast inner-loop): InMemoryAdapter
- `surface="daemon"` (reality-check): RemoteAdapter over Unix socket

Tests assert behavior through the public `__init__` surface — they do
not import internal helpers. Survive a full implementation rewrite.
"""

import pytest

from shared.adapter import CognitiveMemoryAdapter


# ---------------------------------------------------------------------------
# config_overrides
# ---------------------------------------------------------------------------


def test_adapter_no_overrides_preserves_default_config_kwargs():
    """Default construction (no `config_overrides`) keeps the adapter's
    historical defaults. Locks in what was shipping before Phase 0b so a
    silent regression in the merge logic is caught.

    The adapter's contract is: extraction_model='gpt-4o-mini',
    embedding_model='text-embedding-3-small', and the three lowered core
    promotion thresholds (3, 0.50, 2) for benchmark scenarios.
    """
    a = CognitiveMemoryAdapter(use_hash_embeddings=True)
    cfg = a.memory.config
    assert cfg.extraction_model == "gpt-4o-mini"
    assert cfg.embedding_model == "text-embedding-3-small"
    assert cfg.core_access_threshold == 3
    assert cfg.core_stability_threshold == 0.50
    assert cfg.core_session_threshold == 2
    assert cfg.run_maintenance_during_ingestion is False


def test_adapter_config_overrides_propagate_to_memory_config():
    """`config_overrides={"retrieval_score_exponent": 0.5}` reaches
    `memory.config.retrieval_score_exponent`. This is the primary
    Phase-0b contract: arbitrary fields settable per-trial without
    code edits."""
    a = CognitiveMemoryAdapter(
        use_hash_embeddings=True,
        config_overrides={"retrieval_score_exponent": 0.5, "direct_boost": 0.15},
    )
    cfg = a.memory.config
    assert cfg.retrieval_score_exponent == 0.5
    assert cfg.direct_boost == 0.15


def test_adapter_config_overrides_dont_clobber_baseline_kwargs():
    """An override on `retrieval_score_exponent` must not silently flip
    `core_access_threshold` (or any other field the override didn't
    name) — sibling fields keep their adapter defaults. Catches a
    naive `cfg = CognitiveMemoryConfig(**overrides)` bug."""
    a = CognitiveMemoryAdapter(
        use_hash_embeddings=True,
        config_overrides={"retrieval_score_exponent": 0.5},
    )
    cfg = a.memory.config
    assert cfg.core_access_threshold == 3  # adapter baseline
    assert cfg.extraction_model == "gpt-4o-mini"  # adapter baseline


def test_adapter_explicit_kwarg_beats_override_for_same_field():
    """When both `decay_model="power"` and
    `config_overrides={"decay_model": "exponential"}` are passed, the
    explicit kwarg wins. Documented precedence so trial configs can't
    silently subvert harness-level decisions."""
    a = CognitiveMemoryAdapter(
        use_hash_embeddings=True,
        decay_model="power",
        config_overrides={"decay_model": "exponential"},
    )
    assert a.memory.config.decay_model == "power"


def test_adapter_config_overrides_can_set_base_decay_rates():
    """The headline Phase-0a integration: `base_decay_rates` is now a
    config field, so the adapter can flip per-category β via override."""
    from cognitive_memory.types import MemoryCategory

    a = CognitiveMemoryAdapter(
        use_hash_embeddings=True,
        config_overrides={"base_decay_rates": {"semantic": 60.0}},
    )
    cfg = a.memory.config
    assert cfg.base_decay_rates[MemoryCategory.SEMANTIC] == 60.0
    # Sibling categories keep paper defaults (Table 2).
    assert cfg.base_decay_rates[MemoryCategory.EPISODIC] == 45.0


# ---------------------------------------------------------------------------
# surface routing
# ---------------------------------------------------------------------------


def test_adapter_default_surface_is_sdk():
    """The default surface is "sdk" — fast in-process InMemoryAdapter.
    Daemon path is opt-in. Confirms by inspecting the adapter type
    attached to the underlying memory."""
    from cognitive_memory.adapters.memory import InMemoryAdapter

    a = CognitiveMemoryAdapter(use_hash_embeddings=True)
    assert isinstance(a.memory.adapter, InMemoryAdapter)


def test_adapter_surface_daemon_uses_remote_adapter():
    """`surface="daemon"` constructs SyncCognitiveMemory with a
    RemoteAdapter so trials can reality-check against the shipping
    daemon. No daemon needs to be running for construction — the
    RemoteAdapter only opens its socket connection on first call.
    """
    from cognitive_memory.adapters.remote import RemoteAdapter

    a = CognitiveMemoryAdapter(
        use_hash_embeddings=True,
        surface="daemon",
        user_id="phase0-smoke-trial-001",
    )
    assert isinstance(a.memory.adapter, RemoteAdapter)


def test_adapter_unknown_surface_raises_value_error():
    """Typo in surface name should fail loudly at construction, not
    silently fall through to a default."""
    with pytest.raises(ValueError, match="surface"):
        CognitiveMemoryAdapter(use_hash_embeddings=True, surface="memory")
