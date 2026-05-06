# Cognitive Memory — Working Docs

Internal docs for the cognitive-memory project. Organised so a future-you (or a fresh agent session) can rebuild context fast without re-reading source.

These are **operator notes**, not the public-facing docs. The public Astro docs live at `cognitive-memory/docs/`. The Confluence-style truth is the code; these notes are the map.

## Contents

| File | What's in it |
|---|---|
| [`architecture.md`](./architecture.md) | Comprehensive walkthrough of cognitive-memory architecture: decay model, core promotion, two-tier boosting, associations, consolidation, tiered storage. The big one. |
| [`sdk-internals.md`](./sdk-internals.md) | Code-level walkthrough: file map, retrieval pipeline stages with line refs, ingestion pipeline, conflict resolution architecture, TS vs Python divergences. |
| [`repo-layout.md`](./repo-layout.md) | Where everything lives across the two repos post-move. Key paths, build commands, version pins. |
| [`benchmarks-overview.md`](./benchmarks-overview.md) | All benchmark runs A–M: methodology, results, how to reproduce, caveats. |
| [`lti-bench.md`](./lti-bench.md) | LTI-Bench in detail: scenario, probe taxonomy, v1→v2 evolution, scoring, known weaknesses. |
| [`paper.md`](./paper.md) | Paper status, build pipeline (tectonic), section map, what's done vs pending. |
| [`lessons-and-gotchas.md`](./lessons-and-gotchas.md) | Captured learnings from working on this: things that bit us, principles to apply next time. |
| [`next-steps.md`](./next-steps.md) | Queued work — explicit handoff so future sessions don't waste cycles re-discovering. |
| [`context/reviewer-feedback-memory-lifecycle.md`](./context/reviewer-feedback-memory-lifecycle.md) | Reviewer/context capture on never-delete framing, cold-storage TTL, SDK scope, benchmark canon rules. |
| [`context/talk-paper-origin-and-positioning.md`](./context/talk-paper-origin-and-positioning.md) | Origin narrative for the work talk/paper, positioning, deep recall docs guidance, and claim guardrails. |
| [`context/v6-paper-review-and-competitors.md`](./context/v6-paper-review-and-competitors.md) | v6 paper-review fixes, final framing language, canonical result caveats, and Supermemory competitor notes. |

## When to read what

- **"What does this system do?"** → `architecture.md`
- **"Where is X in the code?"** → `sdk-internals.md` or `repo-layout.md`
- **"What's the state of the paper?"** → `paper.md`
- **"What benchmark numbers do we have?"** → `benchmarks-overview.md`
- **"Why is the LTI scenario set up this way?"** → `lti-bench.md`
- **"What did we learn the hard way?"** → `lessons-and-gotchas.md`
- **"What should I work on next?"** → `next-steps.md`
- **"What did pasted reviewer/chat context imply?"** → `context/`

## Conventions

- Filenames are lowercase with dashes.
- Line references like `engine.ts:347` mean line 347 of `sdks/typescript/src/core/engine.ts` in the SDK repo.
- Run IDs (A, B, C, …) match the experimentlog.md run registry.
- "v6" refers to the SDK feature set (decay model, hybrid retrieval, graph expansion, validity filtering, instrumentation) added on the `feat/sdk-v6-implementation` branch and merged in PR #1.
