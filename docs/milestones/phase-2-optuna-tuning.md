# Phase 2 — Optuna inner-loop tuning (in progress)

**Started:** 2026-05-08T09:41 BST
**Sweep status (last refresh 2026-05-08T19:01 BST):** 40 of 50 trials complete (80%); trial 40 in progress
**Per-trial pace (measured):** ~13.9 min/trial
**Projected end:** ~21:21 BST tonight
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

**Best so far:** Trial 23, fitness=0.6531 (associative_boost=0.078, β_semantic=367, core_session_threshold=2). Improvement over previous tied-best is **+0.06pp — within the 3-question marginal-judge noise floor identified in Phase 2.5**. Treat as not-meaningfully-better.

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
| 9 | 0.0487 | 190.2 | 3 | 0.6525 |
| 10 | 0.0458 | 289.6 | 3 | 0.6489 |
| 11 | 0.0403 | 397.3 | 2 | 0.6508 |
| 12 | 0.0554 | 396.5 | 3 | 0.6496 |
| 13 | 0.0514 | 280.8 | 2 | 0.6491 |
| 14 | 0.0639 | 345.5 | 3 | 0.6181 ← low-cluster despite TPE-favoured region |
| 15 | 0.0986 | 366.4 | 2 | 0.6491 |
| 16 | 0.0503 | 311.9 | 2 | 0.6525 |
| 17 | 0.0483 | 313.8 | 3 | 0.6155 ← assoc≈0.05 BUT low cluster |
| 18 | 0.0420 | 269.0 | 2 | 0.6477 |
| 19 | 0.0535 | 313.2 | 3 | 0.6514 |
| 20 | 0.0475 | 185.7 | 2 | 0.6491 |
| 21 | 0.0676 | 368.9 | 2 | 0.6491 |
| 22 | 0.0562 | 306.5 | 2 | 0.6488 |
| 23 | 0.0782 | 367.1 | 2 | **0.6531** ← +0.06pp over tied-best (within noise) |
| 24 | 0.0802 | 255.5 | 3 | 0.6457 |
| 25 | 0.0824 | 352.8 | 2 | 0.6491 |
| 26 | 0.0752 | 324.2 | 2 | 0.6491 |
| 27 | 0.0649 | 380.4 | 3 | 0.6491 |
| 28 | 0.0904 | 299.2 | 2 | 0.6459 |
| 29 | 0.0856 | 332.9 | 2 | 0.6459 |
| 30 | 0.0439 | 275.6 | 3 | 0.6181 ← cst=3 low cluster again |
| 31 | 0.0755 | 379.7 | 2 | 0.6491 |
| 32 | 0.0504 | 359.6 | 2 | 0.6491 |
| 33 | 0.0581 | 324.6 | 2 | 0.6487 |
| 34 | 0.0707 | 381.0 | 1 | 0.6527 ← first cst=1 sample in a while; high cluster |
| 35 | 0.0617 | 384.0 | 1 | 0.6491 |
| 36 | 0.0769 | 346.9 | 1 | 0.6491 |
| 37 | 0.0718 | 232.9 | 1 | 0.6491 |
| 38 | 0.0648 | 259.6 | 1 | 0.6509 |
| 39 | 0.0677 | 244.0 | 1 | 0.6491 |
| 40 | _running…_ | | | |

**cst breakdown after 30 trials:**

| cst | high cluster | low cluster | hit rate | note |
|---|---|---|---|---|
| 1 | 5 | 1 | 5/6 = 83% | n=6 |
| 2 | 13 | 1 | **13/14 = 93%** | **cleanest** |
| 3 | 6 | 3 | 6/9 = 67% | trailing |

cst=2 is now the consistently-cleanest at n=14. cst=3 trailing
holds. Phase 1 OFAT had cst=1/2/3 all flat — joint search
surfaces a real interaction effect.

**Distinct fitness values:** 17 across 30 trials. The bench is
emitting a discrete set; tied configs are common. Trial 23's
"best" of 0.6532 is +0.06pp above the next-tier 0.6525 cluster
— within the marginal-question coin flip identified in Phase 2.5.

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

## Phase 2.5 — per-question variance analysis (DONE, $0)

**Finding:** the bimodal-cluster mystery has a concrete source.
Of LTI-Bench's 42 questions, **only 7 are marginal**; **35 are
stable** (judge always agrees with itself across replicates).
The composite-variance is dominated by 3 questions:

| variance | subscore | correct rate | flips | question |
|---|---|---|---|---|
| 0.959 | revival | 60% (130/216) | 89 | "Was there anything about the weather I mentioned once?" |
| 0.955 | revival | 39% (85/216) | 105 | "Did I ever mention traffic?" |
| 0.826 | decay_trivial | 71% (153/216) | 70 | "What did I have for lunch on day 3?" |

(216 replicates = 216 result.json files across Phase 0g + 1 + first
20 of Phase 2. Analyzer at `tuning/scripts/analyze_question_variance.py`,
output at `tuning/runs/phase2.5/question_variance.csv`.)

**Implications:**

1. **Revival is over-represented as a noise source.** Weight 0.30
   in the fitness composite × 2 of 3 marginal questions land
   there. A trial that wins/loses revival flips composite by
   roughly ±2pp on its own.
2. **TPE was effectively flipping a 3-question coin per trial.**
   Param effects ≤ 3pp can't escape this floor.
3. **A `conflict` question is a stable engine weakness, not
   variance.** "When is the Helios project deadline?" — model
   answers wrong 93% of the time (15/216 correct). Real bug or
   real bench miscalibration; not noise.
4. **Phase 6 / paper recommendations:**
   - LTI-Bench v3 should reword or remove the 3 marginal questions
     (they're "open-recall trivia" wording — too easy for judge to
     score either way).
   - Or expand the bench from 42 → 100+ questions to dilute
     individual-question weight.
   - Re-judge just the 3 marginal questions with a stronger judge
     (gpt-4o vs gpt-4o-2024-08-06) — cheap fix.
5. **For the rest of Phase 2:** the remaining 30 trials will keep
   hitting the same 3-question coin-flip. Don't expect new
   information beyond the existing best (0.6525).

### Originally-planned follow-ups (now reprioritized)

This step (per-question variance analysis) was the highest-leverage
of the four post-sweep ideas. The other three are now triaged:

- **Judge-variance baseline (~$2):** less needed. We already know
  the noise floor and its mechanism.
- **Top-5 confirmation re-run (~$5):** still useful — re-run top-5
  trials at n=5 to see if rank order is stable. But the answer is
  *predictable from the analysis above*: top trials within ~2pp of
  each other will be order-shuffled by the 3-question coin-flip.
- **Switch sampler (CmaEsSampler/BoTorchSampler):** unlikely to
  help — sampler smartness can't beat bench resolution.

### What we now know vs. autoresearch's pitch

The autoresearch research-agent flagged the right concern (greedy-
keep amplifies judge noise; need significance machinery). The
analyzer above provides exactly that significance read — concretely,
*which question's judge-call you'd be greedy-keeping on*. Useful
artifact regardless of whether autoresearch ever ships into the
pipeline.



References:
- `autoresearch` repo + discussions:
  https://github.com/karpathy/autoresearch
  https://github.com/karpathy/autoresearch/issues/131 (no seed
  engineering planned)
  https://github.com/karpathy/autoresearch/discussions/293 (no
  built-in HPO planned)
- LLMs vs classical HPO benchmark:
  https://arxiv.org/html/2603.24647v3
- Optuna noisy-objective samplers:
  https://optuna.readthedocs.io/

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
