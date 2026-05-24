# Parameter Tuning Plan

## Why

Every value in `CognitiveMemoryConfig` (and the daemon's `LifecycleConfig` /
`handlers.rs` consts) was hand-picked from the paper or "feels right after
testing." None has been picked _because the benchmark said so._ The
benchmark suite already exists, our wallets aren't infinite, and the
fastest of those benchmarks (LTI-Bench v2) closes a tuning loop in ~5 min.
Time to use the loop.

The output of this plan is a single commit per repo:
- `cognitive-memory-sdk` — updated `CognitiveMemoryConfig` defaults and per-category `BASE_DECAY_RATES`.
- `cognitive-memory-daemon` — the same values mirrored in `LifecycleConfig::default()` and the consts in `crates/daemon/src/handlers.rs`.
- `cognitive-memory-benchmarks` — the trial harness + `tuning/runs/` history of every trial that produced the winning config.

## What's tunable

Three tiers by impact. Tune Tier 1 hardest, Tier 2 jointly, Tier 3 last.

### Tier 1 — decay shape

The retrieval scoring formula `score = sim × R^α` is the load-bearing
function. Wrong shape here, every other knob is downstream noise.

| Param | Current | Plausible range |
|---|---|---|
| `decay_model` | `Power` | `Exponential` \| `Power` |
| `power_decay_gamma` | 0.7 | 0.5 – 1.5 |
| `retrieval_score_exponent` (α) | 0.3 | 0.1 – 0.7 |
| `BASE_DECAY_RATES.episodic` | 45 d | 14 – 90 |
| `BASE_DECAY_RATES.semantic` | 120 d | 60 – 365 |
| `BASE_DECAY_RATES.core` | 120 d | 60 – ∞ |
| Regular floor (`f_m`) | 0.0 (daemon) / 0.02 (SDK) | 0.0 – 0.10 |
| Core floor | 0.6 | 0.4 – 0.8 |

### Tier 2 — boosting & strengthening

Determines how aggressively retrievals reinforce. Too low and trivial-fact
retention drops; too high and everything becomes core.

| Param | Current | Range |
|---|---|---|
| `direct_boost` | 0.10 | 0.05 – 0.25 |
| `associative_boost` | 0.03 | 0.01 – 0.10 |
| `spaced_rep_interval_days` | 7 | 3 – 21 |
| `max_spaced_rep_multiplier` | 2.0 | 1.5 – 3.5 |
| `association_strengthen_amount` | 0.10 | 0.05 – 0.25 |
| `association_decay_constant_days` | 90 | 30 – 180 |
| Stability baseline slope (`0.1 + 0.3·imp`) | 0.3 | 0.2 – 0.5 |

### Tier 3 — thresholds & lifecycle horizons

Lifecycle gates and ingest-time dispatch bands.

| Param | Current | Range |
|---|---|---|
| `core_access_threshold` | 10 | 3 – 20 |
| `core_stability_threshold` | 0.85 | 0.6 – 0.95 |
| `core_session_threshold` | 3 | 1 – 6 |
| `STABILITY_REINFORCEMENT_THRESHOLD` | 0.75 | 0.65 – 0.85 |
| `CONFLICT_SIMILARITY_THRESHOLD` | 0.85 | 0.80 – 0.95 |
| `SYNAPTIC_TAG_THRESHOLD` | 0.40 | 0.30 – 0.60 |
| `INGESTION_ASSOCIATION_BASE_WEIGHT` | 0.20 | 0.10 – 0.40 |
| `COLD_MIGRATION_DAYS` | 7 | 3 – 30 |
| `COLD_TTL_DAYS` | 180 | 60 – 365 |
| `CONSOLIDATION_RETENTION_THRESHOLD` | 0.20 | 0.10 – 0.30 |
| `CONSOLIDATION_GROUP_SIZE` | 5 | 3 – 10 |
| `CONSOLIDATION_SIM_THRESHOLD` | 0.70 | 0.50 – 0.85 |

**Excluded from tuning:** `min_bridge_edge_weight` (0.3), `max_bridge_paths`
(3), `procedural` decay rate (∞ by design).

## Phase 0 — expose every param to the harness

`CognitiveMemoryAdapter.__init__` in `shared/adapter.py` currently exposes
only `decay_model`, `graph_hops`, `hybrid_search`, and a hard-coded core
threshold lowering. Extend it:

```python
class CognitiveMemoryAdapter(MemoryAdapter):
    def __init__(
        self,
        # …existing args…
        config_overrides: Optional[Dict[str, Any]] = None,
    ):
        # …existing code…
        if config_overrides:
            for k, v in config_overrides.items():
                config_kwargs[k] = v
        config = CognitiveMemoryConfig(**config_kwargs)
```

Plus a parallel override for the per-category decay rates, which live in
`BASE_DECAY_RATES` in `types.py` (currently a module constant). Either
make it a `CognitiveMemoryConfig` field or thread the override through
the adapter via a setter called before construction.

`lti_bench.py` and `ablation_runner.py` get a `--config` flag that loads
a JSON or TOML file of overrides:

```bash
python lti/lti_bench.py --adapter cognitive_memory --config tuning/candidates/c0042.json
```

That single change unlocks the tuning loop. Half a day's work.

## Phase 1 — sensitivity analysis (1 day)

Before optimizing, find the params that actually move the score. One
factor at a time (OFAT). For each Tier 1+2 param, hold all others at
default, sweep through 5 values across its range, run LTI-Bench v2.
Record the LTI-Bench composite score for each.

Output: `tuning/sensitivity.csv` with columns `param, value, composite, decay_trivial, core_persistence, revival, multi_hop`.

Drop any param whose 5-value sweep moves the composite by < 2 percentage
points (within noise floor). Likely outcomes from prior knowledge:

- High influence (keep): `decay_model`, `α`, `BASE_DECAY_RATES.semantic`, `core_floor`, `direct_boost`, `core_session_threshold`.
- Medium influence: `power_decay_gamma`, `regular_floor`, `associative_boost`, `core_access_threshold`, `CONFLICT_SIMILARITY_THRESHOLD`.
- Probably negligible at LTI-Bench horizons: `COLD_TTL_DAYS`, `CONSOLIDATION_*` (consolidation is a slow-burn behavior; LTI-Bench's 30-day window may not even trigger it).

Cost: ~25 params × 5 values × 5 min = ~10 hours wall, ~$3 in API calls.
Run overnight.

## Phase 2 — inner-loop tuning (3 days)

Bayesian optimization (Optuna) over the high-influence params from
Phase 1. Search space is the multi-dim hypercube of Tier 1+2 winners
(typically 8-12 dimensions after Phase 1 prunes the rest).

Fitness function (one scalar):

```python
def lti_bench_fitness(result: dict) -> float:
    # LTI-Bench v2 reports four sub-scores. Weight them by paper claims:
    # - decay_trivial (Table 9): 100% target, weight 0.20
    # - core_persistence (Table 9): 100% target, weight 0.30
    # - revival (Table 9): 60% target, weight 0.30
    # - multi_hop (the hard one): variable, weight 0.20
    return (
        0.20 * result["decay_trivial"] / 100.0
      + 0.30 * result["core_persistence"] / 100.0
      + 0.30 * result["revival"] / 100.0
      + 0.20 * result["multi_hop"] / 100.0
    )
```

This is a soft-Pareto. If you want something stricter, switch to
multi-objective Optuna with the four sub-scores and pick from the
Pareto frontier at Phase 4.

Trials: 150. At 5 min each = 12.5 hours wall. ~$15 API.

Output: `tuning/runs/lti/{trial-id}/{config.json,score.json,trace.log}`
plus `tuning/runs/lti/study.db` (Optuna SQLite). Top 5 candidates by
composite score get promoted to Phase 3.

```bash
python tuning/run_optuna.py \
    --study lti-v1 \
    --benchmark lti \
    --n-trials 150 \
    --space tuning/spaces/tier1_tier2.toml
```

## Phase 3 — decay-shape cross-check (1 day)

LTI-Bench is synthetic and could overfit to its specific test patterns.
The decay-comparison run (~16-30 min) puts the candidate decay shapes
through a different distribution. (If "decay_comparison" doesn't exist
as a single harness today, build it as a stripped-down LTI-Bench variant
that only exercises retention questions over a 90-day horizon.)

Run each of the 5 LTI-winning configs through decay_comparison once.
Drop any candidate whose decay-comparison score is more than 5pp below
its LTI-Bench score — that's overfitting to LTI's specific timeline.

~2.5 hours wall. ~$2.

Survivors (typically 2-3) advance to Phase 4.

## Phase 4 — LoCoMo conv0 reality check (12 hours)

LoCoMo is real conversational data. If a config wins on LTI-Bench but
loses on LoCoMo conv0, it's a synthetic artifact. The user's note is
the actionable rule: **don't promote a config until LoCoMo conv0
agrees**.

For each of the 2-3 Phase 3 survivors, run `ablation_runner.py` with
`adapter_kwargs={"config_overrides": cfg, "deep_recall": True, "dual_perspective": True}`
on conv 0. Compare multi-hop F1 to the current default's conv0 result
(baseline must be re-run with current defaults at the same seed for
fair comparison).

~3 hours wall, ~$5.

Drop any candidate whose multi-hop F1 is below baseline. Often this
is 0 of the survivors (typical case), in which case go back to Phase 2
with the LTI loss function reweighted toward multi-hop. If exactly one
survives, it's the winner. If more than one, run Phase 5 on the top 2.

## Phase 5 — full LoCoMo final (2 hours per candidate)

Single run on the lone (or top-2) survivor. ~$10. Promote if and only
if multi-hop F1 ≥ baseline AND headline F1 within 1pp of baseline.

If nothing beats baseline: log the negative result, document the
parameter sensitivity findings (still useful), and stop. Keep the
current defaults. The point of an empirical loop is also to confirm
when the heuristic was already good enough.

## Phase 6 — ship the tuned config

Single commit per repo:

```
crates/lifecycle/src/lib.rs       — LifecycleConfig::default() new values
crates/daemon/src/handlers.rs     — STABILITY_*_THRESHOLD, CONFLICT_*, etc.
sdks/python/src/cognitive_memory/types.py
                                   — CognitiveMemoryConfig defaults + BASE_DECAY_RATES
sdks/typescript/src/types.ts       — same
```

Commit message body lists: which param changed, old value, new value,
LTI-Bench delta, decay_comparison delta, LoCoMo conv0 delta, full
LoCoMo delta. Link to `tuning/runs/lti/study.db` for full provenance.

Then run the existing Rust workspace test suite + the long-horizon-v3
script to confirm the parity tests still pass with the new defaults.
The decay e2e tests intentionally pin stability=0.5 explicitly so they
don't break when defaults change — but spot-check.

## Trial harness — concrete shape

`tuning/run_optuna.py`:

```python
import optuna, json, subprocess, pathlib, time

SPACE = {
    "decay_model": ("categorical", ["power", "exponential"]),
    "retrieval_score_exponent": ("float", 0.1, 0.7),
    "power_decay_gamma": ("float", 0.5, 1.5),
    "direct_boost": ("float", 0.05, 0.25),
    "associative_boost": ("float", 0.01, 0.10),
    "core_session_threshold": ("int", 1, 6),
    "core_access_threshold": ("int", 3, 20),
    "core_stability_threshold": ("float", 0.6, 0.95),
    # ...
}

def objective(trial):
    cfg = {}
    for name, spec in SPACE.items():
        kind = spec[0]
        if kind == "float":
            cfg[name] = trial.suggest_float(name, spec[1], spec[2])
        elif kind == "int":
            cfg[name] = trial.suggest_int(name, spec[1], spec[2])
        elif kind == "categorical":
            cfg[name] = trial.suggest_categorical(name, spec[1])

    cfg_path = pathlib.Path(f"tuning/runs/lti/{trial.number:04d}/config.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2))

    out = cfg_path.parent / "result.json"
    subprocess.run([
        ".venv/bin/python", "lti/lti_bench.py",
        "--adapter", "cognitive_memory",
        "--config", str(cfg_path),
        "--output", str(out),
        "--quiet",
    ], check=True)
    result = json.loads(out.read_text())
    return lti_bench_fitness(result)

study = optuna.create_study(
    study_name="lti-v1",
    storage="sqlite:///tuning/runs/lti/study.db",
    direction="maximize",
    load_if_exists=True,
)
study.optimize(objective, n_trials=150, show_progress_bar=True)
```

Each trial is fully provenanced — the SQLite `study.db` lets you
resume, inspect, or do post-hoc analysis (`optuna-dashboard`).

## Risks & guardrails

| Risk | Mitigation |
|---|---|
| Overfitting to LTI-Bench (synthetic) | Phase 3 + Phase 4 reality checks |
| Daemon ≠ SDK after porting tuned values | Run Rust workspace tests + long-horizon-v3 with new defaults; if parity test fails, the daemon's port has a bug — fix daemon, not config |
| LLM-judge variance inflates score noise | Pin judge model = `gpt-4o-2024-08-06`, pin temperature 0, pin seed |
| API spend runs away | Hard cap: `OPENAI_TOTAL_BUDGET=20` env var checked by harness; abort study above |
| Different categories want different optimal α | Two-level fit: per-category α first, then global params; or accept α as global and let `BASE_DECAY_RATES` absorb category differences |
| Tuned values regress on LongMemEval-S | Annual re-tune or scheduled re-run; LongMemEval is too expensive for tuning loop but should be reviewed before any v0.2 release |

## Wall + cost budget (worst case)

| Phase | Wall | API |
|---|---|---|
| Phase 0 (harness extension) | 4 h dev | $0 |
| Phase 1 (sensitivity) | 10 h | $3 |
| Phase 2 (Optuna 150 trials) | 12.5 h | $15 |
| Phase 3 (decay-comparison) | 2.5 h | $2 |
| Phase 4 (LoCoMo conv0) | 3 h | $5 |
| Phase 5 (full LoCoMo) | 4 h | $10 |
| Phase 6 (port + parity) | 2 h dev | $0 |
| **Total** | **~38 h wall, 6 h dev** | **~$35** |

Across a single weekend if you let Phase 1 + 2 run overnight on
weekend nights. Fast iteration if you stop after Phase 2 (~$18, 1
day) and accept LTI-Bench as the ground truth — but the user's note
is right: don't.

## Open questions

- Does a "decay_comparison" benchmark exist as its own harness today,
  or is it a slice of LTI-Bench? If the latter, Phase 3 collapses into
  Phase 2 and we go straight to LoCoMo at Phase 3.
- Pareto-multi-objective vs single-scalar fitness: scalar is faster
  but may hide cases where one mechanism trades off against another.
  Recommend scalar for v1, switch to multi-objective if Phase 4 keeps
  rejecting LTI winners.
- Should we tune separately per benchmark distribution (LoCoMo-tuned
  vs LongMemEval-tuned vs general)? Probably not — single global
  config keeps the daemon's defaults coherent. If a deployment needs
  workload-specific tuning, that's a `~/.config/cognitive-memory/config.toml`
  override, not a default change.
