# cognitive-memory-benchmarks

Benchmark suite for [cognitive-memory](https://github.com/planetaryescape/cognitive-memory) — a biologically-inspired agent memory system.

## Headline Results

| Benchmark | Status | Our Result | Comparison |
|---|---|---|---|
| **LoCoMo** (10 conv, 1540 QA) | Complete | **44.8% overall F1, 48.5% multi-hop F1** | Mem0 28.4% multi-hop · 70.0% of LoCoMo oracle ceiling |
| **LongMemEval-S** (500 questions) | Complete | **70.2% task-averaged accuracy** | ENGRAM 71.4% (concurrent) · Full-context 56.2% · TiMem 76.88% / EverMemOS 83.0% (post-dating) |
| **LTI-Bench** (controlled, 42 probes) | Complete | **88.1% accuracy, 100% critical-fact retention** | FadeMem 82.1% critical retention |
| **MemoryBench** (2025) | Scaffolded | — | Future work |

Full per-run details, parameters, and per-category breakdowns: [`experimentlog.md`](./experimentlog.md). Operator notes: [`docs/`](./docs/README.md). Paper: [`paper/cognitive-memory-arxiv-paper-v2.pdf`](./paper/cognitive-memory-arxiv-paper-v2.pdf).

## Setup

```bash
# Recreate venv (uv recommended)
uv venv --python 3.10 .venv  # any Python >=3.10 works
uv pip install -e . -e ../cognitive-memory-sdk/sdks/python

# Set API key
export OPENAI_API_KEY=your-key
```

## Running benchmarks

### LoCoMo (Run A reproduction)

```bash
.venv/bin/python -m locomo.locomo_eval \
  --data locomo/data/locomo10.json \
  --adapter cognitive_memory \
  --prompt-mode mem0 \
  --dual-perspective \
  --deep-recall \
  --rerank --rerank-factor 3 \
  --top-k 60 \
  --use-judge \
  --output locomo/results/v6/primary.json
```

For parallel execution per conversation, see [`locomo/README.md`](./locomo/README.md).

### LongMemEval-S (Run B reproduction)

```bash
.venv/bin/python longmemeval/run_longmemeval.py \
  --data longmemeval/data/longmemeval_s_cleaned.json \
  --adapter cognitive_memory \
  --top-k 20 --deep-recall --rerank --rerank-factor 3 \
  --output longmemeval/results/v6/primary.json
```

### LTI-Bench (Run L reproduction)

```bash
.venv/bin/python -m lti.lti_bench \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --judge-model gpt-4o-2024-08-06 \
  --output lti/results/v6_run_l_v2.json
```

## Run Philosophy

For each benchmark, we run up to three configurations:

1. **Apples-to-apples**: Match competitor's exact model, k, embeddings, prompt
2. **Benchmark pure**: Follow official evaluation protocol exactly
3. **Best tuned**: Our optimal config (Mem0 prompt, k=60, deep recall, LLM re-rank)

The headline numbers above use the recorded v6 benchmark configurations shown in each benchmark README. See `experimentlog.md` for exact parameters and caveats.

## Directory Structure

```
shared/           # Adapter interface, metrics (token_f1, llm_judge)
locomo/           # LoCoMo benchmark (Runs A, D, E, F, G, H–K, M)
longmemeval/      # LongMemEval-S (Run B)
lti/              # LTI-Bench (Run L) — controlled architectural test
memorybench/      # MemoryBench 2025 (scaffolded)
simulations/      # Monte Carlo, boosting, cold storage sims
paper/            # arXiv paper.tex, references.bib, build artifacts
docs/             # Operator notes (architecture walkthrough, lessons, next steps)
```

## SDK version / provenance

| Runs | SDK version | Provenance |
|---|---|---|
| Current-refresh LoCoMo, oracle, derived analyses, LTI-Bench | v0.3.0 local source | See `experimentlog.md` for exact commands, timestamps, output paths, and worktree state |
| LongMemEval-S active 500-question result | recorded completed artifact | Current-refresh rerun is in progress; this number should be replaced if the rerun materially differs |
| Historical March runs | v0.2.0/v0.3.0 snapshots | Retained for provenance only |

See [`docs/benchmarks-overview.md`](./docs/benchmarks-overview.md) for full methodology and [`docs/lessons-and-gotchas.md`](./docs/lessons-and-gotchas.md) for what we learned the hard way.

## License

MIT
