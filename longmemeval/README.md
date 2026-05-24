# LongMemEval (ICLR 2025)

500 hand-crafted questions testing 5 memory abilities across long conversations with ~53 haystack sessions per question. We evaluate on the Small variant only.

## Status: Complete (LongMemEval-S)

Current-refresh canonical result, completed 2026-05-07. Historical Run B from 2026-03-10 remains in `longmemeval/results/v6/` for provenance only.

## Headline

| Metric | Value |
|---|---|
| **Task-averaged accuracy** | **71.6%** |
| Overall accuracy | 72.6% |
| Abstention accuracy | 90.0% |

| Task | n | Accuracy |
|---|---:|---:|
| single-session-user | 70 | 85.7% |
| single-session-assistant | 56 | 76.8% |
| single-session-preference | 30 | 46.7% |
| multi-session | 133 | 69.9% |
| temporal-reasoning | 133 | 64.7% |
| knowledge-update | 78 | 85.9% |

## Comparison

| System | Task-averaged | Notes |
|---|---:|---|
| Full-context baseline | 56.2% | Published |
| **cognitive-memory (ours)** | **71.6%** | Current-refresh CR-B, default v6 config, no benchmark-specific tuning |
| ENGRAM | 71.4% | Concurrent baseline at run time |
| TiMem | 76.88% | Post-dating system, multi-stage architecture |
| EverMemOS | 83.0% | Post-dating system, engram-inspired lifecycle |

We are within 0.2pp of ENGRAM (the strongest single-stage baseline at run time) without benchmark-specific tuning. Newer multi-stage systems (TiMem, EverMemOS) exceed our result; we acknowledge this in the paper rather than over-claiming.

## Reproduction

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

The runner accepts `--start-from <q_index>` for resumable runs. CR-B completed the first 80 questions, fixed a thread-safety patch bug, then resumed from `--start-from 80`.

## Configuration

| Parameter | Value |
|---|---|
| Top-k | 20 |
| Deep recall | enabled |
| Rerank | enabled (factor 3 in the paper configuration) |
| Answer model | gpt-4o-mini |
| Judge model | gpt-4o-2024-08-06 (LongMemEval official) |
| Embedding model | text-embedding-3-small (1536 dims) |
| SDK provenance | See `experimentlog.md`; CR-B is the completed current-refresh artifact |

## Cost

`52328.0s` wall across original plus resumed run. See `longmemeval/results/current_sdk_20260505/primary_resume_80.log` and `experimentlog.md`.

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

The architecture's strengths (decay floors, conflict detection, temporal awareness) align with abilities 3–5. CR-B's strongest tasks were single-session-user (85.7%), knowledge-update (85.9%), and abstention (90.0%); weakest was single-session-preference (46.7%).
