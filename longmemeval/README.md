# LongMemEval (ICLR 2025)

500 hand-crafted questions testing 5 memory abilities across long conversations.

**Priority**: First benchmark to implement (simpler than MemoryBench, JSONL output).

## Status: Scaffolded

Integration pending.

## Competitor Parameters

### ENGRAM (State-of-the-art)

- **Embedding**: text-embedding-3-small
- **Top-k per memory type**: 25
- **Final evidence budget K**: 25 (after dedup)
- **Answer LLM**: gpt-4o-mini
- **Judge**: GPT-4o (binary yes/no)
- **Storage**: SQLite
- **Result**: 71.40% overall (vs 56.20% full-context baseline)

### FadeMem

**Not evaluated on LongMemEval.**

### Mem0

**Not evaluated on LongMemEval.**

## Our Three Run Types

1. **Apples-to-apples with ENGRAM**: text-embedding-3-small, k=25, gpt-4o-mini answer
2. **Benchmark pure**: Follow LongMemEval official protocol (GPT-4o binary judge)
3. **Best tuned**: Our optimal config (k=60, deep recall, LLM re-rank, Mem0 prompt)

## 5 Memory Abilities Tested

1. **Information Extraction** — basic fact recall
2. **Multi-Session Reasoning** — cross-session inference
3. **Knowledge Update** — handling contradictions over time
4. **Temporal Reasoning** — time-aware questions
5. **Abstention** — knowing when you don't know

Our architecture's strengths (decay floors, conflict detection, temporal awareness) align well with abilities 3-5.

## Integration Plan

1. Download LongMemEval dataset (JSONL format)
2. Implement conversation ingestion pipeline
3. Use GPT-4o binary judge for evaluation (match ENGRAM protocol)
4. Compare against ENGRAM's 71.40% and full-context 56.20% baselines

## Evaluation

LongMemEval uses binary accuracy (GPT-4o judges "yes" or "no"):

```
Prompt: "Given the question and reference answer, does the predicted answer
         correctly capture the key information? Answer yes or no."
```

Score = % of "yes" judgments across 500 questions.
