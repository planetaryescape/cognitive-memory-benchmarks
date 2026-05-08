# Phase 2 — Optuna inner-loop tuning (in progress)

**Started:** 2026-05-08T09:41 BST
**Sweep status (last refresh 2026-05-08T09:57 BST):** 1 of 50 trials complete; trial 1 in progress
**Per-trial pace (measured):** ~14.5 min/trial → projected ~12h total wall
**Projected end:** ~21:41 BST tonight
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

**Best so far:** Trial 0, fitness=0.6491 (Phase 1 OFAT baseline ≈ 0.69; the search hasn't yet found a config that beats it, but TPE only just started)

| trial | associative_boost | β_semantic | core_session_threshold | fitness |
|---|---|---|---|---|
| 0 | 0.0864 | 331.6 | 1 | 0.6491 |
| 1 | _running…_ | | | |

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
