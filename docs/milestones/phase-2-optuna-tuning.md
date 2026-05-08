# Phase 2 — Optuna inner-loop tuning (in progress)

**Started:** 2026-05-08T09:41 BST
**Sweep status (last refresh 2026-05-08T11:59 BST):** 10 of 50 trials complete (initial TPE exploration phase done); trial 10 in progress (first exploitation step)
**Per-trial pace (measured):** ~13.6 min/trial → projected ~10h total wall
**Projected end:** ~19:41 BST tonight
**Projected cost:** ~$15
**Output:** `tuning/runs/phase2/lti-phase2.db` (Optuna SQLite study)

This is a live milestone, refreshed as trials land. Final write-up
when the study completes; until then this captures interim
ranking + best-trial state.

## Goal

Bayesian optimization (Optuna TPE sampler, default) over the
parameters Phase 1 surfaced as moving the LTI-Bench composite
above the noise floor. Output: top-5 candidate configs that get
promoted to Phase 3 (decay-shape cross-check) and ultimately to
Phase 6 (ship the tuned defaults).

## Search space (per `tuning/spaces/phase2/space.json`)

3 active dimensions, narrowed from Phase 1 OFAT findings:

| param | range | Phase 1 finding driving the range |
|---|---|---|
| `associative_boost` | float [0.04, 0.10] | default 0.03 was worst; 0.05/0.07 best in OFAT |
| `base_decay_rates.semantic` | float [180, 400] | 240 hit OFAT max f1=0.703; ceiling untested |
| `core_session_threshold` | int {1, 2, 3} | OFAT flat across 1/2/3; value=4 anomalous (excluded) |

All other Tier 1+2 params are locked at their current defaults
(validated in Phase 1 as either optimal or showing no signal).

## Fitness function

Weighted composite of LTI-Bench sub-scores (parent plan §2):

```
0.20 * decay_trivial.mean_f1
+ 0.30 * core_persistence.mean_f1
+ 0.30 * revival.mean_f1
+ 0.10 * associative.mean_f1
+ 0.10 * contextual_retention.mean_f1
```

Median across n=3 sub-runs feeds the fitness — single-outlier
sub-runs don't tank a candidate. Weights mirror paper Tables 8-9
target metrics; remaining 0.20 spreads across associative +
contextual_retention so they don't silently regress.

## Live trial state

_Updated as trials land. Full table at sweep end; this section
shows the running best + the most recent ~5 trials so the
in-progress doc stays scannable._

**Best so far:** Trial 9, fitness=0.6525 (associative_boost=0.049, β_semantic=190, core_session_threshold=3). Note this is the *fitness composite*, not overall.mean_f1 — Phase 1 OFAT's f1 of ~0.69 isn't directly comparable.

| trial | associative_boost | β_semantic | core_session_threshold | fitness |
|---|---|---|---|---|
| 0 | 0.0864 | 331.6 | 1 | 0.6491 |
| 1 | 0.0734 | 237.2 | 3 | 0.6152 |
| 2 | 0.0596 | 191.8 | 1 | 0.6507 |
| 3 | 0.0918 | 338.8 | 1 | 0.6157 |
| 4 | 0.0736 | 250.6 | 1 | 0.6491 |
| 5 | 0.0698 | 209.1 | 1 | 0.6488 |
| 6 | 0.0701 | 371.2 | 2 | 0.6514 |
| 7 | 0.0609 | 210.8 | 1 | 0.6459 |
| 8 | 0.0801 | 221.3 | 2 | 0.6148 |
| 9 | 0.0487 | 190.2 | 3 | **0.6525** ← best so far |
| 10 | _running…_ | | | first TPE exploitation step |

**Bimodal landscape after 10 trials (TPE exploration phase).**

- **High cluster (0.645-0.653):** trials 0, 2, 4, 5, 6, 7, 9 (7 of 10)
  — mixed across all 3 cst values (1, 1, 1, 1, 2, 1, 3).
- **Low cluster (0.615-0.616):** trials 1, 3, 8 (3 of 10) — also
  mixed cst (3, 1, 2).

Neither cst nor associative_boost nor β cleanly separates the two
clusters. Most likely the gap is **judge variance** on a few
specific marginal questions (same "draw effect" Phase 0g flagged).
With n=3 sub-runs and 42 questions, individual question flips can
move the composite by ~3-4pp.

**Implication:** the "winner" found by Optuna may not actually beat
the "loser" if judge draws had been swapped. Phase 3 (decay-shape
cross-check on a different distribution) is now load-bearing —
without it, Phase 2 picks a noise-lottery winner.

TPE exploitation begins at trial 10. If exploitation finds a
config that consistently lands in the upper tail (>0.652), that's
real signal. If it just keeps cycling between the two clusters
regardless of params, the bench is the bottleneck.

**Pattern (updated trial 6):** the cst=1 trials cluster at 0.649-0.651
(trials 0, 2, 4, 5). Trial 6 with cst=2 + long β=371 just nudged
to 0.6514 (+0.07pp over the cst=1 cluster). Earlier cst=3 trial
(trial 1) landed at 0.615. Tentative read: cst=1 or 2 both work;
cst=3 underperforms; β toward the long end of [180, 400] may be
the real win, consistent with Phase 1 finding that β=240 hit
OFAT max with ceiling untested.

**Note on the early baseline:** TPE is sampling broadly across
the prior in trials 0-9 (default Optuna behaviour) before
exploiting. Don't read fitness=0.6491 as a regression — the
fitness is a different metric than overall.mean_f1 (it's a
weighted composite), and the first sample is just the seed point.

## Pending

- 50 Optuna trials, sequential (TPE sampler doesn't parallelise
  trivially without a `RDBStorage` pool config — kept simple for
  Phase 0g/1 reproducibility).
- Each trial: write temp config → run_trial.py with --repeat 3 →
  parse jsonl → compute fitness → report to study.

## Resumability

The Optuna study persists to SQLite. If the process dies
mid-sweep:

```bash
.venv/bin/python tuning/scripts/run_optuna.py \
    --space tuning/spaces/phase2/space.json \
    --resume
```

Resumes from the last completed trial. Per-trial artifacts in
`tuning/runs/lti-NNNN/run-NN/` are preserved regardless.

## Inspection

After the sweep (or any time):

```bash
# Quick summary from the SQLite study
.venv/bin/python -c "
import optuna
s = optuna.load_study(study_name='lti-phase2',
                      storage='sqlite:///tuning/runs/phase2/lti-phase2.db')
print(f'best fitness: {s.best_value:.4f}')
print(f'best params:  {s.best_params}')
print(f'n_trials:     {len(s.trials)}')
"

# Or open the dashboard
optuna-dashboard sqlite:///tuning/runs/phase2/lti-phase2.db
```

## Links

- Phase 1 milestone: `docs/milestones/phase-1-sensitivity-analysis.md`
- Phase 2 search space: `tuning/spaces/phase2/space.json`
- Phase 2 runner: `tuning/scripts/run_optuna.py`
- Optuna SQLite: `tuning/runs/phase2/lti-phase2.db`
- experimentlog_v2.md entry: `2026-05-08 — Phase 2: Optuna tuning`
