# Phase 0 — harness extension + experiment-log discipline

**Completed (dev):** 2026-05-07
**Smoke test (0g):** pending user run (~50 min wall, ~$1 API)
**Wall (dev):** ~5 h
**API spend:** $0 (no LLM calls in 0a-0f)

## Goal

Unblock phases 1-5 of `docs/parameter-tuning-plan.md` by:

1. Making every tunable `CognitiveMemoryConfig` field settable per-run
   without code edits — including `base_decay_rates`, which was a
   module constant before this phase.
2. Establishing a four-level provenance chain (per-trial artifacts /
   `runs.jsonl` / experimentlog narrative / phase-end milestone) so a
   tuning conclusion eight months from now can be reconstructed.
3. Mirroring the SDK changes in the daemon (Rust) so the same JSON
   trial config can drive either surface (in-process SDK or shipping
   IPC daemon).

## What worked

- **Vertical TDD on each slice.** Each per-category β override surface
  (SDK config field, daemon config field, TOML parse, adapter kwarg,
  CLI flag) got its own RED-GREEN cycle with the 5-question quality
  gate. No batched implementation. Caught two real bugs early:
  - String-key check in `test_config_base_decay_rates_string_keys_are_coerced`
    initially passed against `MemoryCategory(str, Enum)` because the
    enum's str-subclass behaviour made `"semantic" in {ENUM: ...}` true;
    fixed by asserting key types instead.
  - Engine's `compute_retention` was still reading
    `memory.base_decay_rate` (module-constant property) after the
    config field was added — caught by parity test, fixed at line 93.
- **Cleanly-cut deprecation of the const fn.** The Rust side's
  `base_decay_rate_for_category(&str) -> f64` free function stays in
  place for back-compat but is no longer called from inside the daemon
  — searcher and handlers all route through `cfg.beta_for(...)`.
- **Load → mutate → save in CLI's `set-llm`.** The previous
  `DaemonConfig { llm: ... }` literal would have clobbered any
  operator-edited `[lifecycle]` on the next `cm config set-llm`.
  Switched the CLI to read the existing file before writing.
- **Statistical determinism gate.** Downgrading from "SHA equality
  across 3 baseline runs" to "median of 3, stddev < 1pp on composite"
  is honest about LLM-judge noise and gives a usable signal-to-noise
  ratio for phase 1 sensitivity sweeps.

## What didn't (yet)

- **0g smoke test not yet run.** ~50 min wall + $1 API; gated on
  user invocation. The harness is ready: `tuning/scripts/run_trial.py`
  produces the expected `runs.jsonl` row schema, the spaces files
  exist, both `lti_bench.py` and `ablation_runner.py` accept
  `--config` and `--surface`. Need to run the determinism baseline
  to know the actual stddev floor before phase 1 begins.

## Falsified hypotheses

- _"`Memory.base_decay_rate` has many readers; refactor will be wide."_
  Exhaustive grep showed exactly one site (`engine.py:93`). The change
  was a single-line replacement.
- _"Threading `LifecycleConfig` through the search path will require
  signature changes everywhere."_ The cleanest fix was a `Searcher`
  field + `with_lifecycle(store, cfg)` builder; existing
  `Searcher::new(store)` callers (9 in tests) needed no edits.

## Phase 1 preconditions met

- [x] All Tier 1+2 params overridable via JSON (any
  `CognitiveMemoryConfig` field via `config_overrides`).
- [x] `base_decay_rates` plumbed through SDK config and daemon config.
- [x] Per-trial JSON config schema documented and tested
  (`shared/trial_config.py` + 12 tests).
- [x] Adapter accepts `config_overrides` + `surface` kwargs (8 tests).
- [x] Both harnesses accept `--config` + `--surface` (smoke-validated
  via `--help`).
- [x] `tuning/scripts/run_trial.py` writes to `runs.jsonl` with the
  documented schema and produces per-trial directories.
- [ ] Determinism baseline confirmed (≥3 baseline runs, stddev < 1pp
  on composite). **Pending 0g.**

## Test counts

- SDK: 66/66 pass (5 new on `base_decay_rates`).
- Daemon: 151/151 pass workspace-wide (was 143 — 8 new across
  lifecycle parity + core config TOML parse).
- Benchmarks: 20/20 pass on `shared/tests/` (8 adapter + 12
  trial_config).

## Links

- Smoke test trials: _pending; will populate at
  `tuning/runs/lti-NNNN/` after 0g is run._
- experimentlog_v2.md: `2026-05-07 — Phase 0: Tuning harness extension`.
- Plan file: `~/.claude/plans/now-create-a-plan-validated-yao.md`.
- Parent plan: `docs/parameter-tuning-plan.md`.
- Tuning README: `tuning/README.md`.

## Files changed (phase 0)

### cognitive-memory-sdk

- `sdks/python/src/cognitive_memory/types.py` — `base_decay_rates`
  field + `__post_init__` coercion.
- `sdks/python/src/cognitive_memory/engine.py:93` — read β from config.
- `sdks/python/tests/test_config.py` — 5 new tests.

### cognitive-memory-daemon

- `crates/lifecycle/src/lib.rs` — `LifecycleConfig.base_decay_rates`
  HashMap + `beta_for(&str)` method.
- `crates/lifecycle/tests/parity.rs` — 4 new tests.
- `crates/daemon/src/handlers.rs` — `AppState.lifecycle` field;
  `compute_current_retention` takes `&LifecycleConfig`;
  `memory_row_to_data` takes `&LifecycleConfig`; 4 callers updated.
- `crates/daemon/src/server.rs` — `Daemon::new_full` constructor.
- `crates/daemon/src/main.rs` — `build_lifecycle_config()` merges
  TOML overrides at startup.
- `crates/daemon/src/lib.rs` — re-exports
  `paper_faithful_lifecycle_config`, `LifecycleOverrides`.
- `crates/search/src/searcher.rs` — `Searcher.life_cfg` field,
  `Searcher::with_lifecycle(store, cfg)` builder; both lookup sites
  use `cfg.beta_for(...)`.
- `crates/core/src/config.rs` — `LifecycleOverrides` struct;
  `DaemonConfig.lifecycle: Option<LifecycleOverrides>`; 4 new tests.
- `crates/core/Cargo.toml` — `tempfile` dev-dep for roundtrip test.
- `crates/cli/src/main.rs` — `set-llm` now load → mutate → save.

### cognitive-memory-benchmarks

- `shared/adapter.py` — `CognitiveMemoryAdapter.__init__` gained
  `config_overrides`, `surface`, `user_id` kwargs.
- `shared/trial_config.py` — new loader for trial JSON configs.
- `shared/tests/test_adapter.py` — 8 new tests.
- `shared/tests/test_trial_config.py` — 12 new tests.
- `lti/lti_bench.py` — `--config` + `--surface` flags.
- `analysis/ablation_runner.py` — same.
- `tuning/scripts/run_trial.py` — wrapper for one-shot trials.
- `tuning/spaces/baseline.json`, `tuning/spaces/smoke_alpha_0_5.json`
  — Phase 0g smoke configs.
- `tuning/README.md` — full docs.
- `experimentlog_v2.md` — Phase 0 narrative entry appended.
- `docs/milestones/phase-0-harness-extension.md` — this file.
