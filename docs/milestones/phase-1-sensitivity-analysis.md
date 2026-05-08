# Phase 1 — sensitivity analysis (in progress)

**Started:** 2026-05-07T21:16 BST
**Sweep status (last refresh 2026-05-08T06:17 BST):** 44/47 trials done, 3 remaining (~36min ETA)
**API spend so far:** ~$13 (estimated from 132 sub-runs at ~$0.10 each)
**Projected total:** ~$14 spend, ~9.5h wall

This is a live milestone. Final write-up happens when the sweep
completes; until then this captures interim results so they don't
get lost if the process dies.

## Goal

Per parent plan §1, OFAT (one-factor-at-a-time) sensitivity sweep
over Tier 1+2 parameters. For each param, hold all others at
default, sweep through 5 values, record LTI-Bench composite. Drop
any param whose 5-value range moves the composite by < 2pp (the
parent plan's noise threshold; Phase 0g found this is the right
threshold for LTI-Bench at n=42).

Output: prunes Phase 2's Optuna search space from 10 dimensions
down to (currently estimated) 4-5.

## Sweep plan (`tuning/spaces/phase1/sweeps.json`)

10 parameters × 5 values × 3 sub-runs = 141 LTI-Bench sub-runs.
Models: answer `gpt-4o-mini`, judge `gpt-4o-2024-08-06`. Trials
indexed `lti-0007` through `lti-0053`. CSV at
`tuning/runs/phase1_sensitivity.csv`.

## Headline findings (interim, 9/10 sweeps complete)

### Easy wins

**`associative_boost`: default 0.03 is the WORST value tested.**

| value | f1 median | stddev |
|---|---|---|
| 0.01 | 0.6840 | 0.013 |
| **0.03 (default)** | **0.6635** | 0.013 |
| 0.05 | 0.6853 | 0.013 |
| 0.07 | 0.6854 | 0.010 |
| 0.10 | 0.6833 | 0.015 |

The default sits in a local minimum. Bumping to 0.05 looks like a
+2pp free win. Phase 2 Optuna should narrow-search [0.04, 0.08].
Phase 6 (ship) is a strong candidate to flip the default.

**`base_decay_rates.semantic = 240` (longer than paper Table 2's 120):**

| value | f1 median | stddev |
|---|---|---|
| 30 | 0.6778 | 0.003 |
| 60 | 0.6877 | 0.015 |
| 120 (default) | 0.6888 | 0.007 |
| 180 | 0.6856 | 0.012 |
| **240** | **0.7026** | 0.012 |

+1.4pp at the long end. Suggests the paper's β_semantic=120d is
too short for LTI-Bench's question distribution. Phase 2 should
sweep further (300, 360) to find the ceiling.

### Defaults validated

**`direct_boost = 0.1` is the sweet spot** (range 3.21pp).

| value | f1 median |
|---|---|
| 0.05 | 0.686 |
| **0.1 (default)** | **0.697** |
| 0.15 | 0.670 |
| 0.2 | 0.688 |
| 0.25 | 0.665 |

Bimodal pattern but default wins clearly.

**`α (retrieval_score_exponent) = 0.3`** (default).

α=0.1 is bad (f1=0.665). α=0.3 through 0.9 all sit at 0.685-0.690
— statistically flat. Default is at the inflection point; no
signal above it.

### Drop from Phase 2

**`core_access_threshold` has no signal** — confirmed flat across
all 5 values: 3 (0.6876), 5 (0.6874), 10 (default, 0.6880),
15 (0.6876), 20 (0.6877). Range 0.06pp on f1. Drop from Optuna
search space.

**`decay_model` (exponential vs power)** within noise (0.41pp).
Pick either; not worth a search dimension.

### Mixed signals (re-run candidates)

**`core_session_threshold = 4` is anomalous** (f1=0.665 vs ~0.686
at 1, 2, 3, 6). Single noisy trial; surrounding values are flat.

**`power_decay_gamma`: γ=2.5 hurts** (0.675 vs ~0.687). Default
1.4427 fine; no signal in [0.7, 2.0].

**`base_decay_rates.episodic`: shorter is better.** 15, 30, 45 at
~0.689; 90, 180 drop to ~0.660. Default 45 is fine; do not
lengthen.

## Pending

- `core_stability_threshold` sweep — 2 of 5 values done so far:
  0.6 (f1=0.6874) and 0.7 (f1=0.6888). Range 0.14pp; looking
  flat. Pending: 0.85 (default, currently running), 0.9, 0.95.

## Phase 2 search-space recommendation (interim)

Down from 10 to ~3 active dimensions:

| param | Phase 2 action |
|---|---|
| associative_boost | search narrowly [0.04, 0.08] |
| base_decay_rates.semantic | search [180, 400] (ceiling untested) |
| core_session_threshold | search {1, 2, 3} (4 anomalous, others flat) |
| direct_boost | lock at 0.1 (default) |
| retrieval_score_exponent | lock at 0.3 (default) |
| base_decay_rates.episodic | lock at 45 (default; ≥30 also fine) |
| power_decay_gamma | lock at 1.4427 (default) |
| decay_model | lock (either; no signal) |
| core_access_threshold | **drop** (confirmed flat across 5 values: range 0.06pp) |
| core_stability_threshold | likely drop — 0.6 / 0.7 flat at f1≈0.688; 0.85 / 0.9 / 0.95 pending |

If Phase 2 search is just 3 dimensions with narrow ranges, Optuna
needs ~30-50 trials instead of 150 → ~$3-5 instead of ~$15.

## What's working / what's not

- **The harness:** trials run reliably, CSV append is durable, no
  process crashes across ~120 sub-runs in ~8h.
- **n=3 is borderline.** stddev ranges from 0.001 to 0.022 across
  trials — same param sweep can have a 0.0pp stddev value sitting
  next to a 1.8pp stddev value. The "draw effect" from Phase 0g
  recurs. A re-run loop for trials with stddev > 0.01 would
  tighten interpretations.
- **2pp threshold is right.** The strongest signals (associative_
  boost +2.2pp, base_decay_rates.semantic +1.4pp) sit just at the
  edge of detectability. Smaller effects would be lost.

## Cost so far

- API: ~$11 (40 trials × 3 sub-runs × ~$0.09)
- Wall: 8h elapsed
- Total Phase 0 + 1 spend: ~$12.30 against the original
  Phase 0 budget of $1 + Phase 1 budget of $14.

## Links

- CSV: `tuning/runs/phase1_sensitivity.csv`
- Per-trial artifacts: `tuning/runs/lti-{0007..0053}/`
- experimentlog_v2.md entry: `2026-05-08 — Phase 1: OFAT
  sensitivity sweeps`
- Sweep spec: `tuning/spaces/phase1/sweeps.json`
- Runner: `tuning/scripts/run_phase1.py`
