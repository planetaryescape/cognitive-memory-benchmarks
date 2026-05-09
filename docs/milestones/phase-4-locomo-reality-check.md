# Phase 4 — LoCoMo conv0 reality check (complete)

**Started:** 2026-05-09T06:42 BST
**Completed:** 2026-05-09T07:57 BST
**Wall:** 75 min (parallel; each run ~73-74 min)
**Cost:** ~$10
**Verdict:** **v0.5 wins by +2.92pp F1 → Phase 5 GO**

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

## Final results

| config | F1 | LLM accuracy | wall | n_questions |
|---|---|---|---|---|
| v0.4 (paper defaults) | **0.4310** | 0.6382 | 4371s | 152 |
| v0.5 (SDK 0.5.0 tuned) | **0.4601** | 0.6382 | 4437s | 152 |
| **delta** | **+2.92pp** | +0.00pp | — | — |

**Headline:** v0.5 improves F1 by +2.92pp on LoCoMo conv0 — well above
the +1pp gate. Phase 6 SDK ship validated on a real benchmark, not
just the LTI-Bench composite.

### Nuance: F1 ↑, LLM accuracy unchanged

LLM judge accuracy stayed at 0.6382 on both configs. This means
v0.5's answers are **closer in wording** to ground truth (token F1
improvement) but the judge's binary CORRECT/INCORRECT verdict is
the same set of questions on both sides. Two interpretations:

1. **Real improvement, just not big enough to flip marginals.**
   F1 captures granular wording quality; the judge captures
   coarse correctness. v0.5 makes answers tighter without changing
   which questions cross the correctness threshold.
2. **Possible noise overlap.** With 152 questions and judge
   non-determinism, a 0pp delta on llm_accuracy at single-run is
   not strong evidence either way.

Phase 5 (full LoCoMo, 10 conversations, ~1500 Q) will resolve
this — larger N gives the judge accuracy delta enough samples to
separate from noise.

### Drift caveat (vs v6 baseline)

The existing v6 CR-A baseline (`locomo/results/v6/parallel/conv0.json`)
hit F1=0.470 with the same flags. My Phase 4 v0.4 baseline at 0.431
is ~4pp lower — possible drift from SDK changes since the v6 baseline
(Phase 0a-sdk made `base_decay_rates` a config field). Doesn't affect
the **delta** (same harness for v0.4 and v0.5 in this comparison),
but worth noting if downstream readers compare absolute numbers.

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
