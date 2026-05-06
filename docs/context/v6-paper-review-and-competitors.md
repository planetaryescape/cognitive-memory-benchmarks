# v6 Paper Review + Competitor Context

Durable context from pasted paper-review / competitor-analysis chats. Treat this as a checklist, not primary evidence. For numbers, prefer `experimentlog.md`, `experimentlog_v2.md`, and result JSONs.

## Claim Framing

Best paper frame:

> We advance the state of the art along memory lifecycle dynamics and availability/accessibility, while remaining competitive with recent memory systems on standard benchmarks.

Use:

- `competitive with`
- `comparable under aligned protocol`
- `within X points of`
- `complements`
- `advances SOTA along [specific axis]`

Avoid unless strictly apples-to-apples:

- `state of the art`
- `surpasses`
- `#1`
- `beats`
- broad “no other system” claims

Strong axis for this paper:

- middle of memory lifecycle, not just write/read
- retention dynamics with floors and reinforcement
- availability = memory still present, modeled by `R(m)`
- accessibility = memory can surface under retrieval competition, modeled by `R(m)^alpha`
- reversible consolidation / core promotion / deep recall
- retrieval-vs-utilization diagnostics

## v6 Results To Cite

Canonical local results:

- LoCoMo Run A: 44.8 overall token F1, 48.5 multi-hop token F1, 59.4 LLM judge, 1540 QA.
- LongMemEval-S Run B: 70.2 task-average, 72.8 overall. Near ENGRAM 71.4 task-average, not a clear surpass claim.
- Decay comparison Run C: power-law 30.4 vs exponential 26.8 on LoCoMo conv0, +3.6 F1.
- Oracle evidence Run E: 63.9 LoCoMo F1 with Mem0-style prompt re-run. Call this an oracle evidence baseline unless prompt/settings exactly match the main run.
- Judge reliability: kappa 0.879, 94% raw agreement, 3 disagreements.

Do not cite evidence Recall@k, utilization probe, or efficiency table as completed unless verified in logs/artifacts.

## Paper Fact-Check Fixes

- `0.02^0.3 ~= 0.309`, not 0.29.
- Effective floor multiplier is `0.309 / 0.02 ~= 15.5x`, not 14.5x.
- With similarity 0.9, score is `0.9 * 0.309 ~= 0.278`, not 0.26.
- If `beta_c` appears in the denominator of `exp(-dt / (S B beta_c))`, it is a time constant, not a decay rate. Larger `beta_c` slows forgetting.
- Avoid “one extraction call + one answer call” when reranking is enabled. Use: ingestion-time extraction call, query-time answer call, optional query-time rerank call.
- Avoid “no external databases.” Use: no managed external vector DB required for reported experiments; local backend used.
- Do not imply Ebbinghaus proves a single exponential forgetting law. Say exponential is an engineering surrogate/prior; Appendix A tests sensitivity.
- Do not claim DialSim was evaluated unless results are actually present.
- Do not claim FadeMem omitted 1000/500 capacity caps or dormancy pruning if the paper states them. Critique missing prompts/scripts/hyperparameters only if verified.
- Mem0 arXiv `2504.19413` is 2025, not 2024.
- TiMem `76.88` rounds to 76.9, but its two LLM calls are recall planning/gating plus answer generation. Count query-time calls consistently.
- LongMemEval comparisons need judge-model caveats, especially GPT-4o vs GPT-4o-mini.

## Recommended Contribution Wording

Abstract-style:

> We achieve competitive performance on LoCoMo and LongMemEval-S while advancing memory lifecycle dynamics through an explicit retention-and-reinforcement model and an availability-accessibility retrieval formulation.

Contribution bullets:

> Our contributions focus on the middle of the memory lifecycle: (i) explicit retention dynamics with floors and reinforcement, (ii) operationalizing availability vs accessibility via `R` and `R^alpha`, (iii) reversible consolidation and deep recall, and (iv) diagnostics that separate retrieval quality from answer utilization.

Comparison caveat:

> Rather than optimizing a specialized retriever for a single benchmark, we focus on a general-purpose lifecycle layer that remains competitive on standard evaluations.

## Supermemory Notes

External/current claims must be re-checked before public citation.

Pasted analysis claimed Supermemory reports:

- LongMemEval-S 81.6 with `gpt-4o`
- 84.6 with `gpt-5`
- 85.2 with `gemini-3-pro-preview`
- Full-context `gpt-4o` baseline 60.2
- Zep `gpt-4o` baseline 71.2

Working interpretation:

- LongMemEval-S result looks plausible, not obviously leaked.
- Treat as company-reported result backed by an open harness, not a gold-standard leaderboard.
- Their LoCoMo-is-insufficient framing is advocacy. LongMemEval-S may be more production-like, but LoCoMo remains a serious benchmark with evidence annotations.
- Their delta row appears to be relative percentage improvement, not percentage-point gain.
- Provider comparison may not be apples-to-apples: pasted code review said orchestrator asks for limit 10, while Supermemory provider hardcodes limit 30 and hybrid search.
- Provider-specific answer prompts mean the score measures memory backend + retrieval packaging + answer prompt.
- Judge implementation may be benchmark-aligned but not official-script identical.
- Retrieval metrics bug reported in pasted analysis: recall@k behaves like hit@k when any relevant item is retrieved. This does not directly invalidate answer accuracy, but weakens retrieval-metric claims.
- README-style blanket `#1 on LongMemEval, LoCoMo, and ConvoMem` should be treated as unstable/outdated unless re-verified.

Safe related-work phrasing:

> Supermemory reports strong LongMemEval-S performance using an open benchmark harness, but strict apples-to-apples comparison is limited by provider-specific retrieval budgets, answer prompts, and judge implementation details.

