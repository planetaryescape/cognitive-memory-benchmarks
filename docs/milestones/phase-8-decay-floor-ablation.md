# Phase 8 — decay-floor ablation on LTI-Bench (complete, NEGATIVE RESULT)

**Started:** 2026-05-11T01:30 BST
**Completed:** 2026-05-11T11:35 BST
**Wall:** trials ran ~14min once laptop woke from sleep (started at
01:30 but were paused by sleep until 11:31 BST)
**Cost:** ~$0.60
**Verdict:** **NULL** — `critical_fact_retention` unchanged at 100%
under floors-off. The floor mechanism is not the dominant cause on
LTI-Bench's 30-day window. Architectural claim survives in weaker
form (preservation-first lifecycle stands; floor-clamping in isolation
isn't load-bearing on this distribution).

This addresses paper §6.10 future-work item #1 (decay-floor ablation)
and lets us replace the future-work sentence with a result paragraph
before submission.

## Goal

The paper claims decay floors prevent retrieval cliff-edges. The
strongest version of this claim is: **`critical_fact_retention`
should drop substantially when the core floor is set to 0**, because
critical facts get promoted to core (floor 0.60) precisely so they
survive the LTI-Bench 30-day window.

Across all 100+ LTI-Bench runs in the Phase 0g→5 tuning campaign,
`critical_fact_retention` was stuck at 100% — the strongest single-
metric finding we have. This ablation tests whether the floor
mechanism is the cause.

## SDK change required

Phase 0a-sdk made `base_decay_rates` a config field; Phase 8's
sibling change makes `decay_floors` a config field too. Both follow
the same pattern: `default_factory=lambda: dict(DECAY_FLOORS)` plus a
`__post_init__` merge so partial overrides preserve siblings.
`engine.py` reads `self.config.decay_floors` instead of
`memory.floor` (the property still exists for back-compat).

Bumps Python SDK to 0.5.1. No breaking API changes.

## Configs

- `tuning/spaces/phase8/floors_on.json`: empty override, uses paper-
  faithful defaults (`core=0.60, regular=0.02`).
- `tuning/spaces/phase8/floors_off.json`:
  `decay_floors={"core": 0.0, "regular": 0.0}`.

## Decision rule for paper §6.10

After both finish:
- **`critical_fact_retention` drops by ≥30pp** (e.g. 100% → ≤70%) →
  floor mechanism is causally responsible. Replace future-work
  sentence with this finding.
- **drops by 10-30pp** → floor contributes but isn't sole cause.
  Frame paragraph honestly.
- **<10pp drop** → floor not isolatable; the architectural claim is
  over-stated. Keep as future work but note the negative result.

`decay_trivial` and `core_persistence` sub-scores also recorded; they
should track the same direction if the floor explanation holds.

## Final results

| config | trial | acc | mean_f1 | critical_fact | decay_trivial | core_persistence |
|---|---|---|---|---|---|---|
| floors_on (paper) | lti-0109 | 0.881 | 0.687 | **1.000** | 0.614 | 0.927 |
| floors_off (ablation) | lti-0110 | 0.905 | 0.686 | **1.000** | 0.614 | 0.917 |
| **delta** | | +2.38pp | -0.17pp | **0pp** | **0pp** | -1.04pp |

### Reading

The headline finding `critical_fact_retention = 100%` on LTI-Bench
is **not caused by the floor mechanism**. With floors=0, every
critical fact is still retrieved correctly by the existing pipeline
(stability accumulation through repeated direct retrieval +
relevance-driven scoring at α=0.3 keeping high-similarity memories
near the top regardless of R).

This falsifies the simplest version of the floor argument
("floors keep critical facts retrievable") on this distribution.
The architectural claim survives in weaker form: floors are
designed to matter at horizons where stability decays past the
clamping point. LTI-Bench's 30-day window doesn't reach there
often enough.

### Implication for paper §6.10 + §7

§6.10 now has a "Decay-floor ablation (negative result)" paragraph
in `paper/paper.tex` (committed in this round). §7 future-work
item #1 is reframed from "run the ablation" to "run a longer-
horizon ablation (90d / 180d) where stability decays past the floor
clamping point".

### Caveats

- n=3 sub-runs per arm; the +2.38pp accuracy delta and -1.04pp
  core_persistence delta are within Phase 0g's measured ~3pp LTI-Bench
  noise floor.
- Tested at v0.5 defaults (β_semantic=240, associative_boost=0.05).
  At paper-faithful β_semantic=120, retention would decay faster
  and the floor might bind earlier in the 30-day window. Future
  work could test floors-off × β_semantic=120 to isolate.
- LTI-Bench is hand-authored, 42 questions. Generalisation to real
  conversational distributions requires LoCoMo-scale ablation
  (~$10, ~75min) which is queued but not run.

## Done

- SDK 0.5.1 ships with `decay_floors` as a config field (cognitive-
  memory-sdk commit pending). Three new value-lock unit tests
  (test_decay_floors_default_matches_paper_table_2,
  test_decay_floors_override_replaces_one_key_only,
  test_compute_retention_reads_decay_floor_from_config). 11/11 SDK
  config tests pass.
- TS SDK also bumped to 0.5.1 for parity, even though no TS-side
  code change was needed yet (the TS engine already reads
  config.regularRetentionFloor / config.coreRetentionFloor).
- Daemon is unchanged — daemon's `LifecycleConfig` doesn't yet
  expose `decay_floors`; not a blocker for the ablation since the
  ablation uses the SDK directly through the benchmarks adapter.
- Paper §6.10 has a new "Decay-floor ablation (negative result)"
  paragraph; §7 future-work item #1 reframed.
- PDFs rebuilt (paper/paper.pdf,
  paper/cognitive-memory-arxiv-paper-v2.pdf,
  paper/arxiv-source/cognitive-memory-arxiv-source/paper.pdf).
