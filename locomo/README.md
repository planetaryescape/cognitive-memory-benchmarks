# LoCoMo Benchmark

Long-term Conversational Memory benchmark — 10 conversations, 1540 QA questions across 5 categories.

## Results Summary

| Run | Config | Overall F1 | Multi-Hop F1 | Notes |
|-----|--------|-----------|-------------|-------|
| A | Official protocol (k=20) | 28.2% | 34.5% | Baseline |
| B | FadeMem settings (k=20) | 27.7% | 33.0% | FadeMem replication |
| E | Tuned prompt (k=40, deep recall) | 38.2% | 33.7% | Prompt tuning |
| F | Mem0 prompt (k=60) | 42.4% | 47.1% | Best published |
| H | Mem0 + deep recall + LLM re-rank | TBD | TBD | Conv 0: 47.8%/59.3% |

## Competitor Results (from their papers)

- **Mem0**: 28.4% multi-hop F1 (LoCoMo paper methodology)
- **FadeMem**: 29.4% multi-hop F1 (their paper, Table 3)
- **ENGRAM**: 77.55% LLM-as-Judge (not F1 — different metric, not comparable)

## Reproduction

```bash
# Exact Run F reproduction
python -m locomo.locomo_eval \
  --data locomo/data/locomo10.json \
  --adapter cognitive_memory \
  --prompt-mode mem0 \
  --top-k 60 \
  --output locomo/results/reproduction.json

# Single conversation test (fast, ~5 min)
python -m locomo.locomo_eval \
  --data locomo/data/locomo10.json \
  --adapter cognitive_memory \
  --prompt-mode mem0 \
  --top-k 60 \
  --conversations 0 \
  --output locomo/results/conv0_test.json
```

## Data

- `data/locomo10.json` — LoCoMo dataset (10 conversations)
- `data/mem0_custom_instructions.txt` — Mem0's custom instruction prompt

## Tuning History

See [tuning.md](tuning.md) for the full optimization journey from 4.2% to 42.4%.
