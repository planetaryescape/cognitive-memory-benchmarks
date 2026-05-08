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
| `lti-0003` | `retrieval_score_exponent=0.5` | 1 | 0.857 | — | 0.687 | — | 4m | single override |
| `lti-0004` | `retrieval_score_exponent=0.5` | 3 | 0.881 | 0.014 | 0.688 | **0.002** | 12m | α override stddev |
| `lti-0005` | `base_decay_rates.semantic=60` | 3 | 0.881 | 0.014 | 0.686 | 0.017 | 12m | β override (Phase 0a-sdk headline) |
| `lti-0006` | none (replication of lti-0002) | 3 | 0.881 | **0.000** | **0.688** | **0.002** | 12m | confirms lti-0002 was the outlier |

Total: 58 min wall, ~$1.30 spend. Models: answer `gpt-4o-mini`,
judge `gpt-4o-2024-08-06`.

**Final reading after lti-0006 replication:** when I re-ran the same
baseline config hours later, it landed at f1=0.688 with stddev=0.002
— matching the override conditions, not the original lti-0002
baseline. The original baseline was the noisy outlier; the
"+2pp shift under override" was 100% noise. The wiring is
verified by 41 unit tests (28 benchmark + 5 SDK + 8 daemon)
plus the new e2e test (commit `02858d0` in cognitive-memory-daemon)
that proves daemon-side override propagation through IPC. LTI-Bench
itself is more stable than first thought — when the judge has a
clean draw, stddev is well below the 1pp gate.

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
- **Noise is condition-dependent, not just sample-size-driven.** The
  α=0.5 override (`lti-0004`) had only 0.2pp stddev on mean_f1
  vs the baseline's 1.5pp — a 7.5× reduction. Plausible mechanism:
  higher α weights retention more in scoring, producing a more
  deterministic memory ranking → less judge variance. Could also be
  coincidence at n=3; worth a follow-up at n≥10 in Phase 1.
- **Override propagation confirmed at n=3.** `lti-0004` (α=0.5)
  median mean_f1 = 0.688 vs baseline median 0.665 = +2.3pp gap,
  ~1.5σ above baseline noise. Directionally meaningful; not yet
  2σ confident. accuracy medians identical — α doesn't move
  accuracy on this bench.
- **Replication failure pattern.** `lti-0005` (β_semantic=60, a
  much larger perturbation than α=0.3→0.5) produced f1 median
  0.686 — almost identical to lti-0004. Both override conditions
  cluster at ~0.687; only the baseline at 0.665 looks anomalous.
  Updated reading: the +2pp shift was almost certainly regression
  to the mean from a noisy baseline draw, not a real α effect.
  The override pipeline IS reaching engine.compute_retention
  (proven by unit tests); LTI-Bench at n=42 just isn't powered to
  detect the underlying effect against LLM-judge noise.
- **Confirmed by lti-0006 replication.** Re-running the exact same
  baseline config hours later landed at f1=0.688 with stddev=0.002
  — matching the override conditions, not the original lti-0002.
  Definitive: the original "baseline" had a bad LLM-judge day; the
  "+2pp under override" was 100% noise. LTI-Bench's actual noise
  floor on a clean draw is ~0.2pp on f1 — well within the 1pp
  gate; the gate failure was draw-specific, not bench-property.
- **Phase 1 implication: re-run any trial with stddev > 0.5pp.** A
  single 3-run trial can land on a noisy draw; treat high stddev
  as a re-run trigger rather than a noise-floor measurement.

### Next

- **Don't use LTI-Bench for sensitivity sweeps.** 42 questions is too
  small for the LLM-judge noise floor to settle. Use it as a
  confirmation step only at promising parameter points found
  elsewhere.
- **Move Phase 1 sensitivity work to LongMemEval-S** (500-question
  sample, expected ~0.3pp stddev — restores the <1pp gate). Costs
  more per run but gives meaningful effect detection at n=3.
- Always measure both arms (≥3 sub-runs each) — single-shot deltas
  against a noisy baseline median produce phantom effects.
- Daemon-surface 0g (4 additional runs) skipped this session: the
  config.toml restart-write per override isn't safe for unattended
  execution. User-driven validation via the recipe in
  `tuning/README.md`.

---

## 2026-05-08 — Phase 1: OFAT sensitivity sweeps (in progress)

**Status:** complete (47/47 trials, finished 2026-05-08T06:43 BST; 9.5h wall; ~$14 spend; exit code 0).

First execution of `tuning/scripts/run_phase1.py` against
`tuning/spaces/phase1/sweeps.json`. 10 Tier 1+2 parameters,
5 values each (where applicable), n=3 sub-runs per value =
141 total LTI-Bench sub-runs. Pace: ~12.2 min per (param, value)
trial — total wall ~9.5h, projected cost ~$14. Started 21:16
on 2026-05-07; CSV at `tuning/runs/phase1_sensitivity.csv`.

### Headline findings (9/10 sweeps complete)

**Easy wins (improve over defaults):**
- `associative_boost`: **default 0.03 is the worst value** in the
  sweep. f1=0.664 at default vs ~0.684 at any other value
  (0.01, 0.05, 0.07, 0.10). Bumping to 0.05 looks like a free
  +2pp; default may have been chosen without empirical backing.
- `base_decay_rates.semantic = 240` (longer than paper Table 2's
  120d) hits f1=0.703 vs default's 0.689 → +1.4pp. Phase 2 should
  sweep further (300, 360) — ceiling not yet found.

**Defaults validated:**
- `direct_boost = 0.1` is the sweet spot (f1=0.697). 0.05/0.15/0.20
  /0.25 all worse. Bimodal pattern but default wins clearly.
- `retrieval_score_exponent (α) = 0.3` (default): only α=0.1
  underperforms (f1=0.665); α=0.3 through 0.9 are statistically
  flat at ~0.687-0.690.

**Drop from Phase 2 search space (no signal):**
- `core_access_threshold`: confirmed completely flat across all
  5 values: 3 (0.6876), 5 (0.6874), 10 (default, 0.6880), 15
  (0.6876), 20 (0.6877) — range 0.06pp on f1. Drop from Phase 2.
- `core_stability_threshold`: confirmed flat across all 5 values:
  0.6 (0.6874), 0.7 (0.6888), 0.85 (default, 0.6876), 0.9
  (0.6893), 0.95 (0.6891) — range 0.20pp on f1. Drop from Phase 2.
- `decay_model`: exponential vs power within noise (0.41pp).
  Pick either; not worth a search dimension.

**Mixed / suspect signals:**
- `core_session_threshold = 4` is anomalously bad (f1=0.665 vs
  ~0.686 at 1, 2, 3, 6). Looks like a noisy single trial; the
  surrounding points are flat. Re-run candidate.
- `power_decay_gamma`: γ=2.5 hurts (f1=0.675); 0.7-2.0 are flat.
- `base_decay_rates.episodic`: shorter is better — 15, 30, 45
  cluster at ~0.689; 90 and 180 drop to ~0.660. Default 45 is
  fine; do not lengthen.

### Trials so far

| param | values swept | f1 range | best value |
|---|---|---|---|
| retrieval_score_exponent | 0.1, 0.3, 0.5, 0.7, 0.9 | 2.51pp | 0.5 (within noise of default) |
| direct_boost | 0.05, 0.1, 0.15, 0.2, 0.25 | 3.21pp | 0.1 (default) |
| associative_boost | 0.01, 0.03, 0.05, 0.07, 0.1 | 2.19pp | 0.05/0.07 (>>default 0.03) |
| decay_model | exponential, power | 0.41pp | tied |
| power_decay_gamma | 0.7, 1.0, 1.4427, 2.0, 2.5 | 1.38pp | 2.0 (within noise) |
| base_decay_rates.semantic | 30, 60, 120, 180, 240 | 2.48pp | **240 (>default 120)** |
| base_decay_rates.episodic | 15, 30, 45, 90, 180 | 2.95pp | 30 (within noise of default) |
| core_session_threshold | 1, 2, 3, 4, 6 | 2.24pp | 1 (within noise; 4 anomalous) |
| core_access_threshold | 3, 5, 10, 15, 20 | 0.06pp | flat (drop) |
| core_stability_threshold | 0.6, 0.7, 0.85, 0.9, 0.95 | 0.20pp | flat (drop) |

### What I'm learning about the methodology

- The Phase 0g concern about LTI-Bench being too noisy at n=42 is
  partially borne out: many sweep ranges are ~2-3pp, sitting at
  the edge of the bench's noise floor. But signals ARE separable
  for the strongest movers (associative_boost, base_decay_rates.
  semantic at the high end). The 2pp drop-gate from the parent
  plan is the right call.
- n=3 is the floor; some trials have stddev ~0.018 (1.8pp), big
  enough to be confused with effects in adjacent param values. A
  re-run loop targeting trials with stddev > 0.01 would tighten
  the picture.
- The "draw effect" from Phase 0g recurs: trials with stddev=0 sit
  next to trials with stddev=0.018 on the same param sweep, i.e.
  some sub-runs cluster cleanly and some don't. This is judge
  variance, not engine variance.

### Next

- Phase 2 (Optuna inner loop) inherits a 2- or 3-dim search:
  - **Drop:** core_access_threshold, core_stability_threshold,
    decay_model (all flat)
  - **Lock at default:** retrieval_score_exponent (0.3),
    direct_boost (0.1), base_decay_rates.episodic (45),
    power_decay_gamma (1.4427)
  - **Search:**
    - `associative_boost ∈ [0.04, 0.10]` — default 0.03 is the
      WORST value tested; bumping to 0.05 gives ~+2pp f1
    - `base_decay_rates.semantic ∈ [180, 400]` — 240 hit the
      sweep maximum at 0.703; ceiling untested
    - Optionally `core_session_threshold ∈ {1, 2, 3}` — value=4
      was anomalous (single bad trial); 1/2/3 all flat at default
- Phase 2 scaffolding ready (commit `f5e6f3d`):
  `tuning/spaces/phase2/space.json` + `tuning/scripts/run_optuna.py`.
  Run with `python tuning/scripts/run_optuna.py --space tuning/spaces/phase2/space.json`.
  ~50 trials × n=3 ≈ 12.5h, ~$15.
- Phase 6 (ship) candidate: flip `associative_boost` default from
  0.03 to 0.05+. Re-run that point at n≥5 to confirm before
  shipping a default change.

---

## 2026-05-08 — Phase 2: Optuna inner-loop tuning (in progress)

**Status:** in-progress (started 2026-05-08T09:41 BST; 30 of 50
trials complete at 16:34 — 60% done; TPE exploitation phase well
underway; per-trial pace ~13.7 min → projected end ~18:48 BST).
Last refresh 16:38 BST.

Bayesian optimization (Optuna TPE) over the 3 dimensions Phase 1
narrowed to. Output: top-5 candidate configs to promote to Phase 3.

### Search space (`tuning/spaces/phase2/space.json`)

| dim | range | Phase 1 finding |
|---|---|---|
| associative_boost | float [0.04, 0.10] | default 0.03 was worst; 0.05/0.07 best |
| base_decay_rates.semantic | float [180, 400] | 240 hit OFAT max; ceiling untested |
| core_session_threshold | int {1, 2, 3} | OFAT flat across 1/2/3 |

### Fitness

Weighted composite (paper Tables 8-9 metrics):
- 0.20 × decay_trivial
- 0.30 × core_persistence
- 0.30 × revival
- 0.10 × associative
- 0.10 × contextual_retention

Median of n=3 sub-runs feeds the fitness.

### Live state

_Best-known refreshed as trials land. Full table at sweep end._

**Best so far:** Trial 9, fitness=0.6525 (associative_boost=0.049,
β_semantic=190, core_session_threshold=3). Improvement over earliest
trial: +0.34pp — within noise. TPE exploration phase complete (trials
0-9); exploitation begins trial 10.

| trial | associative_boost | β_semantic | core_sess_thr | fitness |
|---|---|---|---|---|
| 0 | 0.086 | 331.6 | 1 | 0.6491 |
| 1 | 0.073 | 237.2 | 3 | 0.6152 |
| 2 | 0.060 | 191.8 | 1 | 0.6507 |
| 3 | 0.092 | 338.8 | 1 | 0.6157 |
| 4 | 0.074 | 250.6 | 1 | 0.6491 |
| 5 | 0.070 | 209.1 | 1 | 0.6488 |
| 6 | 0.070 | 371.2 | 2 | 0.6514 |
| 7 | 0.061 | 210.8 | 1 | 0.6459 |
| 8 | 0.080 | 221.3 | 2 | 0.6148 |
| 9 | 0.049 | 190.2 | 3 | **0.6525** ← best |
| 10 | 0.046 | 289.6 | 3 | 0.6489 |
| 11 | 0.040 | 397.3 | 2 | 0.6508 |
| 12 | 0.055 | 396.5 | 3 | 0.6496 |
| 13 | 0.051 | 280.8 | 2 | 0.6491 |
| 14 | 0.064 | 345.5 | 3 | 0.6181 |
| 15 | 0.099 | 366.4 | 2 | 0.6491 |
| 16 | 0.050 | 311.9 | 2 | 0.6525 ← tied with best |
| 17 | 0.048 | 313.8 | 3 | 0.6155 |
| 18 | 0.042 | 269.0 | 2 | 0.6477 |
| 19 | 0.054 | 313.2 | 3 | 0.6514 |
| 20 | 0.048 | 185.7 | 2 | 0.6491 |
| 21 | 0.068 | 368.9 | 2 | 0.6491 |
| 22 | 0.056 | 306.5 | 2 | 0.6488 |
| 23 | 0.078 | 367.1 | 2 | **0.6532** ← new best (+0.06pp, within noise) |
| 24 | 0.080 | 255.5 | 3 | 0.6457 |
| 25 | 0.082 | 352.8 | 2 | 0.6491 |
| 26 | 0.075 | 324.2 | 2 | 0.6491 |
| 27 | 0.065 | 380.4 | 3 | 0.6491 |
| 28 | 0.090 | 299.2 | 2 | 0.6459 |
| 29 | 0.086 | 332.9 | 2 | 0.6459 |

**Cluster picture after 30 trials:** 24 high, 5 low. **17 distinct
fitness values** total — the bench emits a discrete set, with
"0.6491" alone hit 9 times. Trial 23's "best" of 0.6532 is +0.06pp
above the 0.6525 cluster — within the 3-question coin-flip noise
floor identified in Phase 2.5.

**cst hit-rate sharpening at n=30:**

| cst | hit rate | samples |
|---|---|---|
| 1 | 83% | 6 |
| 2 | **93%** | 14 |
| 3 | 67% | 9 |

cst=2 is now decisively the cleanest in the joint search (Phase 1
OFAT had cst=1/2/3 all flat at default). With cst=2 at n=14 the
93% hit-rate is more credible than at n=7 earlier. cst=3 trailing
holds.

### Phase 2.5 — per-question variance analysis (DONE, $0)

Built `tuning/scripts/analyze_question_variance.py` to localize the
bimodal-cluster mystery. Ran across 216 result.json files (Phase
0g + 1 + first 20 Phase 2 trials).

**Headline finding: 35 of 42 LTI-Bench questions are stable
(judge always agrees with itself); the bimodal-cluster behavior
is driven by 3 marginal questions.**

| variance | subscore | correct rate | flips | question |
|---|---|---|---|---|
| 0.959 | revival | 60% (130/216) | 89 | "Was there anything about the weather I mentioned once?" |
| 0.955 | revival | 39% (85/216) | 105 | "Did I ever mention traffic?" |
| 0.826 | decay_trivial | 71% (153/216) | 70 | "What did I have for lunch on day 3?" |

Two of the three marginal questions are in `revival` (weight 0.30
in the fitness composite), so revival is over-represented as a
noise source — a single revival flip swings composite by ~2pp.

Other observations from the 216-replicate scan:
- A `conflict` question is a **stable engine weakness** rather
  than judge variance: "When is the Helios project deadline?"
  is wrong 93% of the time (15/216 correct). Real bug, worth
  investigating in the engine; not noise.
- The `core_persistence` and `contextual_retention` questions
  are uniformly stable. Those weights (0.30 + 0.10 = 0.40 of
  composite) are noise-free.

**What this means for Phase 2:** the remaining 30 trials will keep
flipping the same 3-question coin. Don't expect new information
beyond the existing best at 0.6525.

**What this means for Phase 6 / paper:**
- LTI-Bench v3 should reword the 3 marginal questions or expand
  bench size from 42 to dilute single-question weight.
- Re-judging just the 3 marginal questions with gpt-4o (vs the
  pinned gpt-4o-2024-08-06) might be the cheapest fix — costs ~$0.10.
- The conflict-resolution failure is a real engine signal, separate
  from tuning. Worth a follow-up issue.

**Reprioritized post-sweep plan (was 4 items):**
- ~~Per-question variance analysis~~ → DONE.
- Judge-variance baseline (~$2): less needed; mechanism now known.
- Top-5 re-run at n=5 (~$5): still useful for ranking confidence.
- Switch sampler: unlikely to help; sampler smartness can't beat
  bench resolution.

### Cost projection

50 trials × 3 sub-runs × ~5min = 12.5h wall, ~$15. Total Phase 0+1+2
projected ~$30 against the original Phase 0+1+2 budget of ~$30.

### Resumability

Optuna SQLite study at `tuning/runs/phase2/lti-phase2.db`.
`run_optuna.py --resume` picks up after a process death.

### Next

- Refresh this entry every ~5 trials with the running best.
- Phase 3 (decay-shape cross-check) starts when Phase 2 lands the
  top-5 candidates.
- Phase 6 (ship) candidate already locked in from Phase 1:
  `associative_boost = 0.05`. Phase 2 may surface a tighter value
  (e.g. 0.06) but the direction is settled.
