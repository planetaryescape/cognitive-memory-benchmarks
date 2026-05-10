# cognitive-memory-benchmarks

Benchmark suite for [cognitive-memory](https://github.com/planetaryescape/cognitive-memory) — a biologically-inspired agent memory system. Most headline numbers below come from the **`current_sdk_20260505` refresh** against editable local SDK package version `0.3.0` (legacy `v6/` artifacts remain on disk for provenance). The 2026-05 tuning campaign (Phase 0g→5) added a v0.4-vs-v0.5 head-to-head row at the bottom.

## Headline Results

| Benchmark | Status | Our Result | Comparison |
|---|---|---|---|
| **LoCoMo** (10 conv, 1540 QA) | Complete | **44.8% overall F1, 48.5% multi-hop F1** | Mem0 28.4% multi-hop · 70% of LoCoMo oracle evidence context condition (63.9% F1) |
| **LongMemEval-S** (500 questions) | Complete | **71.6% task-averaged accuracy, 72.6% overall accuracy** | ENGRAM 71.4% (concurrent) · Full-context 56.2% · TiMem 76.88% / EverMemOS 83.0% (post-dating) |
| **LTI-Bench v2** (controlled, 42 probes) | Complete | **88.1% accuracy, 69.7% F1, 100% critical-fact retention** | FadeMem 82.1% critical retention |
| **MemoryBench** (2025) | Scaffolded | — | Future work |

Auxiliary measurements from the same refresh: **LoCoMo oracle evidence context condition 63.9% F1** (61.1% under Mem0 scoring), **evidence Recall@60 35.6%**, **decay model power-law +3.2pp over exponential**, **rerank +1.9pp**, **hybrid search +1.7pp**, **judge agreement 94% (Cohen's κ 0.879)**.

## v0.5 Empirical Default Tuning (Phase 0g→5, 2026-05)

A systematic tuning campaign on LTI-Bench (~$30 / 12h) followed by validation on full LoCoMo (~$100 / 3.4h) shipped three new SDK defaults in [cognitive-memory v0.5.0](https://github.com/planetaryescape/cognitive-memory/blob/main/sdks/python/CHANGELOG.md):

- `associative_boost`: 0.03 → **0.05**
- `base_decay_rates.semantic`: 120 → **240** (days)
- `core_session_threshold`: 3 → **2**

| Bench (production flags) | v0.4 (paper defaults) | v0.5 (tuned) | Δ |
|---|---|---|---|
| LoCoMo full (1540 QA) F1 | 0.4437 | **0.4624** | **+1.87pp** |
| LoCoMo full (1540 QA) LLM accuracy | 0.5857 | **0.6130** | **+2.73pp** |
| LoCoMo conv0 F1 | 0.4310 | 0.4601 | +2.92pp |
| LongMemEval-S 500 QA accuracy | _attempted; OpenAI billing-cap blocked at 30%_ | _inconclusive_ | n/a |

Methodology, per-phase milestones, full provenance: `docs/milestones/phase-{0-harness-extension,1-sensitivity-analysis,2-optuna-tuning,4-locomo-reality-check,5-full-locomo,7-longmemeval-validation}.md`. Single-author campaign; ~$245 spend / ~28h compute total. Phase 7 (LongMemEval-S validation) hit an account billing cap twice at 30% completion; partial data is inconclusive but consistent across both attempts. Phase 5 (full LoCoMo) is the load-bearing v0.5 validation.

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

The `current_sdk_20260505` runs use the v6 retrieval pipeline with deep recall, LLM rerank (`rerank-factor 3`), and `top-k 60` for LoCoMo (`top-k 20` for LongMemEval). Hybrid search is off in the headline run and measured separately in ablations.

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
  --model gpt-4o-mini \
  --top-k 20 --deep-recall --rerank --rerank-factor 3 \
  --max-workers 53 \
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

The headline numbers above use the `current_sdk_20260505` configurations shown in each benchmark README. See `experimentlog.md` and [`docs/current-refresh-20260505.md`](./docs/current-refresh-20260505.md) for exact parameters, artifact paths, and caveats.

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
| `current_sdk_20260505` (LoCoMo, LongMemEval-S, LTI-Bench v2, oracle, ablations, decay, recall, judge reliability) | package version `0.3.0` from editable `../cognitive-memory-sdk/sdks/python` | See `experimentlog.md` and `docs/current-refresh-20260505.md` for exact commands, timestamps, output paths, and worktree state |
| LongMemEval-S 500-question headline | current-refresh completed artifact | `longmemeval/results/current_sdk_20260505/primary.json` |
| Historical March runs (`v6/` namespace) | v0.2.0 / v0.3.0 snapshots | Retained for provenance only |

See [`docs/benchmarks-overview.md`](./docs/benchmarks-overview.md) for full methodology and [`docs/lessons-and-gotchas.md`](./docs/lessons-and-gotchas.md) for what we learned the hard way.

## License

MIT
