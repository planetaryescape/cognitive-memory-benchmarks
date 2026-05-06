# arXiv Metadata Draft

## Title

Cognitive Memory for AI Agents: Decay Floors, Emergent Core Memories, and Retrieval-Driven Reinforcement

## Authors

Bhekani Khumalo

## Abstract

Most AI memory systems innovate at the edges of the memory lifecycle: deciding what to extract and how to retrieve it. The middle, what happens to a memory after it is stored and before it is retrieved, remains comparatively underexplored. Memories persist at the same weight they had on day one, whether they are an hour old or a month old, accessed fifty times or never. This paper presents cognitive-memory, an open-source memory architecture for LLM-based agents that draws on cognitive science to address this gap. We introduce six design contributions: decay floors, where memories fade according to Ebbinghaus-inspired exponential decay but never reach zero, preserving the possibility of future reactivation; emergent core memory detection, where memories earn protected status through repeated access and cross-session stability rather than only through explicit tagging; two-tier retrieval boosting, where direct retrieval and associative co-retrieval produce different reinforcement magnitudes, modelling the distinction between active recall and passive priming; associative memory linking with differential reinforcement, where co-retrieved memories form and strengthen bidirectional connections; tiered hot/cold storage inspired by the Complementary Learning Systems framework and Tulving's availability-accessibility distinction, where faint memories migrate out of the vector index but remain recoverable through associative retrieval or explicit deep recall; and reversible consolidation, where superseded originals are preserved in cold storage rather than deleted, accessible as associated children of their summaries or via a deep recall retrieval mode analogous to the reactivation of silent engrams. We situate these mechanisms within the broader landscape of agent memory research, contrast our design philosophy with recent work such as FadeMem, describe a production deployment backing a consumer chat application, and report an empirical evaluation on LoCoMo and LongMemEval-S along with a controlled long-term-interaction benchmark. On LoCoMo we recover an overall F1 of 44.8% with multi-hop F1 of 48.5%; on LongMemEval-S we reach 70.2% task-averaged accuracy, competitive with ENGRAM-class single-stage memory systems; ablations indicate that power-law decay is the single largest contributor; and on the controlled benchmark we retain 100% of identity-critical facts across a 30-day mixed-access window.

## Comments

25 pages, 9 tables, 3 figures. Code and benchmark artifacts available at https://github.com/planetaryescape/cognitive-memory and https://github.com/planetaryescape/cognitive-memory-benchmarks.

## Suggested Categories

Primary: cs.AI

Secondary: cs.CL, cs.LG

## License

Recommended: CC BY 4.0
