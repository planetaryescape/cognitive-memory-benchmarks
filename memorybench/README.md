# MemoryBench (2025)

Multi-dataset benchmark for evaluating memory systems. 11 datasets, 20K+ test cases.

**Goal**: Debunk the claim that "no memory system consistently beats RAG" (MemoryBench paper, Table 3).

## Status: Scaffolded

Integration pending. Priority: after LongMemEval.

## Competitor Parameters

### Mem0

From MemoryBench evaluation:
- **Backbone LLM**: Qwen3-8B (vLLM, port 12366)
- **Embedding**: Qwen3-Embedding-0.6B (1024 dims, vLLM port 12377)
- **Temperature**: 0.1
- **retrieve_k**: 10 (agent default) / 5 (reported in some configs)
- **Interface**: BaseSolver + BaseAgent
- **Note**: Failed on Open-Domain and LiSo tasks due to context length

### RAG Baselines

- **BM25-S/M**: BM25 retriever, k=5, session/message granularity
- **Embed-S/M**: Qwen3-Embedding-0.6B, k=5, session/message granularity
- **Backbone**: Qwen3-8B, temp=0.1

### FadeMem

**Not evaluated on MemoryBench.**

## Our Three Run Types

1. **Apples-to-apples with Mem0**: Qwen3-8B backbone, k=10, match their embedding model
2. **Benchmark pure**: Follow MemoryBench official BaseSolver protocol exactly
3. **Best tuned**: Our optimal config (text-embedding-3-small, k=60, deep recall, LLM re-rank)

## Integration Plan

1. Clone MemoryBench repo, implement BaseSolver wrapper
2. Set up vLLM with Qwen3-8B for apples-to-apples comparison
3. Run all 11 datasets
4. Compare against Mem0, RAG-BM25, RAG-Embed baselines

## Key Datasets

- Multi-Session Chat, Knowledge Update, Temporal Reasoning — our strengths
- Open-Domain, LiSo — Mem0 failed here, opportunity to differentiate
