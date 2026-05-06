# LoCoMo Benchmark

Long-term Conversational Memory benchmark — 10 conversations averaging 300 turns each, 1540 QA questions across 5 categories (single-hop, multi-hop, temporal, open-domain, adversarial).

## Headline (Run A canonical, 2026-03-11)

| Metric | Value |
|---|---|
| **Overall F1** | **44.8%** |
| **Multi-hop F1** | **48.5%** (~1.7× Mem0's 28.4%) |
| Oracle ceiling (Mem0 prompt) | 63.9% |
| Run A as % of oracle | 71.4% |

## Run registry on LoCoMo

| Run | What it measures | Status | Headline |
|---|---|---|---|
| A | Primary v6 evaluation | Complete | F1=44.8%, multi-hop=48.5% |
| C | Power vs exponential decay (conv 0) | Complete | Power +3.6pp F1 |
| D | Evidence Recall@k (post-processing) | Complete | R@60 = 35.6% (n=1535) |
| E | Oracle ceiling (Mem0 prompt re-run) | Complete | F1=63.9% |
| F | Per-stage efficiency (post-processing) | Complete | Extraction 15.6s, vec search 54ms |
| G | Feature activation (post-processing) | Complete | 540 candidates/query avg, 60 retrieved |
| H | Hybrid search ablation (conv 0) | Complete | −1.1pp |
| I | Graph expansion ablation (conv 0) | Complete | +0.6pp |
| J | Rerank ablation (conv 0) | Complete | +1.8pp |
| K | Decay model ablation (conv 0, see Run C) | Complete | +3.6pp for power |
| M | Judge reliability (50 stratified samples) | Complete | κ=0.879, 96% agreement |

Earlier exploratory runs (B, F, G in the original tuning sequence) are documented in [`tuning.md`](./tuning.md). Note: tuning.md uses different run-letter conventions from the canonical experimentlog. The authoritative letter mapping is in the root [`experimentlog.md`](../experimentlog.md).

## Competitor results (from their papers)

- **Mem0**: 28.4% multi-hop F1 (LoCoMo paper methodology) — we're **1.7×** this on multi-hop
- **FadeMem**: 29.4% multi-hop F1 (their paper, Table 3)
- **ENGRAM**: 77.55% LLM-as-Judge (different metric — not directly comparable to F1)

## Reproduction

### Run A (parallelized, 10 conversations)

```bash
for i in $(seq 0 9); do
  .venv/bin/python -m locomo.locomo_eval \
    --data locomo/data/locomo10.json \
    --conv-index $i \
    --adapter cognitive_memory \
    --prompt-mode mem0 \
    --dual-perspective --deep-recall --rerank --rerank-factor 3 \
    --top-k 60 --use-judge \
    --output locomo/results/v6/parallel/conv${i}.json \
    2> locomo/results/v6/parallel/conv${i}.log &
done
wait
```

~2h wall, ~50M tokens total.

### Single conversation (fast, ~5 min)

```bash
.venv/bin/python -m locomo.locomo_eval \
  --data locomo/data/locomo10.json \
  --adapter cognitive_memory \
  --prompt-mode mem0 \
  --top-k 60 \
  --conversations 0 \
  --output locomo/results/conv0_test.json
```

## Data

- `data/locomo10.json` — LoCoMo dataset (10 conversations, evidence annotations)
- `data/mem0_custom_instructions.txt` — Mem0's custom instruction prompt

## SDK version

Run A and all post-processing runs (D, E, F, G) and ablations (H–K) used SDK v0.2.0 at commit `60ee27e`. See the root [`experimentlog.md`](../experimentlog.md) for full versioning notes.

## Tuning History

[`tuning.md`](./tuning.md) covers the iterative path from a 4.2% F1 baseline to the 42.4% Run F result. The deferred-conflict-resolution refactor and parallelization (PR #2 on the SDK) lifted the canonical headline from Run F's 42.4% to Run A's 44.8%; the tuning log doesn't cover that final jump because it's downstream of an SDK fix rather than a benchmark-tuning change.

## Configuration (Run A canonical)

| Parameter | Value |
|---|---|
| Adapter | `CognitiveMemoryAdapter` |
| Prompt mode | mem0 (Mem0's 7-step CoT) |
| Top-k | 60 |
| Dual-perspective ingestion | enabled |
| Deep recall | enabled |
| Rerank factor | 3 |
| Judge | gpt-4o-2024-08-06 |
| Answer model | gpt-4o-mini |
| Extraction model | gpt-4o-mini |
| Embedding model | text-embedding-3-small |
| Conflict resolution | deferred (similarity threshold 0.85) |
