# LongMemEval (ICLR 2025)

500 hand-crafted questions testing 5 memory abilities across long conversations with ~53 haystack sessions per question. We evaluate on the Small variant only.

## Status: Complete (LongMemEval-S)

Run B canonical result, 2026-03-10. A May 2026 current-refresh rerun is in progress under `longmemeval/results/current_sdk_20260505/`; use the recorded Run B number until that rerun completes and is logged.

## Headline

| Metric | Value |
|---|---|
| **Task-averaged accuracy** | **70.2%** |
| Overall accuracy | 72.8% |
| Abstention accuracy | 90.0% |

| Task | n | Accuracy |
|---|---:|---:|
| single-session-user | 70 | 88.6% |
| single-session-assistant | 56 | 73.2% |
| single-session-preference | 30 | 36.7% |
| multi-session | 133 | 75.9% |
| temporal-reasoning | 133 | 62.4% |
| knowledge-update | 78 | 84.6% |

## Comparison

| System | Task-averaged | Notes |
|---|---:|---|
| Full-context baseline | 56.2% | Published |
| **cognitive-memory (ours)** | **70.2%** | Run B, default v6 config, no benchmark-specific tuning |
| ENGRAM | 71.4% | Concurrent baseline at run time |
| TiMem | 76.88% | Post-dating system, multi-stage architecture |
| EverMemOS | 83.0% | Post-dating system, engram-inspired lifecycle |

We are within 1.2pp of ENGRAM (the strongest single-stage baseline at run time) without benchmark-specific tuning. Newer multi-stage systems (TiMem, EverMemOS) exceed our result; we acknowledge this in the paper rather than over-claiming.

## Reproduction

```bash
.venv/bin/python longmemeval/run_longmemeval.py \
  --data longmemeval/data/longmemeval_s_cleaned.json \
  --adapter cognitive_memory \
  --top-k 20 \
  --deep-recall \
  --rerank --rerank-factor 3 \
  --output longmemeval/results/v6/primary.json
```

The runner accepts `--resume-from <q_index>` for quota-resumable runs (Run B exhausted OpenAI quota at q339 and resumed cleanly).

## Configuration

| Parameter | Value |
|---|---|
| Top-k | 20 |
| Deep recall | enabled |
| Rerank | enabled (factor 3 in the paper configuration) |
| Answer model | gpt-4o-mini |
| Judge model | gpt-4o-2024-08-06 (LongMemEval official) |
| Embedding model | text-embedding-3-small (1536 dims) |
| SDK provenance | See `experimentlog.md`; Run B is a recorded completed artifact, while the May 2026 current-refresh rerun is still in progress |

## Cost

~30M tokens total, ~11.3h wall.

## What's not run

- **LongMemEval-M** — ~10× larger haystack per question. Multi-day wall time, ~$300+ in API. Documented as future work in the paper.
- **LongMemEval-Oracle** — single relevant session per question. Not in the dataset directory.

To run -M, the dataset would need to be downloaded (currently only `longmemeval_s_cleaned.json` is present). The runner script supports arbitrary data files.

## 5 Memory Abilities Tested

1. **Information Extraction** — basic fact recall
2. **Multi-Session Reasoning** — cross-session inference
3. **Knowledge Update** — handling contradictions over time
4. **Temporal Reasoning** — time-aware questions
5. **Abstention** — knowing when you don't know

The architecture's strengths (decay floors, conflict detection, temporal awareness) align with abilities 3–5. Run B's strongest tasks were single-session-user (88.6%), knowledge-update (84.6%), and abstention (90.0%); weakest was single-session-preference (36.7%).
