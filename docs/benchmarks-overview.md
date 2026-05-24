# Benchmarks Overview — Methodology, Runs, Results

The canonical record is split across [`experimentlog_v2.md`](../experimentlog_v2.md) for the Phase 0g-5 tuning campaign and [`experimentlog.md`](../experimentlog.md) for the May 2026 current-refresh artifacts. This doc maps which artifacts are active, what each run measures, and how to reproduce the current paper numbers.

Active LoCoMo headline: `tuning/runs/phase5/v05_tuned/aggregate.json`.

Active current-refresh namespace for LongMemEval-S, LTI-Bench, oracle, retrieval, and ablations: `current_sdk_20260505`.

Historical `v6/` artifacts remain on disk for provenance only.

## 1. Active run registry

| Run | Benchmark | Status | Active artifact | What it measures |
|---|---|---|---|---|
| P5-A | LoCoMo v0.5 tuned defaults | COMPLETE | `tuning/runs/phase5/v05_tuned/aggregate.json` | Current paper LoCoMo headline |
| P5-B | LoCoMo v0.4 paper-faithful baseline | COMPLETE | `tuning/runs/phase5/v04_baseline/aggregate.json` | Head-to-head default comparison |
| CR-A | LoCoMo | COMPLETE | `locomo/results/current_sdk_20260505/primary_merged.json` | Multi-session conversational QA F1 |
| CR-B | LongMemEval-S | COMPLETE | `longmemeval/results/current_sdk_20260505/primary.json` | Long-horizon memory across 6 task types |
| CR-C | LTI-Bench v2 | COMPLETE | `lti/results/current_sdk_20260505/run_l_v2.json` | Controlled 30-day lifecycle behavior |
| CR-D | Oracle evidence context condition | COMPLETE | `locomo/results/current_sdk_20260505/oracle_ceiling_mem0.json` | What is possible if retrieval is perfect |
| CR-E | Decay comparison | COMPLETE | `simulations/results/current_sdk_20260505/decay_comparison.json` | Power-law vs exponential, conv 0 |
| CR-F | Evidence Recall@k | COMPLETE | `locomo/results/current_sdk_20260505/evidence_recall.json` | Retrieval evidence coverage |
| CR-G | Efficiency table | COMPLETE | `locomo/results/current_sdk_20260505/efficiency_table.json` | Per-stage timings |
| CR-H | Feature activation | COMPLETE | `locomo/results/current_sdk_20260505/feature_activation.json` | Graph/validity/bridge activation |
| CR-I | Judge reliability | COMPLETE | `locomo/results/current_sdk_20260505/judge_reliability.json` | Inter-prompt agreement |
| CR-J | Ablations | COMPLETE | `analysis/results/current_sdk_20260505/ablation_results.json` | Per-feature deltas on conv 0 |

## 2. Common setup

| Knob | Value |
|---|---|
| Extraction model | `gpt-4o-mini` |
| Answer model | `gpt-4o-mini` |
| Embedding model | `text-embedding-3-small` |
| LongMemEval/LTI judge | `gpt-4o-2024-08-06` |
| SDK provenance | Editable local SDK, recorded per run in `experimentlog.md` |
| Retrieval semantics | `search()` canonical; normal search excludes cold/superseded/stubs; deep recall includes cold + superseded, excludes stubs |
| Scoring | `score(m,q) = sim(m,q) * R(m)^alpha`, default `alpha=0.3` |
| Rerank | fetch `topK * rerankFactor`, rerank, return `topK` |

## 3. Headlines

### LoCoMo (Phase 5 headline; CR-A previous baseline)

- **Overall F1: 46.2%**
- **Multi-hop F1: 51.3%** (~1.8x Mem0's reported 28.4%)
- Phase 5 v0.4 paper-faithful baseline: 44.4% overall F1, 48.5% multi-hop F1
- CR-A current-refresh baseline remains on disk: 44.8% overall F1, 48.5% multi-hop F1
- 10 conversations; 1540 category 1-4 QA used for the standard LoCoMo result
- Phase 5 artifact: `tuning/runs/phase5/v05_tuned/aggregate.json`
- Production flags: `top-k 60`, dual-perspective ingestion, deep recall, rerank factor 3, Mem0-style answer prompt, judge enabled

### LongMemEval-S (CR-B)

- **Task-averaged accuracy: 71.6%**
- **Overall accuracy: 72.6%**
- **Abstention accuracy: 90.0%**
- 500 questions, 6 task types
- Per-task accuracy:
  - single-session-user: 85.7%
  - single-session-assistant: 76.8%
  - single-session-preference: 46.7%
  - multi-session: 69.9%
  - temporal-reasoning: 64.7%
  - knowledge-update: 85.9%
- The run completed the first 80 questions, fixed a thread-safety patch bug, then resumed from `--start-from 80`.

### LTI-Bench v2 (CR-C)

- **Accuracy: 88.1%**
- **F1: 69.7%**
- **Critical fact retention: 100%**
- 28 facts, 28 daily sessions, 42 probes, 8 probe types
- See [`lti-bench.md`](./lti-bench.md) for scenario details.

### Derived analyses

- Oracle evidence context condition: **63.9%** LoCoMo-scoring F1 / **61.1%** Mem0-scoring F1.
- Evidence Recall@60: **35.6%**.
- Isolated decay-shape sensitivity: power-law **29.5%** vs exponential **25.0%** on conv 0, **+4.6pp**.
- Ablation runner, conv 0: power-law **+3.2pp**, rerank **+1.9pp**, hybrid search **+1.7pp**, graph expansion **+0.0pp**.
- Judge reliability: **94%** raw agreement, Cohen's κ **0.879**.

## 4. Reproduction commands

### LoCoMo CR-A

Sequential reproduction:

```bash
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
  --output locomo/results/current_sdk_20260505/primary.json
```

The canonical run used 10 conversation shards, one per process:

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

The merged artifact is `locomo/results/current_sdk_20260505/primary_merged.json`.

### LongMemEval-S CR-B

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

Resume command used after the first 80 questions:

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

### LTI-Bench CR-C

```bash
.venv/bin/python -m lti.lti_bench \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --judge-model gpt-4o-2024-08-06 \
  --quiet \
  --output lti/results/current_sdk_20260505/run_l_v2.json
```

### Derived runs

```bash
.venv/bin/python locomo/oracle_ceiling.py \
  --data locomo/data/locomo10.json \
  --prompt-mode mem0 \
  --model gpt-4o-mini

.venv/bin/python simulations/decay_comparison.py \
  --data locomo/data/locomo10.json \
  --conv 0 \
  --model gpt-4o-mini

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

.venv/bin/python analysis/ablation_runner.py \
  --data locomo/data/locomo10.json \
  --conv 0 \
  --model gpt-4o-mini
```

## 5. Cost notes

Order-of-magnitude API costs:

| Run | Approx wall |
|---|---:|
| CR-A LoCoMo full, parallel | ~2h |
| CR-B LongMemEval-S | 52328s across original + resumed run |
| CR-C LTI-Bench v2 | ~5 min |
| CR-D oracle evidence context condition | 1391s |
| CR-E decay comparison | ~30 min |
| CR-F/G/H post-processing | <5 min each |
| CR-I judge reliability | <2 min |
| CR-J ablations | ~2.5h |

## 6. Not in the active benchmark suite

- LongMemEval-M and LongMemEval-Oracle.
- MemoryBench 2025.
- Full in-house NaiveRAG LoCoMo run.
- Cross-model runs with Claude, Gemini, or Llama answer models.
- Multi-seed runs.

These are paper limitations or future work, not hidden results.
