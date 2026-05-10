# Phase 7 — LongMemEval-S validation (FAILED, OpenAI billing block)

**Started:** 2026-05-10T00:45 BST
**Failed:** 2026-05-10T~05:30 BST (both runs at ~150/500 questions = ~30%)
**Failure mode:** `openai.RateLimitError 429 - insufficient_quota` —
account-level billing cap reached, NOT a transient per-minute rate
limit. Resuming requires the user to add OpenAI credits / increase
the billing limit before any more API runs.
**Plan:** Head-to-head v0.4 vs v0.5 SDK defaults on LongMemEval-S
(500 questions). Same configs as Phase 4/5; same pattern (one
locomo_eval-style run per candidate, no tuning).
**Projected wall:** ~14.5h parallel (matches CR-B baseline
52,328s = 14.5h for one candidate; in-process thread pool of 53
workers handles parallelism)
**Projected cost:** ~$100 ($50 per candidate × 2 in parallel)

This is the third real benchmark for v0.5 validation, after
LTI-Bench (tuning surface) and LoCoMo (Phase 4/5 cross-validation).
LongMemEval-S has a different "shape" than LoCoMo (single-session
vs multi-session questions, abstention, knowledge updates,
temporal reasoning) — useful for distribution-robustness check.

## Goal

Answer one question: **does v0.5's lift on LoCoMo replicate on
LongMemEval-S?** No tuning — pure validation. The risk we're
checking for is that v0.5 defaults are LoCoMo-specific and
either no-op or regress on LongMemEval.

## Configs

Reused from Phase 4 (`tuning/spaces/phase4/{v04_baseline,v05_tuned}.json`).
Same v0.4 vs v0.5 deltas:
- `associative_boost`: 0.03 → 0.05
- `base_decay_rates.semantic`: 120 → 240

(Note: `core_session_threshold` 3 → 2 doesn't matter here either —
the benchmarks adapter pins cst=2 regardless of SDK default.)

## Production flag stack (matching CR-B baseline)

```
--top-k 20
--deep-recall
--rerank
--max-workers 53
```

Note: LongMemEval-S has ALWAYS used `--use-judge` style scoring
(it's built into the harness — every question gets a CORRECT/
INCORRECT verdict from gpt-4o-2024-08-06). No `--use-judge` flag
to set; it's always on.

## CR-B reference baseline

For absolute-number comparison:
- task-averaged accuracy: **71.6%**
- overall accuracy: **72.6%**
- abstention accuracy: 90.0%
- Per-type: single-session-user 85.7%, single-session-assistant
  76.8%, single-session-preference 46.7%, multi-session 69.9%,
  temporal-reasoning 64.7%, knowledge-update 85.9%

## Decision rule

After both finish:
- **v0.5 acc ≥ v0.4 acc + 1pp** → ship strengthened, paper claim
  becomes "validated on 2 of 2 real benchmarks"
- **|delta| < 1pp** → no signal on LongMemEval; document and
  caveat (still defensible — Phase 5 LoCoMo lift stands)
- **v0.5 < v0.4 by >1pp** → v0.5 defaults are LoCoMo-specific.
  Consider per-benchmark profiles or honest "tuned for LoCoMo-like
  conversational distributions" framing.

## Partial data (inconclusive — see caveats)

Both runs got to 150/500 questions before failing. Per-type
coverage is incomplete — only single-session-user (n=70),
single-session-preference (n=18 of 30 expected), and multi-session
(n=62 of 133 expected) were touched. Temporal-reasoning,
knowledge-update, single-session-assistant, and abstention all
have **0 samples** in this partial set.

| metric | v0.4 (n=150) | v0.5 (n=150) | delta |
|---|---|---|---|
| overall accuracy | 71.33% | 70.00% | -1.33pp (v0.4 ahead) |
| single-session-user | 90.0% (63/70) | 90.0% (63/70) | identical |
| single-session-preference | 33.3% (6/18) | 27.8% (5/18) | -5.6pp (n=18) |
| multi-session | 61.3% (38/62) | 59.7% (37/62) | -1.6pp (n=62) |

### Why this is NOT a Phase 6 rollback signal

1. **Sample sizes are tiny per-type.** single-session-preference at n=18
   means a single judge flip moves the percentage by 5.6pp — the entire
   "v0.4 wins" delta on that type fits inside one question's swing.
2. **Question-type composition is heavily skewed.** The first 150
   questions are dominated by single-session types where v0.4 and v0.5
   tied at 90%. The categories where v0.5 might win (temporal-reasoning,
   knowledge-update — multi-step memory tasks where longer β_semantic
   would matter) didn't get touched.
3. **The Phase 5 LoCoMo result (+1.87pp F1, +2.73pp LLM acc on 1540 Q)
   stands.** v0.5 ship is still defensible on that evidence alone. Phase 7
   was a "confirm on a second bench" check; it didn't run far enough to
   say either way.

## What to do next (operator action required)

1. **Resolve the OpenAI billing block.** Add credits / increase
   monthly cap at https://platform.openai.com/settings/organization/billing/overview
2. Once billing has headroom: **re-run Phase 7 from scratch** with
   `--start-from 0` (the partial files at `tuning/runs/phase7/v0{4,5}_result.json`
   would resume from question 150 if `--start-from 150` is set, but a
   clean re-run avoids any state from the failed runs).
3. Phase 6 ship can stay as-is. Phase 7 is "nice to have" validation;
   not load-bearing for the v0.5.0 ship.

## Pending

- Both runs in parallel. ETA revised at 01:44: 20/500 each after
  1h ≈ 25 questions/hour per run (slower than CR-B's solo 34/h
  because two parallel processes share OpenAI rate limits).
  **New ETA ~20h wall, finish around 20:45 BST today.**
- Bash background tasks fire completion notifications when each
  exits.

## Links

- CR-B baseline (reference): `longmemeval/results/current_sdk_20260505/primary.json`
- Phase 5 LoCoMo result (the previous validation): `tuning/runs/phase5/summary.json`
- Configs: `tuning/spaces/phase4/{v04_baseline,v05_tuned}.json`
