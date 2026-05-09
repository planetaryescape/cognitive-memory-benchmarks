# Phase 5 — full LoCoMo head-to-head (complete)

**Started:** 2026-05-09T08:00 BST
**Completed:** 2026-05-09T11:22 BST
**Wall:** 3h 22min (v0.4 6217s + v0.5 5954s, sequential)
**Cost:** ~$100
**Verdict:** **v0.5 wins +1.87pp F1, +2.73pp LLM accuracy** —
unambiguous win on both metrics. Phase 6 SDK ship fully validated.

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

## Final results

| candidate | F1 | LLM accuracy | wall | n_questions |
|---|---|---|---|---|
| v0.4 baseline (paper) | **0.4437** | **0.5857** | 6217s (1.7h) | 1540 |
| v0.5 tuned (SDK 0.5.0) | **0.4624** | **0.6130** | 5954s (1.65h) | 1540 |
| **delta** | **+1.87pp** | **+2.73pp** | — | — |

**Both metrics improve meaningfully.** The "F1 ↑ but LLM acc 0pp"
pattern from Phase 4 conv0 was sample-size noise — at n=1540 the
judge's binary accuracy delta also surfaces.

### Subcase landed: unambiguous win

Per the decision tree in the in-progress version of this doc,
this is the **best subcase**: F1 delta ≥ +1pp AND LLM accuracy
delta ≥ +1pp. Both metrics agree. v0.5 is now the official
paper-numbers baseline.

### Comparison to v6 CR-A reference

| | F1 | LLM acc |
|---|---|---|
| v6 CR-A baseline (full LoCoMo, 1540 Q) | 0.448 | 0.584 |
| Phase 5 v0.4 baseline (this run) | 0.444 | 0.586 |
| Phase 5 v0.5 tuned (this run) | 0.462 | 0.613 |

Phase 5 v0.4 ≈ v6 CR-A baseline (-0.4pp F1, +0.2pp LLM acc) —
this run reproduces the existing baseline within noise. The
4pp drift I worried about in Phase 4 (conv0 only) doesn't
appear at full benchmark — was likely conv0-specific variance.

**Real headline:** v0.5 ships +1.4pp F1 AND +3.0pp LLM acc over the
existing v6 CR-A baseline. That's a real benchmark improvement
worth a paper update.

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

## What this means for shipping

- **Phase 6 (cognitive-memory-sdk commit `707758d`, v0.5.0)** is
  validated. The two empirically-tuned defaults that drive this
  improvement on the benchmarks:
  - `associative_boost`: 0.03 → 0.05
  - `base_decay_rates.semantic`: 120 → 240
- **`core_session_threshold` 3 → 2** is in v0.5 too but the
  benchmarks adapter pinned cst=2 already, so the v0.5 shift on
  cst doesn't drive this Phase 5 lift. Still defensible from
  Phase 2 joint-search evidence (cst=3 trails 67% vs cst=1/2 at
  ~92%).
- **Paper update** can claim: "On LoCoMo full benchmark, our
  empirically-tuned defaults (v0.5) lift F1 from 44.4% to 46.2%
  and LLM accuracy from 58.6% to 61.3%, both relative to the
  paper-faithful (v0.4) baseline at the same harness configuration."

## Cost ledger (full session)

- Phase 0g: $1.30
- Phase 1: $14
- Phase 2: $15
- Phase 2.5b (top-K confirm): $2.50
- Phase 3 (LoCoMo cross-check): $2.50
- Phase 4 (LoCoMo conv0 head-to-head): $10
- **Phase 5 (full LoCoMo head-to-head): ~$100**
- Total: **~$145**

## Links

- Phase 4 milestone (Phase 5 trigger): `docs/milestones/phase-4-locomo-reality-check.md`
- Phase 5 wrapper: `tuning/scripts/run_phase5.py`
- Configs (reused from Phase 4): `tuning/spaces/phase4/`
- v6 baseline (reference for absolute numbers):
  `locomo/results/v6/parallel/conv*.json`
