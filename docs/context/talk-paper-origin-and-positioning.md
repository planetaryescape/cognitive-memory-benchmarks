# Talk/Paper Origin and Positioning Context

Source: early conversation about an internal tech talk and first arXiv paper draft, 2026-02-26 onward. This is narrative/context only. Do not infer current benchmark truth from this file; use `experimentlog.md`, `experimentlog_v2.md`, and result JSONs for results.

## Core narrative

The original talk idea was: start with agentic memory in general, briefly use the CoALA taxonomy to orient engineers, then focus on effective forgetting as the unsettled middle of the memory lifecycle.

Durable framing:

- Most memory systems innovate at the edges: extraction and retrieval.
- The middle is the interesting gap: what happens after a memory is stored and before it is retrieved.
- A memory should not sit at day-one weight forever.
- Forgetting is not just human mimicry; it is an engineering tool for signal-to-noise, stale context, and decision quality.

Good phrasing:

> Most AI memory systems innovate at the edges: deciding what to remember, and how to retrieve it. But the middle, what happens to a memory after it is stored and before it is retrieved, is a dead zone.

Avoid claiming "forgetting is unsolved." Better:

- Forgetting is an active, fast-moving frontier.
- There is no settled consensus on the right architecture.
- Cognitive Memory is one design in that live conversation.

## Talk Registration

Working title:

> How to Make AI Agents Forget (and Why That's Important)

Registration abstract used as the base:

> Most AI memory systems innovate at the edges: deciding what to remember, and how to retrieve it. But the middle - what happens to a memory after it's stored and before it's retrieved - is a dead zone. Memories sit there with the same weight they had on day one, whether they're an hour old or a month old, accessed fifty times or never.
>
> In this talk I'll briefly map the landscape of agentic memory using the CoALA framework, then zoom in on forgetting, the part that's still unsettled, and where the most interesting work is happening right now. Drawing on cognitive science (Ebbinghaus decay curves, spaced repetition, associative linking, and synaptic tagging), I'll walk through a memory system I built where important memories persist, trivial ones fade, and nothing is ever fully lost. I'll cover decay floors, core memory detection, two-tier retrieval boosting, and how retrieval itself reshapes what an agent remembers backed by real usage data from a production chat application. The session includes a live demo of my open-source cognitive-memory SDK showing how to wire this into your own agents.

If reused, update "nothing is ever fully lost" to account for current TTL/stub policy.

## Suggested Talk Arc

For a one-hour engineering audience:

1. Hook with two memories that are semantically similar but should not rank the same.
2. Minimal CoALA framing, 3-5 minutes.
3. The lifecycle gap: extraction/retrieval get attention; memory dynamics are underdeveloped.
4. Consolidation as the common answer, and why lossy consolidation is not enough.
5. Cognitive science foundations: forgetting curves, spaced repetition, spreading activation, availability/accessibility.
6. Architecture: decay floors, core promotion, two-tier boosting, associations, hot/cold/stub tiers, deep recall.
7. Demo using pre-seeded notebooks rather than live compressed-time decay.
8. Evidence and open questions.

Demo guidance:

- Prefer pre-seeded memories with different timestamps/states over "30 seconds = 1 day" live time simulation.
- Show a faint memory being retrieved and boosted.
- Show a core memory staying strong.
- Show association/deep recall behavior separately from normal retrieval.

## Consolidation Critique

Consolidation should be addressed directly because many systems use it as their forgetting story.

Useful critique:

- Consolidation is a form of forgetting, but it can be lossy.
- If originals are deleted, details summarized away are gone when later needed.
- An LLM deciding what to keep is making a prediction about future relevance without a reliable framework.
- Cognitive Memory's better framing is reversible consolidation: summary in hot memory, originals in cold storage during dormancy, deep recall for exact details, TTL/stub policy for bounded storage.

Good line:

> Consolidation is forgetting with amnesia; decay is forgetting with a trail.

Use carefully; it is punchy, but may be too informal for the paper.

## Core Memory Detection

Early idea: LLM tags obvious core facts at extraction.

Better architecture: dual path.

- Explicit: LLM can mark obvious identity/safety facts as core at extraction.
- Emergent: memories can earn core status through access count, stability, and cross-session recurrence.

The emergent path is more cognitively plausible and more domain-general than a static example dataset. A dataset of "core-like" examples may catch common facts like names/allergies/family, but it will miss domain-specific core facts.

## Observability

Audit logging belongs in the SDK because the SDK is where memory state changes happen.

Useful event types:

- retrieval boost
- associative boost
- decay recalculation/snapshot
- association strengthened/decayed
- core promotion/demotion
- cold migration
- cold revival
- consolidation
- TTL/stub conversion
- conflict detection/resolution

Keep logs cheap:

- memory id
- event type
- old/new numeric values or status
- timestamp
- source query/session id if available

Avoid storing full user content in audit rows by default.

Useful derived charts:

- single-memory lifecycle over time
- average half-life by category
- revival rate from faint/cold states
- core-promotion distribution
- hot/cold/stub counts over time

## Deep Recall SDK Guidance

Deep recall should be exposed as a search/retrieval parameter, not as a global mode.

The SDK should stay unopinionated about when to enable it. Consumers can build:

- LLM-decided deep recall: the agent sets `deepRecall: true` when the user asks for exact old wording, archived details, or something likely consolidated.
- Automatic fallback: run normal retrieval first; if top scores are weak, retry with deep recall.
- Combined approach: honor explicit agent choice first, fallback second.

This belongs in SDK documentation more than the paper.

## Paper Origin

Initial paper goal:

- 6-8 page arXiv architecture/system paper.
- Establish priority and articulate design philosophy.
- No overclaiming against FadeMem or other concurrent work.
- Empirical production-data paper later.

The paper later evolved into a benchmark-backed paper. Keep the origin context useful, but current paper claims must be verified against current `paper/paper.tex`, `experimentlog.md`, and result files.

## Claim Guardrails

Avoid:

- "Nobody is working on forgetting."
- "Forgetting is unsolved."
- Comparing LLM-judge scores against competitor token-F1 scores.
- Claiming "highest published" without checking E-mem, MemoryOS, TiMem, EverMemOS, and newer systems.
- Claiming "only system where multi-hop exceeds single-hop"; MemoryOS also shows that pattern.
- Treating pasted chat numbers as canonical.

Prefer:

- "Forgetting remains unsettled."
- "The field lacks consensus on memory lifecycle dynamics."
- "Our contribution is architectural and reproducibility-oriented."
- "Token F1 and judge scores are reported separately."
- "LongMemEval-S result is competitive with concurrent single-stage systems, not SOTA once newer multi-stage systems are included."

## Editor Feedback To Preserve

Important corrections from later editor review:

- Use token-F1 for apples-to-apples LoCoMo comparisons.
- E-mem's multi-hop number means any "highest published" claim needs checking.
- LongMemEval should be named precisely as LongMemEval-S when using the Small variant.
- The abstract/contribution count should only list architectural contributions; implementation features like extraction modes and conflict resolution can be discussed without inflating contribution count.
- Flush LaTeX floats before the bibliography so the final PDF appears complete.

## Fact-Check Traps From v5 Review

Source: rigorous fact-check + peer-review pass before planned arXiv submission.

Treat these as recurring checks before any public paper build:

- ENGRAM authorship: cite ENGRAM as Patel and Patel, not Anagnostidis et al.
- Mem0 year: check whether the relevant arXiv entry is 2025, not 2024.
- ENGRAM architecture: do not describe it as "multi-stage routing" if referring to its single lightweight router / typed-store design.
- TiMem score: use precise 76.88% when citing the LongMemEval-S number, unless deliberately rounded.
- ENGRAM LoCoMo: if reporting LoCoMo judge comparisons, include or explicitly discuss ENGRAM's LoCoMo judge result. Do not omit a stronger competitor silently.
- LongMemEval-S judge comparability: if our run uses `gpt-4o-2024-08-06` and ENGRAM used `gpt-4o-mini`, do not claim a clean apples-to-apples win without caveat or rerun.
- Prompt effects: if an ablation shows prompt/metadata formatting produced a larger gain than an architectural change, explain why that happened. In earlier work, exposing low-retention metadata made the model over-answer "I don't know"; fixing that was partly a prompt/format bug, not a pure architecture gain.
- "Never delete" language: introduction/abstract must align with TTL/stub policy. Prefer "by default" or "never abruptly delete full memories" framing.
- Absolute novelty claims: soften "not present in any other published system" to "to our knowledge" unless a systematic review supports the stronger claim.
- LoCoMo question count: explain when adversarial category is excluded, since LoCoMo has about 2,000 questions but reported runs may score 1,540.
- Mem0 multi-hop number: Mem0 appears as 28.37 or 28.64 depending on source/evaluation. Footnote if needed; do not mix sources casually.

Peer-review smells to check:

- Are judge scores being compared only to judge scores, and token-F1 only to token-F1?
- Are competitor claims fair enough that the competitor authors would recognize their own systems?
- Is the largest empirical gain framed honestly, even if it is prompt-related?
- Are current implementation features described as implemented only if verified in code?
- Does the paper end with complete references, not floated figures after bibliography?

## Paper Artifact Process Lessons

The source of truth can drift between PDF, `.tex`, and generated artifacts. In one review round, the uploaded PDF represented a newer v5 while local `paper.tex` appeared older. Before editing:

- Identify which artifact is canonical for that task.
- Prefer editing real source when available.
- If reconstructing from a PDF, mark that clearly and reconcile back into source.
- Build a fresh PDF after edits and inspect the last page, references, figure placement, and citation rendering.
- Keep figure PDFs/JPEG conversions self-contained for arXiv source bundles.

## ArXiv/Visibility Notes

ArXiv endorsement is a spam filter, not a quality endorsement.

Likely useful outreach categories:

- authors of closely related papers cited by the work
- survey/paper-list maintainers in agent memory
- AI engineering community builders for visibility after publication

Swyx/Latent Space is a visibility contact, not an obvious arXiv endorser.

## ACH/FaithBench Aside

ACH reviewer invitation context is unrelated to Cognitive Memory but may matter for academic profile-building around FaithBench. The revised judgment was: accepting can be strategically useful if the review load is manageable, because FaithBench sits at AI evaluation + humanities/religion.
