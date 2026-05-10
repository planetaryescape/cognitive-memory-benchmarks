# 2026-05 tuning campaign — end-to-end summary (Phase 0g → 7)

**Window:** 2026-05-07 → 2026-05-11 (4 days, mostly unattended compute)
**Total spend:** ~$285 OpenAI (Phase 0g→7 inclusive of the failed retries)
**Total compute wall:** ~32h spread across 4 days
**Commits:** 14 across `cognitive-memory-sdk` (1) + `cognitive-memory-daemon` (3) + `cognitive-memory-benchmarks` (10)
**Outcome:** **v0.5.0 SDK ship validated end-to-end on LoCoMo** (+1.87pp F1, +2.73pp LLM accuracy on 1540 questions)

This document is the single overview tying together the per-phase
milestone notes. Each phase has its own milestone with full
methodology + per-trial artifacts; this is the index + executive
summary.

## Goal

Replace [`cognitive-memory`](https://github.com/planetaryescape/cognitive-memory)'s
paper-faithful default config values with empirically-derived
defaults that improve real-benchmark performance, with full
provenance so the choices remain defensible months later.

## What shipped (v0.5.0)

Three default flips in `CognitiveMemoryConfig`:

| param | v0.4 (paper) | v0.5 (tuned) | source |
|---|---|---|---|
| `associative_boost` | 0.03 | **0.05** | Phase 1 OFAT |
| `base_decay_rates.semantic` | 120 days | **240 days** | Phase 1 OFAT |
| `core_session_threshold` | 3 | **2** | Phase 2 joint search |

Other Tier 1+2 parameters unchanged. The same three flips were
mirrored in `cognitive-memory-daemon`'s `LifecycleConfig::default()`
in v0.0.2.

## Validation chain (each phase has its own milestone)

| phase | bench | n trials / Q | spend | wall | finding |
|---|---|---|---|---|---|
| 0g | LTI-Bench (smoke) | 6 trials | $1.30 | 22min | harness validates; bimodal landscape |
| 1 | LTI-Bench OFAT | 47 × 3 sub-runs | $14 | 9.5h | assoc=0.03 worst; β_sem=240 max |
| 2 | LTI-Bench Optuna | 50 × 3 sub-runs | $15 | 12h | top-5 within noise; cst=3 trails 67% vs cst=1/2 ~92% |
| 2.5a | per-question variance | 305 result.json analysed | $0 | minutes | 3 of 42 LTI Q cause bimodality (weather, traffic, lunch) |
| 2.5b | top-K confirm @n=5 | 5 trials × 5 sub-runs | $2.50 | 2h | all ranks shuffle; trial closest to v0.5 defaults wins |
| 3 | LoCoMo conv0 cross-check | 5 trials × 1 conv | $2.50 | 56min | rank stability holds; no overfitting |
| 4 | LoCoMo conv0 head-to-head | 2 candidates × 1 conv | $10 | 75min | v0.5 +2.92pp F1 |
| **5** | **LoCoMo full** | **2 × 10 conv (1540 Q)** | **$100** | **3.4h** | **v0.5 +1.87pp F1, +2.73pp LLM acc** |
| 6 | SDK ship (no benchmark) | — | $0 | minutes | v0.5.0 published with 3 default flips + value-lock tests |
| 7 | LongMemEval-S | 2 × 500 Q (attempted) | $140 | failed at 30% twice | OpenAI billing cap blocked both attempts; partial inconclusive |

**Phase 5 is the load-bearing validation.** Phase 7 was meant as a
second-bench confirmation but hit the account billing cap twice;
partial data shows v0.4 marginally ahead on the categories it
sampled, but those categories don't include the ones where v0.5
should win (temporal-reasoning, knowledge-update, abstention).

## Methodology lessons (worth carrying forward)

1. **Small benches (LTI's 42 Q) hit a noise floor at ~3pp.** The
   variance is dominated by 3 specific marginal questions where
   the LLM judge flips between trials. Use small benches for
   confirmation, not sensitivity sweeps.
2. **Joint search surfaces interactions OFAT misses.** `cst=3`
   looked flat in Phase 1's one-factor-at-a-time sweep; Phase 2's
   joint search (3 dimensions varied together) surfaced its
   underperformance.
3. **n=3 sub-runs is the floor.** Phase 2.5b confirmed all 5 top
   ranks shuffle when re-run at n=5 — the n=3 ranking was lottery,
   not signal. Real verdicts need n≥5.
4. **The strongest finding (`assoc=0.05`) replicated at every
   level**: Phase 1 OFAT, Phase 2 joint search, Phase 2.5b
   confirmation, Phase 3 cross-distribution, Phase 5 full bench.
   That's why it was safe to ship.
5. **Real-time logging matters.** Chat-only progress reports aren't
   durable. The four-level provenance chain (per-trial JSON / runs.jsonl
   / experimentlog narrative / milestone notes) makes the campaign
   reconstructable. Captured as a memory rule mid-campaign after
   the user pushed on it twice.
6. **Account billing caps are a real failure mode.** Phase 7 burned
   $140 across two attempts hitting the same wall. For long
   unattended runs, verify both credit balance AND the separate
   monthly usage cap have headroom before launching.

## Provenance map

Repo: `cognitive-memory-benchmarks` (this one)

- **Narrative log** — `experimentlog_v2.md`. One dated entry per
  phase, refreshed in real-time during long sweeps.
- **Per-phase milestones** — `docs/milestones/phase-{0-harness-extension,
  1-sensitivity-analysis, 2-optuna-tuning, 4-locomo-reality-check,
  5-full-locomo, 7-longmemeval-validation}.md`.
- **Structured row log** — `tuning/runs/runs.jsonl`. Append-only;
  one line per trial (LTI sweeps).
- **Per-trial artifacts** — `tuning/runs/lti-NNNN/run-NN/result.json`
  for LTI-Bench trials; `tuning/runs/phase{4,5,7}/` for benchmark
  head-to-heads.
- **Phase 2 Optuna study** — `tuning/runs/phase2/lti-phase2.db`
  (SQLite, openable with optuna-dashboard).
- **Phase 2.5 analyses** — `tuning/runs/phase2.5/{question_variance,
  top_k_confirmation}.csv`.

Repo: `cognitive-memory-sdk`

- **CHANGELOG entry** — `sdks/python/CHANGELOG.md` v0.5.0 section
  with empirical evidence and migration notes.
- **Default values** — `sdks/python/src/cognitive_memory/types.py`
  with inline rationale comments per default flip.
- **Value-lock tests** — `sdks/python/tests/test_config.py`
  (3 new tests: `test_associative_boost_default_is_v0_5_tuned`,
  `test_core_session_threshold_default_is_v0_5_tuned`,
  `test_base_decay_rates_semantic_default_is_v0_5_tuned`).

Repo: `cognitive-memory-daemon`

- **Default values** — `crates/lifecycle/src/lib.rs`
  (`LifecycleConfig::default` + `default_base_decay_rates`).
  Bumped to v0.0.2.
- **Tests** — `crates/lifecycle/tests/parity.rs` +
  `crates/daemon/tests/e2e.rs` updated for v0.5 defaults.

## Cost ledger

| phase | spend | cumulative |
|---|---|---|
| Phase 0g | $1.30 | $1.30 |
| Phase 1 | $14 | $15.30 |
| Phase 2 | $15 | $30.30 |
| Phase 2.5b | $2.50 | $32.80 |
| Phase 3 | $2.50 | $35.30 |
| Phase 4 | $10 | $45.30 |
| Phase 5 | $100 | $145.30 |
| Phase 7 (failed × 2) | $140 | $285.30 |
| **Total** | **~$285** | |

Phase 0+1+2 ($30) plus Phase 4+5 validation ($110) = the
"successful" $140 spend. Phase 7's $140 was burned hitting the
account billing wall and produced no usable bench-level result;
salvageable as a methodology lesson (always pre-check billing cap).

## What we did NOT change

- **The algorithm itself.** Same paper model, just two β values
  tuned and one threshold lowered. No new features, no API
  changes.
- **Speed / memory.** Defaults don't move runtime characteristics.
- **The other 6 swept parameters** (`direct_boost`, α/`retrieval_score_exponent`,
  `power_decay_gamma`, `decay_model`, `core_access_threshold`,
  `core_stability_threshold`, `base_decay_rates.episodic`).
  Phase 1 found them either at-optimum or showing no signal.
- **Daemon `[lifecycle]` TOML override** continues to work the
  same way — operators can override the new defaults if they
  prefer paper-faithful values.

## Honest caveats

- **Phase 7 didn't complete.** LongMemEval-S validation is partial
  and inconclusive on the categories where v0.5 should win.
  Strictly speaking we have one (1) full real-benchmark validation
  (LoCoMo Phase 5), not two.
- **The +1.87pp lift is on LoCoMo's distribution.** Other
  workloads — particularly very-long-conversation or knowledge-
  update-heavy ones — may behave differently.
- **The campaign is single-author and single-account.** No
  independent replication.
- **The v0.4 baseline at Phase 4 was 0.431 F1** (vs v6 CR-A at
  0.470). Drift since the v6 baseline; doesn't affect the v0.4-vs-
  v0.5 delta but means absolute Phase 4/5 numbers differ from the
  v6 reference. Phase 5 v0.4 reproduces v6 within noise (0.444
  vs 0.448) — the conv0 drift was conv0-specific.
