# cognitive-memory-benchmarks

Benchmark suite for [cognitive-memory](https://github.com/bhekanik/cognitive-memory-py) — a biologically-inspired agent memory system.

## Benchmarks

| Benchmark | Status | Our Best | Mem0 | FadeMem | ENGRAM |
|---|---|---|---|---|---|
| **LoCoMo** (10 conv) | Complete | 42.4% F1 | 28.4% MH | 29.4% MH | 77.55% LLM-Judge* |
| **MemoryBench** (2025) | Scaffolded | - | Evaluated | Not evaluated | - |
| **LongMemEval** (ICLR 2025) | Scaffolded | - | Not evaluated | Not evaluated | 71.40% |

\* ENGRAM uses LLM-as-Judge (not F1), so scores are not directly comparable.

## Setup

```bash
# Install the SDK
pip install cognitive-memory[openai]

# Install benchmarks
pip install -e .

# Set API key
export OPENAI_API_KEY=your-key
```

## LoCoMo Evaluation

```bash
# Run F: Mem0 prompt, k=60 (our published result)
python -m locomo.locomo_eval \
  --data locomo/data/locomo10.json \
  --adapter cognitive_memory \
  --prompt-mode mem0 \
  --top-k 60 \
  --output locomo/results/my_run.json

# With deep recall + LLM re-ranking (Run H)
python -m locomo.locomo_eval \
  --data locomo/data/locomo10.json \
  --adapter cognitive_memory \
  --prompt-mode mem0 \
  --top-k 60 \
  --deep-recall \
  --rerank \
  --output locomo/results/my_run_h.json
```

## Run Philosophy

For each benchmark, we run three configurations:

1. **Apples-to-apples**: Match competitor's exact model, k, embeddings, prompt
2. **Benchmark pure**: Follow official evaluation protocol exactly
3. **Best tuned**: Our optimal config (Mem0 prompt, k=60, deep recall, LLM re-rank)

## Directory Structure

```
shared/           # Adapter interface, metrics
locomo/           # LoCoMo benchmark (complete with results)
lti/              # LTI-Bench (custom forgetting dynamics test)
memorybench/      # MemoryBench 2025 (scaffolded)
longmemeval/      # LongMemEval ICLR 2025 (scaffolded)
paper/            # arXiv paper, references
simulations/      # Monte Carlo, boosting, cold storage sims
```

## License

MIT
