# Phase 7 — LongMemEval-S validation (in progress)

**Started:** 2026-05-10T00:45 BST
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

## Live state

| candidate | accuracy | task_avg | wall | status |
|---|---|---|---|---|
| v0.4 baseline | _running…_ | | | starts ~13:00 |
| v0.5 tuned | _running…_ | | | starts ~13:00 |

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
