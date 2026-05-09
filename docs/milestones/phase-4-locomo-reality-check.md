# Phase 4 — LoCoMo conv0 reality check (in progress)

**Started:** 2026-05-09T06:42 BST
**Plan:** Head-to-head LoCoMo conv0 with v0.4 SDK defaults vs v0.5
SDK defaults (the Phase 6 tuned values from commit `707758d`).
Production flag stack identical to existing v6 baseline so the
result lands in the same metric space.
**Projected wall:** ~96 min (matches v6 CR-A baseline at 5776s/conv)
**Projected cost:** ~$10 ($5 per run × 2 in parallel)

This is a live milestone, refreshed as runs land.

## Goal

Validate that the v0.5 default flips actually improve a real
benchmark, not just the LTI-Bench composite Phase 1+2 optimised
against. LoCoMo conv0 is a legitimate distribution (152 questions,
3.6× LTI's sample size) — if v0.5 ≥ v0.4 by ≥1pp on F1, the Phase 6
ship is validated and Phase 5 (full LoCoMo, all 10 conversations)
is worth running for the paper. If v0.5 ≤ v0.4, **the Phase 6
ship is wrong and we need to debug** before Phase 5.

## What's actually different between v0.4 and v0.5 here

The benchmarks adapter (shared/adapter.py) was already pinning
some Tier 1 params: `core_session_threshold=2`, `core_access_
threshold=3`, `core_stability_threshold=0.50`. So the only
*meaningful* deltas in this comparison are:

- `associative_boost`: 0.03 (paper) → 0.05 (v0.5)
- `base_decay_rates.semantic`: 120 (paper) → 240 (v0.5)

The v0.5 cst flip (3 → 2) doesn't show up here because the adapter
already overrode it.

## Production flag stack (matching v6 CR-A baseline)

```
--prompt-mode mem0
--dual-perspective
--deep-recall
--rerank --rerank-factor 3
--top-k 60
--use-judge
--max-conversations 1   (conv0 only for Phase 4; Phase 5 does all 10)
--model gpt-4o-mini
```

Without these the F1 caps at ~0.31 (vanilla flags). With them the
v6 baseline hits 0.470. We need the v0.4 vs v0.5 comparison in the
0.470-ish range so the delta is meaningful.

## Live trial state

| config | trial dir | F1 | LLM accuracy | wall | status |
|---|---|---|---|---|---|
| v0.4 (paper defaults) | _running…_ | | | | started 06:42 |
| v0.5 (SDK 0.5.0 tuned) | _running…_ | | | | started 06:42 |

## Decision rule

After both finish:
- **If v0.5 F1 ≥ v0.4 F1 + 1pp** → Phase 6 ship validated; kick off
  Phase 5 (full LoCoMo all 10 conversations, ~$100, ~3.5h
  parallel).
- **If v0.5 F1 within ±1pp of v0.4** → no signal; document and
  stop. Phase 6 still defensible (it's a "no harm" change) but
  not a validated win.
- **If v0.5 F1 < v0.4 F1 - 1pp** → Phase 6 ship is wrong on real
  benchmarks. Roll back the SDK changes; investigate why LTI-Bench
  signal didn't transfer.

## Pending

- Both runs in progress. Bash background tasks fire completion
  notifications when done. ETA ~08:15 BST.

## Links

- Phase 1 OFAT findings: `docs/milestones/phase-1-sensitivity-analysis.md`
- Phase 2 Optuna findings: `docs/milestones/phase-2-optuna-tuning.md`
- v6 baseline (single conv0): `locomo/results/v6/parallel/conv0.json`
  (F1 = 0.470, LLM acc = 0.645, 5776s wall)
- Phase 6 SDK ship: `cognitive-memory-sdk` commit `707758d`
- Phase 4 configs: `tuning/spaces/phase4/{v04_baseline,v05_tuned}.json`
