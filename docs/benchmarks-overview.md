# Benchmarks Overview — Methodology, Runs, Results

The full canonical record is in `experimentlog.md` (run registry, parameters, changelog). This doc is a higher-altitude summary of how the benchmark suite is organised, how each run works, and what we found.

## 1. The benchmark suite

| Run | Benchmark | Status | What it measures |
|---|---|---|---|
| A | LoCoMo v6 Primary | COMPLETE | Multi-session conversational QA F1 |
| B | LongMemEval-S | COMPLETE | Long-horizon memory across 6 task types |
| C | Decay comparison | COMPLETE | Power-law vs exponential, conv 0 |
| D | Evidence Recall@k | COMPLETE | Retrieval quality, post-processing of Run A |
| E | Oracle Ceiling | COMPLETE | What's possible if retrieval is perfect |
| F | Efficiency table | COMPLETE | Per-stage timings |
| G | Feature activation | COMPLETE | How often graph expansion / validity / bridge fire |
| H–K | Ablations | COMPLETE | Per-feature delta on conv 0 |
| L | LTI-Bench | COMPLETE (v2) | Synthetic 30-day controlled architectural test |
| M | Judge reliability | COMPLETE | Inter-judge agreement (κ) on a LoCoMo Run A QA sample |

## 2. Setup, common across runs

| Knob | Value |
|---|---|
| Extraction model | `gpt-4o-mini` |
| Embedding model | `text-embedding-3-small` (1536 dims) |
| Answer model | `gpt-4o-mini` |
| Judge model (LongMemEval) | `gpt-4o-2024-08-06` |
| SDK provenance | See `experimentlog.md` for exact command, output path, commit/worktree state, and model config per run |
| Hardware | Apple Silicon M-series, 128 GB RAM, macOS 26.3 |
| OpenAI tier | High |
| Python | 3.14.2 (benchmarks venv) |

Default v6 adapter configuration unless ablated:

```python
decay_model = "exponential"
hybrid_search = False
graph_expansion_hops = 1
rerank_enabled = True (kRerank=10, factor=3 for LoCoMo)
filter_expired_transients = True
include_expired_in_deep_recall = True
```

## 3. Headlines

### LoCoMo (Run A)
- **Overall F1: 44.8%**
- **Multi-hop F1: 48.5%** (~1.7× Mem0's reported 28.4%)
- 10 conversations, 1540 questions
- Mem0 prompt + dual-perspective ingestion + deep recall + rerank ×3 + k=60 + judge + deferred conflicts
- Run via 10 parallel processes (one per conversation), ~2h wall

### LongMemEval-S (Run B)
- **Task-averaged accuracy: 70.2%** (vs ENGRAM 71.4%, full-context 56.2%)
- 500 questions, 6 task types
- Per-task accuracy:
  - single-session-user 88.6%, single-session-assistant 73.2%, single-session-preference 36.7%
  - multi-session 75.9%, temporal-reasoning 62.4%, knowledge-update 84.6%
  - abstention 90.0%
- 11.3h wall, hit OpenAI quota at q339, resumed from q340

### Decay comparison (Run C)
- Conv 0 only, exp vs power
- Power-law: 30.4% F1 / Exponential: 26.8% F1 — **+3.6pp for power-law**
- Largest single-feature contribution measured

### Evidence Recall@k (Run D)
- Post-processing of Run A's per-question retrieved memories
- R@5: 24.8%, R@10: 28.5%, R@20: 31.7%, R@60: 35.6%
- n=1535 (99.7% of LoCoMo questions have evidence annotations)
- Implication: retrieval is the bottleneck, answer model robustness compensates

### Oracle Ceiling (Run E, with Mem0 prompt re-run)
- Ground-truth evidence as context, gpt-4o-mini answers
- F1=63.9% (LoCoMo scoring) / 61.1% (Mem0 scoring)
- Current LoCoMo F1 44.8% = 70.0% of LoCoMo oracle ceiling

### Efficiency (Run F)
- Extraction: ~15.6s per turn (LLM-bound)
- Vector search: 54ms mean per query
- Scoring: 0.69ms per query
- Rerank/answer not in trace (deployment-dependent)

### Feature activation (Run G)
- 540 candidates/query average pre-filter
- 60 retrieved (after scoring + rerank + slice)
- All 10 LoCoMo conversations

### Ablations (Runs H–K, conv 0)
| Feature | Off | On | Δ |
|---|---:|---:|---:|
| Power-law decay | 26.8% | 30.4% | **+3.6pp** |
| Rerank ×3 | 43.2% | 45.0% | +1.8pp |
| Graph expansion (1 hop) | 44.4% | 45.0% | +0.6pp |
| Hybrid search | 45.0% | 43.9% | **−1.1pp** |

Power-law decay is the only individually large-positive feature. Hybrid search slightly hurts on conversational text (likely BM25 noise on natural-language turns).

### Judge reliability (Run M)
- 50 stratified QA pairs (8 buckets: 5 categories × correct/wrong)
- Re-judged with alternative "EQUIVALENT/DIFFERENT" prompt
- **Cohen's κ = 0.879, 94% raw agreement, 3 disagreements (both single-hop)**

### LTI-Bench v2 (Run L) — see [`lti-bench.md`](./lti-bench.md)
- 28 facts, 28 daily sessions, 42 probes, 8 probe types
- Time-stepped ingestion, llm_judge scoring (gpt-4o-2024-08-06)
- **Overall: 88.1% accuracy, F1 69.7%**
- **Critical fact retention: 100% vs FadeMem 82.1%**
- 66/85 stored memories promoted to core (78%)

## 4. How each run is driven

### Run A — `locomo/locomo_eval.py`

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

For parallel execution, Run A used 10 separate processes one per conversation. `locomo_eval.py` accepts `--conv-index N` to run just one.

### Run B — `longmemeval/run_longmemeval.py`

```bash
.venv/bin/python longmemeval/run_longmemeval.py \
  --data longmemeval/data/longmemeval_s_cleaned.json \
  --adapter cognitive_memory \
  --top-k 20 \
  --deep-recall \
  --rerank \
  --output longmemeval/results/v6/primary.json
```

Quota-resumable via `--resume-from <q_index>`.

### Run C — `simulations/decay_comparison.py`

Custom script, runs locomo_eval on conv 0 with both decay models, captures F1 delta.

### Run D — `locomo/evidence_recall.py`

Post-processing only. Reads `locomo/results/v6/parallel/conv{0..9}.json`, walks each question's `retrieved_contents` (top-60 memory strings), checks if the question's gold evidence text appears as a substring (fuzzy / case-insensitive) at k=5/10/20/60. No new API calls.

### Run E — `locomo/oracle_ceiling.py`

Drives `locomo_eval.py` with a custom adapter that returns ground-truth evidence sessions instead of doing similarity search. Two variants: original (LoCoMo prompt, max_tokens=100) and re-run (Mem0 prompt, no max_tokens) — only the re-run is comparable to Run A.

### Run F — `locomo/efficiency_table.py`

Post-processing. Walks `trace.stages.*.wall_ms` from each conv's per-question entries, computes mean/p50/p95.

### Run G — `locomo/feature_activation.py`

Post-processing. Counts how often graph expansion fired, how often validity filtering excluded a candidate, how often a bridge path was found.

### Runs H–K — `analysis/ablation_runner.py`

Wrapper that re-runs `locomo_eval.py` on conv 0 with one feature toggled per run:
- H: hybrid_search on (default off)
- I: graph_expansion_hops=0 (default 1)
- J: rerank off (default on)
- K: decay_model=power (default exponential) — overlaps with Run C

Output goes to `locomo/results/v6/ablations/{baseline,h_hybrid_on,i_hops0,j_rerank_off}.json`.

### Run L — `lti/lti_bench.py`

```bash
.venv/bin/python -m lti.lti_bench \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --judge-model gpt-4o-2024-08-06 \
  --output lti/results/v6_run_l_v2.json
```

See [`lti-bench.md`](./lti-bench.md) for the full v1→v2 evolution.

### Run M — `locomo/judge_reliability.py`

Reads conv{0..9}.json, samples 50 QA pairs stratified by (category × correctness), re-judges with alternative prompt, computes Cohen's κ.

## 5. Key methodology choices

### Ingestion: parallel + dual-perspective
Run A ingests each LoCoMo conversation via 10 parallel processes (one per conversation, not one per turn). Within a conversation, ingestion is dual-perspective: the same conversation is ingested twice, once from each speaker's viewpoint. This produces ~2× memories but covers both sides. Same-session-root pairs are skipped during conflict detection so dual-perspective doesn't generate false conflicts.

### Deferred conflict resolution
Earlier attempts at Run A hung at session 19 of conv 0 due to inline conflict detection making O(N²) LLM calls. The fix: detect (cosine > 0.85) at ingestion, queue for resolution; resolve in batches at maintenance tick time. The threshold was raised from 0.6 to 0.85 because 0.6 produced 1422 false-positive candidates per conv. After the fix, conv 0 ingestion completed in ~76 minutes with no hangs.

### Mem0 prompt for answer generation
LoCoMo's official scoring uses an answer prompt that includes 7-step CoT-style instructions. Run A uses this Mem0 prompt to be apples-to-apples with Mem0's published numbers. Earlier debug runs used a generic prompt and got lower F1; multi-hop in particular jumped from 39.4% → 65.9% (debug) and 48.5% (production) when switching to the Mem0 prompt.

### Top-k = 60 for LoCoMo, 20 for LongMemEval
LoCoMo questions can require evidence from many sessions; top-60 gives the rerank room to operate. LongMemEval questions are typically narrower; top-20 + deep recall + rerank is sufficient. These were tuned during debug runs, not formally swept.

### Judge model = gpt-4o-2024-08-06
LongMemEval's official judge. We use the same model for LongMemEval-S grading (Run B) and for LTI-Bench v2 LLM-as-judge scoring (Run L v2) for consistency. Run M established that this judge has κ=0.879 inter-prompt agreement, so it's load-bearing enough to use as the headline metric.

## 6. Data inventory

| File | Contents | Notes |
|---|---|---|
| `locomo/data/locomo10.json` | 10 conversations, ~300 turns each, 1540 QA, evidence annotations | Source data |
| `locomo/results/v6/parallel/conv{0..9}.json` | Per-conv full results: per_question entries (with retrieved_contents and trace) + aggregate F1 | Run A canonical output |
| `locomo/results/v6/parallel/conv{0..9}.log` | stderr (extraction/rerank timing info) | Run A logs |
| `locomo/results/v6/oracle_ceiling.json` | Run E v1 (LoCoMo prompt, max_tokens=100) | Superseded by Mem0 re-run |
| `locomo/results/v6/oracle_ceiling_mem0.json` | Run E re-run (Mem0 prompt, no max_tokens) | Canonical comparison |
| `locomo/results/v6/efficiency_table.json` | Per-stage wall timings | Run F |
| `locomo/results/v6/feature_activation.json` | Activation counters | Run G |
| `locomo/results/v6/ablations/{4 files}.json` | Per-feature ablation results | Runs H–K |
| `locomo/results/v6/judge_reliability.json` | κ stats and disagreement details | Run M |
| `longmemeval/data/longmemeval_s_cleaned.json` | 500 questions, 53 haystack sessions/q | Source data |
| `longmemeval/results/v6/primary.json` | Per-task accuracy + abstention + per-question | Run B canonical |
| `simulations/decay_comparison.json` | Power vs exp F1 deltas | Run C |
| `lti/results/v6_run_l_v2.json` | LTI-Bench canonical | Run L v2 |
| `lti/results/v6_run_l.json` | LTI-Bench v1 (substring scoring) | Superseded |

## 7. Reproducing a run

Standard sequence for any run:

```bash
cd ~/code/bhekanik/cognitive-memory-benchmarks
source .venv/bin/activate   # or use .venv/bin/python directly

# Verify SDK version
python -c "import cognitive_memory; print(cognitive_memory.__version__)"
# Should print 0.3.0 (current local) or 0.2.0 (the published Run A–K version)

# Run the relevant script (see commands above)
```

For Run A specifically, the parallel form:

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

## 8. Cost notes

Order-of-magnitude API costs (gpt-4o-mini answer + extraction, gpt-4o-2024-08-06 judge):

| Run | Approx tokens | Approx wall |
|---|---|---|
| A (LoCoMo full, parallel) | ~50M total tokens across 10 processes | ~2h |
| B (LongMemEval-S, single) | ~30M tokens | ~11.3h |
| C (decay, conv 0 ×2) | ~5M tokens | ~30 min |
| D | 0 (post-processing) | <5 min |
| E re-run (oracle, Mem0 prompt, all conv) | ~3M tokens | ~18 min |
| F | 0 (post-processing) | <2 min |
| G | 0 (post-processing) | <2 min |
| H–K (4 conv-0 ablation runs) | ~2M tokens | ~2h parallel |
| L (LTI-Bench v2) | ~500k tokens | ~5 min |
| M (50-pair re-judge) | ~50k tokens | <2 min |

Run A was the dominant cost driver; everything else is incremental. OpenAI quota was exhausted once during Run A and once during Run B; both resumed cleanly.

## 9. What's NOT in the benchmark suite

- **MSC** (Multi-Session Chat) — referenced as future work but never run.
- **MemoryBench** — vendored as `memorybench/repo/` but never wired up.
- **LongMemEval-M and Oracle** — only -S was run. -M would be ~10× tokens; deferred.
- **NaiveRAG full LoCoMo run** — `NaiveRAGAdapter` exists in `shared/adapter.py` but was never run on the full corpus to give an in-house baseline column. The published Mem0 / FadeMem numbers serve as the comparison instead.
- **Cross-model generalisation** — every run uses gpt-4o-mini answer + gpt-4o-2024-08-06 judge. Nothing tested with Claude or Llama.
- **Multi-seed runs** — every reported number is single-seed.

These are documented as Limitations in the paper and as Future Work entries.
