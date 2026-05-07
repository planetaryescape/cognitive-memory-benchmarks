# Tuning harness

Scaffolding for parameter-tuning experiments on the `cognitive-memory`
SDK and daemon. Phase 0 of the parent plan
(`docs/parameter-tuning-plan.md`) ships the harness; phases 1-5 fill it
with sensitivity studies, Optuna runs, and final defaults.

## Directory map

```
tuning/
├── README.md                  # this file
├── runs/                      # one subdirectory per trial + jsonl log
│   ├── runs.jsonl             # append-only one-line summary per trial
│   └── <bench>-NNNN/          # per-trial artifacts
│       └── run-NN/            # per sub-run (for median-of-N)
│           ├── result.json    # harness output
│           ├── stdout.log
│           └── stderr.log
├── spaces/                    # JSON config files defining a trial
│   ├── baseline.json          # 0g determinism baseline (no overrides)
│   └── smoke_alpha_0_5.json   # 0g override propagation check
└── scripts/
    └── run_trial.py           # one-shot wrapper; appends to runs.jsonl
```

## Running a trial

```bash
.venv/bin/python tuning/scripts/run_trial.py \
    --benchmark lti \
    --config tuning/spaces/smoke_alpha_0_5.json \
    --phase phase0_smoke \
    --repeat 3
```

`--repeat 3` runs the trial three times so the loader can compute
median + stddev (the determinism gate from Phase 0g). Sub-run
artifacts are stored in
`tuning/runs/lti-NNNN/run-{00,01,02}/`. The aggregated row appears
in `tuning/runs/runs.jsonl`.

To pass extra args to the underlying benchmark, separate them with `--`:

```bash
.venv/bin/python tuning/scripts/run_trial.py \
    --benchmark lti \
    --config tuning/spaces/baseline.json \
    --phase phase0_smoke \
    -- --quiet --judge-model gpt-4o-2024-08-06
```

## Trial config schema

JSON, four optional blocks:

```json
{
  "surface": "sdk",
  "adapter": {
    "deep_recall": true,
    "rerank": false,
    "graph_hops": 1
  },
  "config_overrides": {
    "retrieval_score_exponent": 0.5,
    "direct_boost": 0.15,
    "decay_model": "power"
  },
  "base_decay_rates": {
    "semantic": 60,
    "episodic": 30
  }
}
```

- `surface` — `"sdk"` (in-process, default, fast) or `"daemon"` (Unix
  socket reality check). CLI flag `--surface` overrides this field.
- `adapter` — kwargs forwarded to `CognitiveMemoryAdapter.__init__`.
- `config_overrides` — arbitrary `CognitiveMemoryConfig` fields. The
  adapter merges these atop its baseline kwargs; explicit kwargs
  (`decay_model`, `hybrid_search`) win on collision.
- `base_decay_rates` — hoisted shorthand for
  `config_overrides.base_decay_rates` (per-category β_c override).
  Top-level wins over a same-named entry under `config_overrides`.

See `shared/trial_config.py` for the loader and
`shared/tests/test_trial_config.py` for the contract.

## Provenance chain

Every Phase 1+ tuning conclusion ("we set α=0.42 because…") must be
defensible eight months later. Four levels of logging:

1. **Per-trial artifacts** — `tuning/runs/<trial_id>/run-NN/{result.json, stdout.log, stderr.log}`.
2. **runs.jsonl** — append-only, one line per trial, structured for grep/jq.
3. **experimentlog_v2.md** — narrative, per-day or per-phase. Links
   trial IDs to decisions.
4. **Milestone notes** — `docs/milestones/phase-N-*.md`. Phase summary
   at end of each phase: what worked, what didn't, falsified
   hypotheses, links every cited trial ID.

`runs.jsonl` line schema (Phase 0):

```json
{
  "trial_id": "lti-0001",
  "ts_utc": "2026-05-07T20:00:00Z",
  "phase": "phase0_smoke",
  "benchmark": "lti",
  "surface": "sdk",
  "config": { ... full JSON config ... },
  "sub_runs_count": 3,
  "median": { "overall_f1": 0.872, "composite": 0.870 },
  "stddev": { "overall_f1": 0.004, "composite": 0.005 },
  "git_sha": "f5ba541",
  "wall_seconds": 936
}
```

## Daemon-surface trials

When `--surface daemon`, the adapter constructs a `RemoteAdapter`
that opens a Unix socket connection to a running `cm-daemon`. Two
prerequisites:

1. The daemon must be running (`cargo run -p cognitive-memory-daemon`
   or the installed binary).
2. To override `[lifecycle]` parameters per-trial, the trial must
   write `~/.config/cognitive-memory/config.toml` with the desired
   `[lifecycle.base_decay_rates]` overrides, then `pkill cm-daemon`
   so the next adapter call auto-spawns a daemon with the new
   config. The plan calls for an IPC `Reload` op as a Phase 4
   optimization; for Phase 0 the restart is acceptable (~3s embedding
   model reload, < 1% of trial wall time).

## Phase 1 — sensitivity analysis

OFAT (one-factor-at-a-time) sweeps over Tier 1+2 parameters.
Defined in `tuning/spaces/phase1/sweeps.json`; runner is
`tuning/scripts/run_phase1.py`.

```bash
# Preview the sweep plan (no API calls)
.venv/bin/python tuning/scripts/run_phase1.py \
    --spec tuning/spaces/phase1/sweeps.json --dry-run

# Run a single param's sweep (smoke test before committing budget)
.venv/bin/python tuning/scripts/run_phase1.py \
    --spec tuning/spaces/phase1/sweeps.json \
    --params retrieval_score_exponent

# Full Phase 1 sweep (141 sub-runs at n=3, ~12 h wall, ~$14)
.venv/bin/python tuning/scripts/run_phase1.py \
    --spec tuning/spaces/phase1/sweeps.json
```

Output: `tuning/runs/phase1_sensitivity.csv`. Columns:
`param_path, value, is_default, n_repeats, trial_id, median.<key>, stddev.<key>`
for each `score_keys` entry. Drop any param whose 5-value sweep moves
the composite by < the noise floor (Phase 0g found ~1.5pp f1 stddev
on LTI-Bench at n=3 — anything below ~3pp range is not separable).

**Phase 0g caveat:** sensitivity on LTI-Bench may be hard to
distinguish from LLM-judge noise at the 42-question size. Consider
running Phase 1 on LongMemEval-S (500 questions, expected ~0.3pp
stddev) instead — change `benchmark` in sweeps.json and add LongMemEval
to `BENCHMARKS` in `run_trial.py`.

## See also

- `docs/parameter-tuning-plan.md` — parent plan, six-phase ladder.
- `~/.claude/plans/now-create-a-plan-validated-yao.md` — Phase 0
  detailed plan that produced this scaffolding.
- `experimentlog_v2.md` — narrative experiment log.
