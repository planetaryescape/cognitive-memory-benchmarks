# LoCoMo Benchmark

Long-term Conversational Memory benchmark — 10 conversations averaging 300 turns each, 1540 QA questions across 5 categories (single-hop, multi-hop, temporal, open-domain, adversarial).

## Headline (current paper row, Phase 5 v0.5 tuned defaults)

| Metric | Value |
|---|---|
| **Overall F1** | **46.2%** |
| **Multi-hop F1** | **51.3%** (~1.8× Mem0's reported 28.4%) |
| Oracle ceiling (Mem0 prompt) | 63.9% |
| Current row as % of oracle | 72.3% |

Phase 5 is the active paper/docs LoCoMo row. The May current-refresh CR-A artifact remains useful and reproducible, but it is now a baseline snapshot: 44.8% overall F1, 48.5% multi-hop F1, and 58.4% judge accuracy.

## Run registry on LoCoMo

| Run | What it measures | Status | Headline |
|---|---|---|---|
| P5 | Full LoCoMo v0.5 tuned defaults | Complete | F1=46.2%, multi-hop=51.3% |
| CR-A | May 2026 current-refresh baseline | Complete | F1=44.8%, multi-hop=48.5% |
| C | Power vs exponential decay (conv 0) | Complete | Power +3.6pp F1 |
| D | Evidence Recall@k (post-processing) | Complete | R@60 = 35.6% (n=1535) |
| E | Oracle ceiling (Mem0 prompt re-run) | Complete | F1=63.9% |
| F | Per-stage efficiency (post-processing) | Complete | Extraction 15.6s, vec search 54ms |
| G | Feature activation (post-processing) | Complete | 540 candidates/query avg, 60 retrieved |
| H | Hybrid search ablation (conv 0) | Complete | +1.7pp in current-refresh rerun |
| I | Graph expansion ablation (conv 0) | Complete | ~0.0pp in current-refresh rerun |
| J | Rerank ablation (conv 0) | Complete | +1.9pp in current-refresh rerun |
| K | Decay model ablation (conv 0, see Run C) | Complete | +3.2pp to +4.6pp depending on runner |
| M / CR-I | Judge reliability (50 stratified samples) | Complete | κ=0.879, 94% agreement |
| P15 | In-house NaiveRAG baseline | Complete | CM +1.06pp overall; +27.93pp temporal; NaiveRAG wins single-hop/multi-hop/open-domain |

Earlier exploratory runs (B, F, G in the original tuning sequence) are documented in [`tuning.md`](./tuning.md). Note: tuning.md uses different run-letter conventions from the canonical experimentlog. The authoritative letter mapping is in the root [`experimentlog.md`](../experimentlog.md).

## Competitor results (from their papers)

- **Mem0**: 28.4% multi-hop F1 (LoCoMo paper methodology) — the Phase 5 row is **~1.8×** this on multi-hop
- **FadeMem**: 29.4% multi-hop F1 (their paper, Table 3)
- **ENGRAM**: 77.55% LLM-as-Judge (different metric — not directly comparable to F1)

## Reproduction

### CR-A (parallelized, 10 conversations)

```bash
for i in $(seq 0 9); do
  .venv/bin/python -m locomo.locomo_eval \
    --data locomo/data/locomo10.json \
    --conv-index $i \
    --adapter cognitive_memory \
    --prompt-mode mem0 \
    --dual-perspective --deep-recall --rerank --rerank-factor 3 \
    --top-k 60 --use-judge \
    --output locomo/results/current_sdk_20260505/parallel/conv${i}.json \
    2> locomo/results/current_sdk_20260505/parallel/conv${i}.log &
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

## SDK and artifact provenance

The active LoCoMo headline is `tuning/runs/phase5/v05_tuned/aggregate.json`. The May current-refresh baseline is `locomo/results/current_sdk_20260505/primary_merged.json`. See the root [`experimentlog.md`](../experimentlog.md) and [`experimentlog_v2.md`](../experimentlog_v2.md) for full versioning notes.

Older Run A/F/H/J labels are historical unless a section explicitly says it is discussing an ablation or baseline.

## Configuration (current LoCoMo harness)

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
