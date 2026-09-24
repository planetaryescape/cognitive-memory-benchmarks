# Current Refresh 20260505 — Reproducibility Record

This is the repeatability map for the May 2026 current-refresh artifacts. `experimentlog.md` remains the full chronological audit log; this file is the condensed operator view. The active paper still uses these artifacts for LongMemEval-S, LTI-Bench, oracle, retrieval, and ablations; the LoCoMo headline is superseded by the Phase 5 v0.5 tuned-default run in `tuning/runs/phase5/v05_tuned/aggregate.json`.

Later milestones add mechanism evidence but do not change what this namespace means. Phase 8 narrows the LTI-Bench attribution by showing decay floors are not load-bearing on the 30-day setup. Phase 12/13/15 add off-spec local-model controls, retrieval-evidence controls, and a NaiveRAG baseline.

## Source of truth

| Field | Value |
|---|---|
| Output namespace | `current_sdk_20260505` |
| SDK | Editable local `../cognitive-memory-sdk/sdks/python`, package version `0.3.0`, commit `905aba7`, dirty worktree recorded in `experimentlog.md` |
| Extraction / answer model | `gpt-4o-mini` |
| Embedding model | `text-embedding-3-small` |
| LongMemEval / LTI judge | `gpt-4o-2024-08-06` |
| Retrieval scoring | `sim(m,q) * R(m)^alpha`, default `alpha=0.3` |
| Rerank shape | retrieve `topK * rerankFactor`, rerank, return `topK` |
| Normal search filter | excludes cold, superseded, stubs |
| Deep recall filter | includes cold + superseded, excludes stubs |

## Current-refresh artifacts and metrics

| Run | Artifact | Headline |
|---|---|---|
| CR-A LoCoMo | `locomo/results/current_sdk_20260505/primary_merged.json` | 44.8% overall F1; 48.5% multi-hop F1 |
| CR-B LongMemEval-S | `longmemeval/results/current_sdk_20260505/primary.json` | 71.6% task-averaged accuracy; 72.6% overall; 90.0% abstention |
| CR-C LTI-Bench v2 | `lti/results/current_sdk_20260505/run_l_v2.json` | 88.1% accuracy; 69.7% F1; 100% critical retention |
| CR-D Oracle evidence context condition | `locomo/results/current_sdk_20260505/oracle_ceiling_mem0.json` | 63.9% LoCoMo-scoring F1; 61.1% Mem0-scoring F1 |
| CR-E Decay comparison | `simulations/results/current_sdk_20260505/decay_comparison.json` | Power-law +4.6pp over exponential |
| CR-F Evidence recall | `locomo/results/current_sdk_20260505/evidence_recall.json` | Recall@60 35.6% |
| CR-G Efficiency | `locomo/results/current_sdk_20260505/efficiency_table.json` | Extraction dominates; vector search/scoring negligible |
| CR-H Feature activation | `locomo/results/current_sdk_20260505/feature_activation.json` | Activation counters for graph/validity/bridge |
| CR-I Judge reliability | `locomo/results/current_sdk_20260505/judge_reliability.json` | 94% raw agreement; Cohen's κ 0.879 |
| CR-J Ablations | `analysis/results/current_sdk_20260505/ablation_results.json` | Power-law +3.2pp; rerank +1.9pp; hybrid +1.7pp; graph +0.0pp |

## Commands

### CR-A LoCoMo

The canonical run used one shard per conversation:

```bash
for i in $(seq 0 9); do
  .venv/bin/python -m locomo.locomo_eval \
    --data locomo/data/locomo10.json \
    --adapter cognitive_memory \
    --model gpt-4o-mini \
    --prompt-mode mem0 \
    --dual-perspective \
    --deep-recall \
    --rerank --rerank-factor 3 \
    --top-k 60 \
    --use-judge \
    --quiet \
    --max-conversations $((i+1)) \
    --start-from $i \
    --output locomo/results/current_sdk_20260505/parallel/conv${i}.json \
    2> locomo/results/current_sdk_20260505/parallel/conv${i}.log &
done
wait
```

Merge output: `locomo/results/current_sdk_20260505/primary_merged.json`.

### CR-B LongMemEval-S

Initial command:

```bash
.venv/bin/python longmemeval/run_longmemeval.py \
  --data longmemeval/data/longmemeval_s_cleaned.json \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --top-k 20 \
  --deep-recall \
  --rerank --rerank-factor 3 \
  --max-workers 53 \
  --output longmemeval/results/current_sdk_20260505/primary.json
```

Resume command used after 80 completed questions:

```bash
.venv/bin/python longmemeval/run_longmemeval.py \
  --data longmemeval/data/longmemeval_s_cleaned.json \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --top-k 20 \
  --deep-recall \
  --rerank --rerank-factor 3 \
  --max-workers 53 \
  --start-from 80 \
  --output longmemeval/results/current_sdk_20260505/primary.json
```

Resume log: `longmemeval/results/current_sdk_20260505/primary_resume_80.log`.

### CR-C LTI-Bench v2

```bash
.venv/bin/python -m lti.lti_bench \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --judge-model gpt-4o-2024-08-06 \
  --quiet \
  --output lti/results/current_sdk_20260505/run_l_v2.json
```

### CR-D Oracle evidence context condition

```bash
.venv/bin/python locomo/oracle_ceiling.py \
  --data locomo/data/locomo10.json \
  --prompt-mode mem0 \
  --model gpt-4o-mini
```

### CR-E Decay comparison

```bash
.venv/bin/python simulations/decay_comparison.py \
  --data locomo/data/locomo10.json \
  --conv 0 \
  --model gpt-4o-mini
```

### CR-F to CR-I post-processing / judge reliability

```bash
.venv/bin/python locomo/evidence_recall.py \
  --data locomo/data/locomo10.json \
  --results locomo/results/current_sdk_20260505/primary_merged.json

.venv/bin/python locomo/efficiency_table.py \
  --results-dir locomo/results/current_sdk_20260505/parallel \
  --output locomo/results/current_sdk_20260505/efficiency_table.json

.venv/bin/python locomo/feature_activation.py \
  --results-dir locomo/results/current_sdk_20260505/parallel \
  --output locomo/results/current_sdk_20260505/feature_activation.json

.venv/bin/python locomo/judge_reliability.py \
  --results-dir locomo/results/current_sdk_20260505/parallel \
  --n 50 \
  --model gpt-4o-mini
```

### CR-J Ablations

```bash
.venv/bin/python analysis/ablation_runner.py \
  --data locomo/data/locomo10.json \
  --conv 0 \
  --model gpt-4o-mini
```

## Notes

- CR-B is complete and replaces the older March Run B number.
- Historical Run A-K/L/M labels still appear in old logs and plan docs. They are not active paper numbers unless explicitly marked historical.
- If a rerun changes a paper number, update `experimentlog.md`, this file, `docs/benchmarks-overview.md`, `paper/paper.tex`, and the public docs site in the same change.
