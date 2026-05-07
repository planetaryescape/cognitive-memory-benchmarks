# Cognitive Memory v6 — Remaining Work for arXiv

> Historical May 5 status snapshot. The canonical run registry is `experimentlog.md`; use this file only for provenance unless a result is explicitly cross-checked there.

## Current SDK Full Rerun Refresh — 2026-05-05

Status: **COMPLETE**. Active paper numbers now come from fresh artifacts in the `current_sdk_20260505` namespace and matching entries in `experimentlog.md`.

| Field | Value |
|-------|-------|
| Started | 2026-05-05T19:08:42Z / 2026-05-05 20:08:42 BST |
| SDK | editable `../cognitive-memory-sdk/sdks/python`, package `0.3.0`, git `905aba7`, dirty worktree |
| Benchmarks | git `d6c28c1`, dirty worktree |
| Required reruns | LoCoMo 10 conv / 1540 QA; LongMemEval-S 500 Q; LTI-Bench v2 42 probes; oracle, decay, evidence recall, efficiency, feature activation, judge reliability |
| Output namespace | `current_sdk_20260505` |
| Rule | No manuscript number is valid unless logged and backed by an artifact in that namespace |

Run checklist:
- CR-A LoCoMo primary: complete at 2026-05-05T20:51:00Z, merged artifact `locomo/results/current_sdk_20260505/primary_merged.json`; headline F1 `44.8%`, multi-hop `48.5%`, judge accuracy `58.4%`
- CR-B LongMemEval-S: complete at 2026-05-07T06:36:53Z, `longmemeval/results/current_sdk_20260505/primary.json`; task-averaged accuracy `71.6%`, overall accuracy `72.6%`
- CR-C LTI-Bench v2: complete at 2026-05-05T20:57:11Z, `lti/results/current_sdk_20260505/run_l_v2.json`; accuracy `88.1%`, F1 `69.7%`, critical retention `100%`
- CR-D/CR-I derived analyses: CR-D oracle ceiling complete at 2026-05-06T13:00:00Z (`63.9%` LoCoMo / `61.1%` Mem0 scoring); CR-F/G/H local post-processing complete; CR-I judge reliability complete; CR-E decay complete; CR-J ablations complete

Prep notes:
- Derived LoCoMo analysis scripts now accept current result/output paths.
- LongMemEval thread-safety search monkey patch now matches current adapter filters.
- Paper, benchmark docs, and public docs were refreshed after completed `current_sdk_20260505` artifacts.
- CR-A progress check at 2026-05-05T19:31:57Z / 2026-05-05 20:31:57 BST: all ten shards running, in embedding/query traffic, with no obvious failure signatures and no completed JSON outputs yet.
- CR-A progress check at 2026-05-05T19:47:55Z / 2026-05-05 20:47:55 BST: all ten shards still running; no completed JSON outputs yet; latest logs show successful OpenAI embedding/chat-completion calls and increasing request counts.
- CR-A partial completion at 2026-05-05T19:58:40Z / 2026-05-05 20:58:40 BST: `conv1.json` completed cleanly (`105` total QA, `81` category 1-4 QA, F1 `0.498319`, judge accuracy `0.580247`); nine shards still running.
- CR-A partial completion at 2026-05-05T20:19:46Z / 2026-05-05 21:19:46 BST: `conv5.json` completed cleanly (`158` total QA, `123` category 1-4 QA, F1 `0.480845`, judge accuracy `0.617886`); eight shards still running.
- CR-A partial completion at 2026-05-05T20:25:14Z / 2026-05-05 21:25:14 BST: `conv6.json` completed cleanly (`190` total QA, `150` category 1-4 QA, F1 `0.459934`, judge accuracy `0.520000`); seven shards still running.
- CR-A partial completion at 2026-05-05T20:30:46Z / 2026-05-05 21:30:46 BST: `conv0.json`, `conv2.json`, and `conv8.json` completed cleanly; six shards complete, four still running.
- CR-A partial completion at 2026-05-05T20:36:19Z / 2026-05-05 21:36:19 BST: `conv9.json` completed cleanly (`204` total QA, `158` category 1-4 QA, F1 `0.478623`, judge accuracy `0.645570`); seven shards complete, three still running.
- CR-A partial completion at 2026-05-05T20:41:52Z / 2026-05-05 21:41:52 BST: `conv4.json` completed cleanly (`242` total QA, `178` category 1-4 QA, F1 `0.439514`, judge accuracy `0.539326`); eight shards complete, two still running.
- CR-A partial completion at 2026-05-05T20:47:21Z / 2026-05-05 21:47:21 BST: `conv7.json` completed cleanly (`239` total QA, `191` category 1-4 QA, F1 `0.381271`, judge accuracy `0.539267`); nine shards complete, one still running.
- CR-A complete at 2026-05-05T20:51:00Z / 2026-05-05 21:51:00 BST: all ten shards exited cleanly; merged artifact `locomo/results/current_sdk_20260505/primary_merged.json`; `1540` standard category 1-4 QA; overall F1 `44.8%`, multi-hop F1 `48.5%`, judge accuracy `58.4%`.
- CR-F/G/H started at 2026-05-05T20:51:50Z / 2026-05-05 21:51:50 BST from CR-A artifacts; local post-processing, no new API calls expected.
- CR-F/G/H complete at 2026-05-05T20:52:23Z / 2026-05-05 21:52:23 BST: evidence R@60 `35.6%`; vector search mean `53.87ms`; mean candidates `540`, mean retrieved `60`.
- CR-C/CR-I started at 2026-05-05T20:53:09Z / 2026-05-05 21:53:09 BST; bounded API runs for LTI-Bench and judge reliability.
- CR-I complete at 2026-05-05T20:54:36Z / 2026-05-05 21:54:36 BST: raw agreement `94.0%`, Cohen's kappa `0.879`, disagreements `3/50`.
- CR-C complete at 2026-05-05T20:57:11Z / 2026-05-05 21:57:11 BST: LTI-Bench accuracy `88.1%`, F1 `69.7%`, critical retention `100%`, core memories `66/85`.
- CR-E/CR-J started at 2026-05-05T20:57:49Z / 2026-05-05 21:57:49 BST for decay comparison and conv0 feature ablations.
- CR-E complete at 2026-05-05T21:13:35Z / 2026-05-05 22:13:35 BST: power-law `29.5%` vs exponential `25.0%`, delta `+4.6pp`.
- CR-J failed at 2026-05-05T21:13:35Z / 2026-05-05 22:13:35 BST before artifact: `KeyError: 'answer'` on LoCoMo category-5 item; not usable, patch/rerun required.
- CR-J harness fix at 2026-05-05T21:14:07Z / 2026-05-05 22:14:07 BST: answer/adversarial-answer fallback added; `py_compile` passed.
- CR-J rerun started at 2026-05-05T21:14:30Z / 2026-05-05 22:14:30 BST.
- CR-J progress at 2026-05-05T22:00:54Z / 2026-05-05 23:00:54 BST: rerun still healthy with successful chat/embedding calls; no artifact yet because the ablation runner writes output only after all H-K condition pairs complete.
- CR-J progress at 2026-05-05T22:24:42Z / 2026-05-05 23:24:42 BST: rerun still active and healthy after ~70 minutes elapsed; at least one condition pass completed and another session replay began; no artifact yet.
- CR-J progress at 2026-05-05T22:40:18Z / 2026-05-05 23:40:18 BST: rerun still active after ~85 minutes elapsed, mostly model-call wait time; no errors and no artifact yet.
- CR-J complete at 2026-05-05T23:50:20Z / 2026-05-06 00:50:20 BST: `analysis/results/current_sdk_20260505/ablation_results.json`; hybrid search `+1.7pp`, graph expansion `+0.0pp`, rerank `+1.9pp`, power decay `+3.2pp`.
- CR-B and CR-D started at 2026-05-06T11:37:11Z / 2026-05-06 12:37:11 BST: current-refresh LongMemEval-S and oracle ceiling artifacts are now running before final paper/docs updates.
- CR-D complete at 2026-05-06T13:00:00Z / 2026-05-06 14:00:00 BST: oracle ceiling artifact `locomo/results/current_sdk_20260505/oracle_ceiling_mem0.json`; LoCoMo F1 `63.9%`, Mem0 scoring F1 `61.1%`, evidence-only F1 `64.1%`.
- CR-B progress at 2026-05-06T13:22:36Z / 2026-05-06 14:22:36 BST: process still alive; partial artifact has `40` completed `per_question` entries and no final aggregate; not usable for paper numbers.
- CR-B stopped at 2026-05-06T15:57:14Z / 2026-05-06 16:57:14 BST with `80/500` completed and no final aggregate. A resume smoke test exposed a missing `user_id` parameter in the LongMemEval thread-safety monkey patch; patched and `py_compile` passed. CR-B resumed at 2026-05-06T16:04:44Z / 2026-05-06 17:04:44 BST from `--start-from 80` in tmux session `lme-current-refresh`.
- CR-B complete at 2026-05-07T06:36:53Z / 2026-05-07 07:36:53 BST: `500` questions; task-averaged accuracy `71.6%`; overall accuracy `72.6%`; abstention accuracy `90.0%`. Per-type accuracy: single-session-user `85.7%`, single-session-assistant `76.8%`, single-session-preference `46.7%`, multi-session `69.9%`, temporal-reasoning `64.7%`, knowledge-update `85.9%`.
- Ablation prep at 2026-05-05T19:39:19Z / 2026-05-05 20:39:19 BST: `analysis/ablation_runner.py` now passes condition overrides into `CognitiveMemoryAdapter`; `py_compile` passed.

## Completed Runs

| Run | Result | Notes |
|-----|--------|-------|
| A — LoCoMo Primary | F1=45.6%, multi-hop=48.9% | 10 convs, 1540 QA, deferred conflicts |
| CR-B — LongMemEval-S | Task-avg 71.6%, overall 72.6% | Complete current-refresh artifact; effectively tied with ENGRAM (71.4%) |
| C — Decay Comparison | Power-law +3.6% F1 | Conv 0 only, exp vs power |
| D — Evidence Recall@k | R@60=36.3% | R@5=24.9%, R@10=28.6%, R@20=31.8%, n=1535 |
| F — Efficiency Table | Extraction 14.1s, VecSearch 54ms | Mean/p50/p95 timing per stage |
| G — Utilization Probe | 540 candidates/query avg | 60 retrieved, all 10 convs |
| H-K — Ablations | rerank +1.8pp, power +3.6pp | hybrid -1.1pp, graph +0.6pp |
| E — Oracle Ceiling | F1=63.9% (Mem0 prompt re-run) | Re-run with Mem0 prompt: F1=63.9% (LoCoMo), 61.0% (Mem0) |
| L — LTI-Bench (v2) | Overall 90.5% acc, F1 70.1%, critical retention 100%, 67/85 core | SDK v0.3.0; n=42; time-stepped + llm_judge; associative is weak spot (60%) |

---

## Remaining Work Checklist

### 1. Run D — Evidence Recall@k ✅ COMPLETE

**Type**: Post-processing (no new API calls needed)

**Method**: For each LoCoMo QA with evidence annotations (99.7% coverage, 1536/1540), check if the evidence dialog IDs appear in the top-k retrieved memory contents at k=5, 10, 20, 60.

**Evidence format**: `["D1:3", "D1:12"]` — dialog turn IDs within sessions. Need to map these to session turn text and check if retrieved memories contain the relevant information.

**Data available**: `locomo/results/v6/parallel/conv{0-9}.json` — each per_question entry has `retrieved_contents` (list of 60 memory strings). Source data has `evidence` field per QA.

**Challenge**: Evidence IDs reference raw dialog turns (e.g., `D1:3` = session 1, turn 3). Retrieved memories are extracted facts, not raw turns. Need fuzzy matching — check if the *information* from the evidence turn appears in any retrieved memory, not exact string match.

**Paper output**: One table (Recall@5/10/20/60) + 1-2 sentences.

**Effort**: ~2h scripting + analysis.

---

### 2. Run F — Efficiency Table ✅ COMPLETE

**Type**: Post-processing (no new API calls needed)

**Data available**: Each per_question entry has `trace` with:
- `total_wall_ms` (retrieval only, mean ~63ms for conv 0)
- `stages.vector_search.wall_ms` + `candidate_count`
- `stages.scoring.wall_ms` + `candidate_count`
- No rerank stage in trace (rerank happens in adapter, not SDK engine)
- No token counts in trace (`total_tokens: 0`)

**Missing data**:
- Rerank tokens/wall time (not captured in trace — happens in adapter layer)
- Answer generation tokens/wall time (not captured — happens in locomo_eval.py)
- Extraction tokens/wall time (logged to stderr, not in JSON)

**Options**:
1. **Parse stderr logs** for extraction/rerank timing (already logged with timestamps)
2. **Re-instrument adapter** to capture rerank token usage into trace
3. **Report what we have** — retrieval-only timing is the SDK's responsibility. Rerank/answer are deployment-dependent.

**Paper output**: Table with retrieval wall_ms (mean/p50/p95), candidate counts, and note that rerank/answer costs are deployment-dependent.

**Effort**: ~1h if using existing data, ~3h if re-instrumenting.

---

### 3. Run G — Utilization Probe ✅ COMPLETE

**Current definition in experiment log**: Feature activation analysis (graph expansion, bridge paths, validity filtering). This is useful but isn't a "utilization probe."

**Real utilization probe** (as described): Hold retrieval constant, vary prompt, measure delta. Tests whether the model actually *uses* the retrieved context.

**Proposed approach**:
1. Take saved `retrieved_contents` from Run A (already in JSON)
2. Re-generate answers with a constrained prompt: "Answer ONLY from the memories below. If the answer is not in the memories, say 'I don't know'."
3. Compare F1 delta with Run A's unconstrained prompt
4. Delta measures utilization sensitivity

**Paper output**: 1 table (Prompt A vs Prompt B F1/judge), 1 paragraph interpretation.

**Effort**: ~2h (new answer generation pass, ~1540 API calls).

**Alternative**: Skip this entirely. Feature activation analysis (how often graph expansion / validity filtering / bridge paths fire) is already interesting for the paper and doesn't require re-running. Call it "Feature Activation Analysis" not "Utilization Probe."

---

### 4. Runs H-K — Ablation Studies (conv 0 only) ✅ COMPLETE

**Type**: New runs (API calls needed)

| Run | Variable | Condition A | Condition B |
|-----|----------|-------------|-------------|
| H | hybrid_search | False (default) | True |
| I | graph_expansion_hops | 0 | 1 (default) |
| J | rerank | off | on (already in Run A conv0) |
| K | decay_model | exponential | power (already in Run C) |

**Run J note**: Run A conv0 already has rerank=on. Need rerank=off condition only.
**Run K note**: Run C already has both conditions on conv0. Can reuse.

**Needed**: H (2 conditions), I (1 condition — Run A conv0 = hops=1), J (1 condition — rerank off).

**Total new runs**: 4 single-conversation runs. Can parallelize.

**Paper output**: Ablation table showing delta per feature.

**Effort**: ~2h wall time (4 parallel conv0 runs).

---

### 5. Run M — Judge Reliability ✅ COMPLETE

**Method**: Sampled 50 QA pairs stratified by category × correctness. Re-judged with alternative prompt (EQUIVALENT/DIFFERENT). Computed inter-judge agreement.

**Results**: κ=0.919, 96% raw agreement, 2 disagreements (both single-hop). Output: `locomo/results/v6/judge_reliability.json`

---

### 6. Oracle Ceiling Reconciliation ✅ COMPLETE

**Problem**: Run E (oracle ceiling) used a different prompt and `max_tokens=100`. Run A (mem0 mode) uses the Mem0 7-step CoT prompt with no max_tokens limit. These aren't comparable as "ceiling vs actual."

**Resolution**: Re-ran with Mem0 prompt. F1=63.9% (LoCoMo), 61.0% (Mem0). Per-cat: single-hop 53.4%, multi-hop 65.9%, temporal 35.5%, open-domain 70.0%.

---

## Priority Order

| Priority | Task | Blocks Paper? | Status |
|:--------:|------|:-------------:|--------|
| 1 | H-K Ablations | Yes (ablation table) | ✅ COMPLETE |
| 2 | D Evidence Recall@k | Yes (retrieval quality) | ✅ COMPLETE |
| 3 | Oracle re-run (option 1) | Yes (ceiling comparison) | ✅ COMPLETE |
| 4 | F Efficiency table | Nice-to-have | ✅ COMPLETE |
| 5 | G Feature activation | Nice-to-have | ✅ COMPLETE |
| 6 | M Judge reliability | Nice-to-have | ✅ COMPLETE |

**Remaining**: None — all runs complete. Run L done 2026-05-05 (see experimentlog.md for details and scoring caveats).

---

## Data Inventory

| File | Contents | Status |
|------|----------|--------|
| `locomo/results/v6/parallel/conv{0-9}.json` | Run A full results (per_question + aggregate) | Complete |
| `locomo/results/v6/oracle_ceiling.json` | Run E oracle results | Complete (wrong prompt) |
| `locomo/results/v6/parallel/conv{0-9}.log` | Run A stderr logs (extraction/rerank timing) | Complete |
| `longmemeval/results/current_sdk_20260505/primary.json` | CR-B LongMemEval-S results | Complete |
| `simulations/results/decay_comparison.json` | Run C results | Complete |
| `locomo/data/locomo10.json` | Source data with evidence annotations | Available |

---

## 2026-05-07 — Phase 0: Tuning harness extension

**Status:** complete (smoke test 0g pending user run)

Extends the benchmark adapter to accept arbitrary `CognitiveMemoryConfig`
overrides per-trial so phases 1-5 of `docs/parameter-tuning-plan.md`
can run without code edits. Plumbs `base_decay_rates` (per-category β_c)
through the SDK config field and mirrors it as a `[lifecycle]` section
in the daemon's config.toml so the same JSON trial config can drive
either surface.

### Decisions

- **`base_decay_rates` as a `CognitiveMemoryConfig` field, not a module
  constant.** SDK-side: added `base_decay_rates: dict` to the
  dataclass with `BASE_DECAY_RATES` (paper Table 2) as default and
  `__post_init__` coercing string keys (for JSON-loaded configs).
  `engine.py` reads from `config.base_decay_rates` instead of the
  module constant. The module constant remains as the source of
  defaults so existing imports work.
- **Daemon-side parity now, not Phase 6.** Per user direction, mirrored
  the same surface in `LifecycleConfig.base_decay_rates` (HashMap) +
  `cfg.beta_for(category)` lookup method. `[lifecycle.base_decay_rates]`
  parses from `~/.config/cognitive-memory/config.toml` and merges atop
  `paper_faithful_lifecycle_config()` at daemon startup. Threaded
  through `AppState.lifecycle`, `Searcher::with_lifecycle`, and the
  4 callers of `compute_current_retention` in handlers.rs.
- **Dual-surface harness (sdk + daemon).** `CognitiveMemoryAdapter`
  gained `surface: str = "sdk"` kwarg. `surface="daemon"` constructs
  `RemoteAdapter(user_id=...)` and passes to `SyncCognitiveMemory`.
  Per-phase routing: phases 1-2 (sensitivity, Optuna inner loop) run
  on `sdk` for speed; phase 3 cross-checks both; phases 4-5 run on
  `daemon` for reality check.
- **Statistical determinism gate, not SHA equality.** Per user
  direction: `--repeat 3`, median + sample stddev across sub-runs,
  pass if stddev < 1pp on composite. SHA equality with LLM judges
  was never going to hold; documenting the noise floor is the
  honest version.

### Tests

- SDK: `cognitive-memory-sdk/sdks/python/tests/test_config.py` — 5
  tests on `base_decay_rates` field + engine integration. All 66 SDK
  tests pass.
- Daemon: `crates/lifecycle/tests/parity.rs` — 4 new tests on
  `LifecycleConfig.base_decay_rates` + `beta_for(...)`.
  `crates/core/src/config.rs` — 4 new tests on `[lifecycle]` TOML
  parse + roundtrip. Total 151/151 workspace tests pass (was 143).
- Benchmarks: `shared/tests/test_adapter.py` — 8 tests on
  `config_overrides` + `surface` kwargs.
  `shared/tests/test_trial_config.py` — 12 tests on JSON schema.
  All 20/20 pass.

### Pending (user-triggered)

- **0g smoke test.** 10 runs across both surfaces (~50 min wall, ~$1).
  Three baseline + one override per surface + two ablation_runner.
  Determinism gate stddev < 1pp on composite. The harness is ready;
  the `python tuning/scripts/run_trial.py` entrypoint produces the
  expected jsonl line schema and per-trial directories.

### Trials (0g SDK surface, 2026-05-07)

| trial_id | overrides | sub-runs | median acc | stddev | median f1 | stddev | wall | notes |
|---|---|---|---|---|---|---|---|---|
| `lti-0001` | none | 1 | 0.857 | — | 0.689 | — | 5m | validation |
| `lti-0002` | none | 3 | 0.881 | 0.024 | 0.665 | 0.015 | 13m | baseline |
| `lti-0003` | `retrieval_score_exponent=0.5` | 1 | 0.857 | — | 0.687 | — | 4m | propagation check |

Total: 22 min wall, ~$0.40 spend. Models: answer `gpt-4o-mini`,
judge `gpt-4o-2024-08-06`.

### What I learned

- `Memory.base_decay_rate` had a single consumer (`engine.py:93`) per
  exhaustive grep, so the cutover was low-risk. The lookup site moved
  cleanly to the config without breaking the SDK API.
- The daemon's `Searcher` had two hidden lookup sites
  (`candidate_to_state` + `expand_via_graph`'s scoped use) — both now
  read from `cfg.beta_for`. `Searcher::with_lifecycle(store, cfg)` is
  the canonical builder; `Searcher::new(store)` keeps paper defaults
  for tests.
- CLI's `set-llm` previously rebuilt a fresh `DaemonConfig`, which
  would have clobbered any hand-edited `[lifecycle]`. Switched to
  load → mutate → save so the surfaces don't fight each other.
- **Determinism gate (<1pp stddev) doesn't hold on LTI-Bench at n=3.**
  Baseline stddev was 2.4pp on accuracy and 1.5pp on mean_f1 across 3
  identically-configured sub-runs. The plan's risk note anticipated
  this and prescribed median-of-5; phase 1 inherits that guidance.
- **Override propagation works end-to-end.** `lti-0003` (α=0.5) shifts
  mean_f1 by +2.2pp vs baseline median — exceeds the 0.5pp gate, but
  with n=1 on the override side, can't separate noise from real
  effect. Wiring is confirmed regardless.

### Next

- Phase 1 must use n≥5 sub-runs per parameter point on LTI-Bench
  (~$0.50/point, ~25 min/point) OR switch sensitivity studies to
  LongMemEval-S (500-question sample, expected ~0.3pp stddev).
  Recommend the latter; reserve LTI-Bench for confirmation runs.
- Daemon-surface 0g (4 additional runs) skipped this session: the
  config.toml restart-write per override isn't safe for unattended
  execution. User-driven validation via the recipe in
  `tuning/README.md`.
