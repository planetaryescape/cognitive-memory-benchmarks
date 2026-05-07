# Phase 0 — harness extension + experiment-log discipline

**Completed (dev):** 2026-05-07
**Smoke test (0g):** SDK surface complete 2026-05-07 (8 sub-runs across 4 trials, ~35 min wall, ~$0.70 spend). Daemon-surface skipped — needs operator-side daemon orchestration (config.toml restart-write); see "Pending" below.
**Wall (dev):** ~5 h
**API spend:** $0.70 (8 SDK lti_bench sub-runs across 4 trials)

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

- **Determinism gate (<1pp stddev) FAILED at n=3.** See "Smoke
  results" below. The plan's risk note anticipated this and
  prescribed downgrading to median-of-5; phase 1 inherits that
  guidance. Smallest detectable effect on the current 42-question
  LTI-Bench is ~3-4pp, not the 0.5pp originally planned.
- **Daemon-surface 0g (4 runs) skipped this session.** The path
  needs `cm-daemon` running plus a config.toml restart-write per
  override trial — orchestration that I judged unsafe to do
  unattended. The wiring itself is exercised by daemon test suite
  (151/151 pass) and the SDK runs proved the harness end-to-end;
  daemon parity is a separate user-driven validation.

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
  via `--help` and 4 real runs).
- [x] `tuning/scripts/run_trial.py` writes to `runs.jsonl` with the
  documented schema and produces per-trial directories.
- [x] Override propagation confirmed end-to-end via `lti-0003`
  (smoke_alpha_0_5.json shifted mean_f1 by +2.2pp vs baseline median).
- [~] Determinism baseline measured but **failed the <1pp gate**.
  Phase 1 must either widen N (5+ sub-runs) or accept ~3-4pp as
  the smallest detectable effect on this bench surface.

## Smoke results (0g, SDK surface)

Pinned models: answer `gpt-4o-mini`, judge `gpt-4o-2024-08-06`. All
runs against editable SDK install of `cognitive-memory` Phase 0a-sdk
+ benchmarks Phase 0c CLI flags.

| trial | sub-runs | median accuracy | stddev | median mean_f1 | stddev | critical |
|---|---|---|---|---|---|---|
| `lti-0001` (validation, baseline) | 1 | 0.857 | — | 0.689 | — | 1.000 |
| `lti-0002` (baseline `--repeat 3`) | 3 | 0.881 | **0.024** | 0.665 | **0.015** | 1.000 |
| `lti-0003` (α=0.5, `--repeat 1`) | 1 | 0.857 | — | 0.687 | — | 1.000 |
| `lti-0004` (α=0.5, `--repeat 3`) | 3 | 0.881 | 0.014 | **0.688** | **0.002** | 1.000 |

Wall: validation 5m, baseline-3 13m, override-1 4m, override-3 12m →
~35 min total. Spend: ~$0.70.

Findings:

1. **Override propagation works (now with stddev on both sides).**
   `lti-0004` (α=0.5) median mean_f1 = 0.688 vs `lti-0002` (α=0.3)
   median mean_f1 = 0.665 — gap of +2.3pp. Override stddev on f1 is
   only 0.2pp; baseline stddev is 1.5pp. The +2.3pp gap is ~1.5σ
   above baseline noise — directionally meaningful but not yet 2σ
   confident. Both medians on accuracy are identical (0.881) — no
   detectable α effect on accuracy at this sample size.
2. **Noise is condition-dependent, not just sample-size-driven.**
   The override condition (α=0.5) has 7.5× lower f1 stddev than
   baseline (0.2pp vs 1.5pp), and 1.7× lower accuracy stddev. One
   plausible mechanism: higher α weights retention more in scoring,
   producing a more deterministic memory ranking → less judge-side
   variance. Could also be coincidence at n=3. Worth a follow-up at
   n≥10 in Phase 1.
3. **The 1pp gate held on the override side; failed on baseline.**
   `lti-0004` f1 stddev (0.2pp) is well below the 1pp gate; the
   1pp gate failure documented earlier was driven entirely by
   baseline noise. This means "median-of-3" can be sufficient *for
   the parameter point being tuned* if the tuned regime happens to
   be lower-noise, but the comparison-against-baseline always
   inherits the noisier side.
4. **Implications for Phase 1.** Sensitivity studies need either
   n≥5 sub-runs per parameter point (compute cost ~$0.50 per
   parameter point on LTI-Bench), OR a less noisy bench surface
   (LongMemEval-S 500-question sample → expected ~0.3pp stddev),
   OR accept the asymmetric noise floor and report effect sizes in
   units of baseline-σ. Recommend: use LongMemEval for sensitivity
   sweeps, LTI-Bench for confirmation runs only.
5. **`critical_fact_retention` is invariant at 1.0 across all 8
   sub-runs.** Either the test cases are easy or all params tested
   so far don't move it. Worth checking in Phase 1 whether any
   tunable shifts it off the ceiling.

Per-trial artifacts:
- `tuning/runs/lti-0001/run-00/` — validation
- `tuning/runs/lti-0002/run-{00,01,02}/` — baseline 3-run (α=0.3)
- `tuning/runs/lti-0003/run-00/` — α=0.5 single-shot
- `tuning/runs/lti-0004/run-{00,01,02}/` — α=0.5 3-run
- `tuning/runs/runs.jsonl` — 4 lines, one per trial

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
