# arXiv Metadata Draft

## Title

Cognitive Memory for AI Agents: Preservation-First Decay, Core Promotion, and Retrieval-Driven Reinforcement

## Authors

Bhekani Khumalo

## Abstract

Most AI memory systems focus on extraction and retrieval, leaving the stored-memory lifecycle under-specified. We present cognitive-memory, an open-source agent-memory architecture that treats forgetting as reduced accessibility rather than immediate deletion. Memories decay through configurable curves, are reinforced on retrieval, can earn core status through sustained cross-session use, and migrate between hot, cold, and stub states with reversible consolidation and explicit deep recall. On LoCoMo, a v0.5 tuned configuration reaches 46.2% overall F1 and 51.3% multi-hop F1; on LongMemEval-S, a May 2026 current-refresh run reaches 71.6% task-averaged accuracy. A controlled LTI-Bench scenario recovers all identity-critical facts after 30 days, but a floors-off ablation shows unchanged critical retention, suggesting stability accumulation and softened retention weighting are more load-bearing than floor-clamping in this horizon. These results position cognitive-memory as a competitive single-stage memory architecture and expose open questions around longer-horizon decay, core-promotion thresholds, and associative retrieval.

## Comments

28 pages, 10 tables, 3 figures. Code and benchmark artifacts available at https://github.com/planetaryescape/cognitive-memory and https://github.com/planetaryescape/cognitive-memory-benchmarks.

## Suggested Categories

Primary: cs.AI

Secondary: cs.CL

## License

Recommended: CC BY 4.0
