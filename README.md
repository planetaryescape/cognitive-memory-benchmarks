# cognitive-memory-benchmarks

Benchmark suite for [cognitive-memory](https://github.com/planetaryescape/cognitive-memory) — a biologically-inspired agent memory system. All headline numbers below come from the **`current_sdk_20260505` refresh** against SDK v0.4.0; legacy `v6/` artifacts remain on disk for provenance.

## Headline Results

| Benchmark | Status | Our Result | Comparison |
|---|---|---|---|
| **LoCoMo** (10 conv, 1540 QA) | Complete | **44.8% overall F1, 48.5% multi-hop F1** | Mem0 28.4% multi-hop · 70% of LoCoMo oracle ceiling (63.9% F1) |
| **LongMemEval-S** (500 questions) | Recorded artifact (rerun in progress) | **70.2% task-averaged accuracy** | ENGRAM 71.4% (concurrent) · Full-context 56.2% · TiMem 76.88% / EverMemOS 83.0% (post-dating) |
| **LTI-Bench v2** (controlled, 42 probes) | Complete | **88.1% accuracy, 69.7% F1, 100% critical-fact retention** | FadeMem 82.1% critical retention |
| **MemoryBench** (2025) | Scaffolded | — | Future work |

Auxiliary measurements from the same refresh: **LoCoMo oracle ceiling 63.9% F1** (61.1% under Mem0 scoring), **evidence Recall@60 35.6%**, **decay model power-law +3.2pp over exponential**, **rerank +1.9pp**, **hybrid search +1.7pp**, **judge agreement 94% (Cohen's κ 0.879)**.

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

The `current_sdk_20260505` runs use the v6 retrieval pipeline with hybrid search, deep recall, LLM rerank (`rerank-factor 3`), and `top-k 60` for LoCoMo (`top-k 20` for LongMemEval).

### LoCoMo (Run CR-A reproduction)

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
  --output locomo/results/current_sdk_20260505/primary.json
```

For parallel execution per conversation, see [`locomo/README.md`](./locomo/README.md).

### LongMemEval-S (Run CR-B reproduction)

```bash
.venv/bin/python longmemeval/run_longmemeval.py \
  --data longmemeval/data/longmemeval_s_cleaned.json \
  --adapter cognitive_memory \
  --top-k 20 --deep-recall --rerank --rerank-factor 3 \
  --output longmemeval/results/current_sdk_20260505/primary.json
```

### LTI-Bench v2 (Run CR-C reproduction)

```bash
.venv/bin/python -m lti.lti_bench \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --judge-model gpt-4o-2024-08-06 \
  --output lti/results/current_sdk_20260505/run_l_v2.json
```

## Run Philosophy

For each benchmark, we run up to three configurations:

1. **Apples-to-apples**: Match competitor's exact model, k, embeddings, prompt
2. **Benchmark pure**: Follow official evaluation protocol exactly
3. **Best tuned**: Our optimal config (Mem0 prompt, k=60, deep recall, hybrid search, LLM rerank)

The headline numbers above use the `current_sdk_20260505` configurations shown in each benchmark README. See `experimentlog.md` for exact parameters and caveats.

## Directory Structure

```
shared/           # Adapter interface, metrics (token_f1, llm_judge)
locomo/           # LoCoMo benchmark (Runs A, CR-A, ablations, oracle)
longmemeval/      # LongMemEval-S (Run B, CR-B)
lti/              # LTI-Bench (Run L, CR-C) — controlled architectural test
memorybench/      # MemoryBench 2025 (scaffolded)
analysis/         # Post-processing scripts, ablation runner
simulations/      # Monte Carlo, boosting, cold storage sims
paper/            # arXiv paper.tex, references.bib, build artifacts
docs/             # Operator notes (architecture walkthrough, lessons, next steps)
```

## SDK version / provenance

| Runs | SDK | Provenance |
|---|---|---|
| `current_sdk_20260505` (LoCoMo, LTI-Bench v2, oracle, ablations, decay, recall, judge reliability) | v0.4.0 from editable `../cognitive-memory-sdk/sdks/python` | See `experimentlog.md` for exact commands, timestamps, output paths, and worktree state |
| LongMemEval-S 500-question headline | recorded completed artifact (Mar 2026 run) | Current-refresh rerun is in progress; replace if rerun materially differs |
| Historical March runs (`v6/` namespace) | v0.2.0 / v0.3.0 snapshots | Retained for provenance only |

See [`docs/benchmarks-overview.md`](./docs/benchmarks-overview.md) for full methodology and [`docs/lessons-and-gotchas.md`](./docs/lessons-and-gotchas.md) for what we learned the hard way.

## License

MIT
