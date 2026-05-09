# Phase 5 — full LoCoMo head-to-head (in progress)

**Started:** 2026-05-09T08:00 BST (estimated)
**Plan:** Full LoCoMo (10 conversations, ~1500 questions) with v0.4
SDK defaults vs v0.5 SDK defaults. Same production flag stack as
Phase 4 + v6 CR-A baseline.
**Projected wall:** ~7h sequential (3.5h per candidate, 10 parallel
shards within each candidate)
**Projected cost:** ~$100 ($50 per candidate × 2)
**Trigger:** Phase 4 conv0 showed v0.5 +2.92pp F1 over v0.4 → Phase 5
GO per the decision rule.

This is a live milestone, refreshed as candidates land.

## Goal

Validate the +2.92pp lift Phase 4 surfaced on conv0 generalises
across all 10 LoCoMo conversations. Conv0 is just one shard;
the full benchmark catches per-conversation variance and gives
enough sample (~1500 Q) for the LLM accuracy delta to separate
from judge noise.

## Configs

Same as Phase 4 (`tuning/spaces/phase4/{v04_baseline,v05_tuned}.json`).
Reused intentionally so this is the cleanest possible n=10×conv
extension of Phase 4's n=1×conv result.

## Production flag stack (matching Phase 4 + v6 CR-A)

```
--prompt-mode mem0 --dual-perspective --deep-recall \
    --rerank --rerank-factor 3 --top-k 60 --use-judge \
    --model gpt-4o-mini
```

## Live state

| candidate | shards done | overall F1 | LLM acc | status |
|---|---|---|---|---|
| v0.4 baseline | 0 / 10 | _running…_ | | started 08:00 |
| v0.5 tuned | _pending_ | | | starts after v0.4 |

## Decision tree (after both finish)

After both candidates land, comparing weighted-by-question F1
and LLM accuracy:

- **F1 delta ≥ +1pp** → ship validated end-to-end. v0.5 is
  the new official paper-numbers baseline.
- **|F1 delta| < 1pp** → Phase 4's conv0 lift didn't generalize.
  v0.5 is no-harm but not validated. Consider rolling Phase 6
  back to v0.4 paper-faithful as the more honest position.
- **F1 delta < -1pp** → v0.5 actually regresses. Roll back
  Phase 6 SDK changes immediately.

The interesting subcase: if **F1 delta ≥ +1pp AND LLM accuracy
delta ≥ +1pp**, the win is unambiguous (both metrics agree). If
F1 delta ≥ +1pp but llm_acc delta is 0±1pp (Phase 4's pattern at
n=152), the win is real-but-narrow.

## Pending

- Phase 5 v0.4 baseline running (10 parallel shards). Bash task
  notification will fire when wrapper exits.
- Phase 5 v0.5 tuned will auto-start after v0.4 finishes (the
  wrapper runs them sequentially).

## Links

- Phase 4 milestone (Phase 5 trigger): `docs/milestones/phase-4-locomo-reality-check.md`
- Phase 5 wrapper: `tuning/scripts/run_phase5.py`
- Configs (reused from Phase 4): `tuning/spaces/phase4/`
- v6 baseline (reference for absolute numbers):
  `locomo/results/v6/parallel/conv*.json`
