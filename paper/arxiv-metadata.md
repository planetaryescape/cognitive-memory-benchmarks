# arXiv Metadata Draft

## Title

Cognitive Memory for AI Agents: Decay Floors, Emergent Core Memories, and Retrieval-Driven Reinforcement

## Authors

Bhekani Khumalo

## Abstract

Most AI memory systems focus on two lifecycle edges: deciding what to extract and deciding how to retrieve it. The middle - what happens after a memory is stored but before it is retrieved - remains less settled. This paper presents cognitive-memory, an open-source memory architecture for LLM-based agents that treats memory as a dynamic lifecycle rather than a static vector index. The system combines decay floors, emergent core-memory promotion, two-tier retrieval reinforcement, associative linking, tiered hot/cold/stub storage, and reversible consolidation. Faint memories can become hard to retrieve without being immediately discarded, and retrieval itself changes future accessibility. We situate the design in cognitive-science work on forgetting, availability versus accessibility, and spreading activation, then evaluate it on LoCoMo, LongMemEval-S, and a controlled long-term-interaction benchmark. On LoCoMo, empirically tuned cognitive-memory defaults reach 46.2% overall F1 and 51.3% multi-hop F1; on LongMemEval-S, it reaches 71.6% task-averaged accuracy, competitive with ENGRAM-class single-stage systems but behind higher-scoring or differently configured recent architectures. A controlled benchmark retains 100% of identity-critical facts across a 30-day mixed-access window, while also exposing likely over-promotion to core status.

## Comments

27 pages, 9 tables, 3 figures. Code and benchmark artifacts available at https://github.com/planetaryescape/cognitive-memory and https://github.com/planetaryescape/cognitive-memory-benchmarks.

## Suggested Categories

Primary: cs.AI

Secondary: cs.CL, cs.LG

## License

Recommended: CC BY 4.0
