# Cognitive Memory — Architecture Walkthrough

The cognitive-memory SDK is a memory layer for LLM agents that implements biologically-inspired decay, retrieval-driven reinforcement, and emergent core memory promotion. This is the conceptual walkthrough. For the line-by-line code map, see [`sdk-internals.md`](./sdk-internals.md).

## 1. The problem this is trying to solve

Most agent memory systems are good at two things: **extracting** salient information from conversations, and **retrieving** relevant memories on demand. They're bad at the *middle phase* — what happens to a memory after it's stored and before it's retrieved.

Concretely, the failure modes the architecture is designed to avoid:

- A user mentioned their dog's name once on day 1 and again on day 30 — the system treats both as equally fresh information.
- A user said "I'm allergic to peanuts" once 6 months ago — the system has no way to flag this as critical and protect it from being out-prioritised by yesterday's "I had pasta for lunch" turn.
- A user said something contradictory to an earlier memory — the system either keeps both at full weight or destroys one without trace.
- The system aggressively summarises old memories into one-line tldrs to save space — and now the original detail is gone forever.
- Storage grows unboundedly because every turn produces a memory and nothing ever leaves.

The architecture targets all of these via six interlocking design commitments.

## 2. The six design commitments

### 2.1 Decay floors (memories never reach zero)

Every memory has a retention score `R ∈ [0, 1]`. Retention drops over time according to an Ebbinghaus-inspired curve, but **never goes to zero**. There are two floors:

- **Regular memories**: floor at 0.02 (faint but recoverable)
- **Core memories**: floor at 0.60 (always strongly retrievable)

The retention formula (Equation 1 in the paper):

```
R(m) = max(floor, exp(-Δt / (S · B · β_c)))
```

Where:
- `Δt` = days since last access
- `S` = stability (0..1, grows with retrievals via spaced repetition)
- `B` = importance boost = `min(3.0, 1 + 2·importance)`
- `β_c` = category-specific base decay rate (episodic 45 days, semantic 120 days, core 120 days, procedural ∞)
- `floor` = 0.60 if core, else 0.02

There's also a **power-law variant** (Equation 1'):

```
R(m) = max(floor, (1 + Δt / (S · B · β_c))^(-γ))
```

where `γ = 1/ln(2) ≈ 1.4427`. The power-law variant fits long-horizon human memory better and gave +3.6pp F1 over exponential on LoCoMo conv 0 (Run C). Exponential remains the SDK default; power-law is opt-in via `decayModel: "power"`.

**Why floors matter.** Without a floor, faint memories vanish. With a floor, even a six-month-old once-mentioned fact is recoverable when the right cue arrives. This mirrors Tulving's *availability vs accessibility* distinction in cognitive science: a memory can be unavailable for retrieval (decayed past usable score) without being erased.

### 2.2 Emergent core memory promotion

A memory becomes "core" through one of two paths:

1. **Explicit tagging at extraction.** The LLM extractor classifies whether a turn carries identity-critical information (name, allergy, family relationship, medical condition) and tags it as core immediately. Core memories get the 60% retention floor from creation.

2. **Emergent promotion through use.** A memory not initially tagged as core is promoted when *all three* of these criteria hold:
   - `accessCount ≥ coreAccessThreshold` (default 10)
   - `stability ≥ coreStabilityThreshold` (default 0.85)
   - `sessionIds.length ≥ coreSessionThreshold` (default 3 distinct sessions)

The third criterion is the important one. A memory that's accessed 10 times all in one session isn't necessarily important — it's just topically relevant *right now*. A memory that surfaces across 3 separate sessions has demonstrated cross-context relevance.

When promoted, the memory's category changes to `core` and its retention floor jumps from 2% → 60%. Future decay can never push it below the 60% line. It also stops being a candidate for cold-tier migration and TTL expiry.

In the paper's Figure 1 (Monte Carlo analysis), 76.8% of *directly retrieved* memories cross the core threshold by day 90 across 500 randomised retrieval schedules; **0%** of memories that were only ever retrieved associatively make it. This is the empirical justification for the two-tier boosting design (Section 2.3).

### 2.3 Two-tier retrieval boosting

When a memory is retrieved, it gets a *stability* boost. The boost size depends on whether the memory was retrieved directly or pulled in associatively:

- **Direct retrieval boost** (default 0.1): Applied to memories that were the primary semantic match for a query.
- **Associative retrieval boost** (default 0.03): Applied to memories that came along for the ride because they were associatively linked to a directly retrieved memory.

The boost scales with *spaced repetition factor*: `min(maxMultiplier, daysSinceLastAccess / spacedRepIntervalDays)`. A memory accessed today and last accessed 14 days ago gets a 2× multiplier (the cap). Closer accesses get smaller boosts.

```
new_stability = min(1.0, old_stability + boost · spacing_factor)
```

The two-tier design models the cognitive distinction between **active recall** (direct retrieval — strong reinforcement) and **passive priming** (associative co-retrieval — weak reinforcement). Both happen during a single search; both leave a trace; but the directly-recalled memory gets reinforced more.

### 2.4 Bidirectional weighted associations

Memories form weighted, directional links to each other. Two mechanisms create them:

1. **Synaptic tagging at ingestion.** When multiple memories are extracted from the same conversation, any pair with cosine similarity > 0.4 gets bidirectional associations. (Python: weight scales with excess similarity above the threshold; TypeScript: weight = `sim * 0.5`.) This is "memories that arrived together get linked."

2. **Co-retrieval strengthening at retrieval.** When two memories appear together in the same direct-result set, their mutual association weight increments by `associationStrengthenAmount` (default 0.1). This is "memories that surface together get linked."

Associations decay too. Each link has a `lastCoRetrieval` timestamp and an effective weight that decays exponentially with a 90-day time constant. Below the `associationRetrievalThreshold` (default 0.3), an association is too faint to follow at retrieval time. This bounds graph density without hard pruning — weak links just stop being followed.

### 2.5 Tiered hot/cold storage

Memories live in one of three tiers:

- **Hot**: indexed in the vector store, fully searchable.
- **Cold**: out of the vector index but still in the database. Reachable only via deep recall or association traversal.
- **Stub**: lightweight pointer (id + summary content + association references), no embedding. Used for memories absorbed into a consolidation summary or expired from cold storage after TTL.

A memory migrates hot → cold when it has spent N consecutive maintenance cycles at the retention floor (default 7 days). The hot index size therefore stays bounded — the paper's Figure 3 shows hot index converging to 7–11% of total memories across six different access patterns over a simulated year.

A memory migrates cold → hot when it gets retrieved (e.g., via deep recall or association traversal that surfaces a cold target). This models reactivation: a faint memory becomes available again when something cues it.

A memory migrates cold → stub after `coldStorageTtlDays` without reactivation (default 180 days). This bounds full-memory storage while preserving a small trace. TTL is the current architecture, not a speculative future concession.

**Deep recall** is a query mode that:
- includes superseded memories (normally filtered out)
- searches across hot AND cold tiers
- applies a `deepRecallPenalty` (default 0.5×) to scores so deep-recalled memories don't outrank hot direct matches

Deep recall is the computational analogue of "silent engrams" in neuroscience — memories that exist in storage but are inaccessible through normal cues, recoverable only through artificial stimulation.

### 2.6 Reversible consolidation

Consolidation is the field's standard answer to "memories grow unboundedly": cluster faint memories by semantic similarity, summarise the cluster into a compressed memory, delete the originals.

Consolidation itself does not delete originals. Instead:

1. Find clusters of fading memories (retention < 0.20, group size ≥ 5, pairwise cosine ≥ 0.70).
2. LLM-summarise each cluster into a single new memory.
3. Mark the originals as `superseded` with `supersededBy = summaryId`. Keep them in cold storage.
4. Add bidirectional associations from summary to each original.

Result: the summary takes the foreground; the originals remain recoverable via deep recall or by following associations from the summary during their cold-storage dormancy window. If the summary turns out to be lossy or wrong for a future query, the system can still get to the original before TTL expiry; after TTL, only the lightweight stub remains.

## 3. Data model

A memory is represented with the following key fields (full schema in [`spec/memory-schema.md`](../../cognitive-memory-sdk/spec/memory-schema.md) and TS types in `sdks/typescript/src/core/types.ts`):

| Field | Type | Purpose |
|---|---|---|
| `id` | UUID | Primary key |
| `userId` | string | Multi-tenancy (TS only; Python passes user_id at API level) |
| `content` | string | The actual text |
| `embedding` | float[] \| null | Dense vector (null for stubs) |
| `category` | enum | `episodic` / `semantic` / `procedural` / `core` — controls decay rate and floor |
| `semanticType` | enum | `fact` / `preference` / `plan` / `transient_state` / `other` — orthogonal classification, used for validity filtering |
| `importance` | float | 0..1, set at extraction (boost factor in decay formula) |
| `stability` | float | 0..1, grows with retrievals (rate factor in decay formula) |
| `accessCount` | int | Lifetime retrieval count |
| `lastAccessed` | timestamp | Used for `Δt` in decay |
| `retention` | float | Cached current retention (TS only — Python computes on the fly) |
| `associations` | map[id → Association] | Bidirectional weighted links |
| `sessionIds` | string[] | Sessions where this memory was created or accessed |
| `isCold`, `coldSince`, `daysAtFloor` | tiering state | Tracks hot/cold migration |
| `isSuperseded`, `supersededBy` | replacement chain | For consolidation and conflict resolution |
| `contradictedBy` | string \| null | Set when another memory contradicts this one |
| `isStub` | bool | Lightweight pointer state (post-consolidation) |
| `validFrom`, `validUntil`, `ttlSeconds` | temporal validity (v6) | For plans and transient state |
| `sourceTurnIds` | string[] | Provenance; ties memory back to original conversation turns |

### Two orthogonal classification axes

`category` is *temporal*: it determines decay rate and retention floor. It also captures whether the memory is identity-critical (`core`).

`semanticType` (added in v6) is *content type*: facts, preferences, plans, transient states. It's used to enable selective expiry — `transient_state` memories with explicit `validUntil` get filtered out of normal retrieval after expiry, but stay accessible via deep recall.

These two axes are independent. A `core` memory can be a `fact` ("My name is Alex") or a `preference` ("I prefer dark mode"). A `semantic` memory could be a `plan` ("Helios deadline is March 15") that becomes invalid at a specific point.

## 4. The retrieval pipeline (v6)

When a query comes in, it runs through six sequential stages, with optional rerank:

1. **Hybrid candidate generation.** Run dense vector search via `adapter.vectorSearch()`, collecting up to `topK · 3` candidates. If `hybridSearch: true`, also run BM25 lexical search via `adapter.searchLexical()` (a default `topK · 2` candidates), then union with the dense results, dedupe by id, and compute dense similarity for any lexical-only candidates.

2. **Retention scoring + validity filtering.** For each candidate, compute current retention (Equation 1, accounting for power-law if configured), then compute the combined score:

   ```
   score = relevance · retention^α
   ```

   where `α = retrievalScoreExponent` (default 0.3). Apply the deep-recall penalty (×0.5) if the memory is superseded. Filter out memories where `semanticType` is `plan` or `transient_state` AND `validUntil` is in the past (unless `includeExpiredInDeepRecall` and the query is in deep recall mode). Sort descending by combined score.

3. **LLM rerank** (optional). If `rerankEnabled: true`, send the top `kRerank` candidates plus the query to an LLM (defaults to extraction model) for relevance reranking. The LLM returns an ordering; tokens are tracked in the trace. Run A used `kRerank=10`, factor 3.

4. **Direct results selection.** Take the top-k from the (re)ranked list. These are the *direct* results — they get the full direct-retrieval boost.

5. **Associative + graph expansion.** For each direct result, fetch associated memories via `adapter.getLinkedMemories()`, apply association decay (90-day exponential), filter by `associationRetrievalThreshold` (default 0.3). If `graphExpansionHops > 0`, also do a multi-hop BFS from the direct results, accumulating bridge memories (with multiplied edge weights). If `bridgeDiscovery: true`, find multi-path chains between top results.

6. **Boost, promote, persist.** Apply direct boost (default +0.1) to direct results' stability, scaled by the spaced-repetition factor. Apply associative boost (default +0.03) to associative results. Update `accessCount`, `lastAccessed`, `sessionIds`. Migrate cold memories to hot if they were retrieved. Check core promotion thresholds; promote any memory that newly qualifies. Strengthen associations between co-retrieved direct memories. **Persist all mutations** via `adapter.updateMemory()`.

7. **Combine + return.** Merge direct + associative results, sort by combined score, take final top-k. Attach evidence chains (the bridge paths, if any) to the response. Return `SearchResponse` with results, chains, and an optional per-stage trace.

The trace is the v6 instrumentation: each stage records `wallMs`, `candidateCount`, `promptTokens`, `completionTokens`, plus stage-specific metadata. This is what the benchmarks read out of for efficiency tables (Run F).

## 5. The ingestion pipeline

When a conversation turn or batch comes in, ingestion runs through three stages:

1. **LLM extraction.** Send the conversation text to the extraction LLM (default `gpt-4o-mini`) with a prompt that asks for a JSON array of memories with `content`, `category`, `importance`, `memory_type`, optional `valid_from`/`valid_until`/`ttl_seconds`, and `source_turn_ids`. Parse the response (robust to markdown fencing). For each extracted memory, embed it via the embedding provider (default `text-embedding-3-small`, 1536 dims) and `adapter.create()` it. Initial stability is `0.1 + importance · 0.3` so important memories start with a head start.

   Two non-LLM modes exist:
   - `extractionMode: "raw"` — store each turn verbatim as an episodic memory with fixed importance 0.5 and stability 0.2.
   - `extractionMode: "hybrid"` — do both LLM extraction and raw turn storage.

2. **Deferred conflict detection.** For each newly stored memory, search for similar existing memories. If cosine similarity > 0.85, queue `(newId, existingId, sim)` for *deferred* resolution at the next maintenance tick. **No LLM calls happen inline** during ingestion — this was a critical fix made on `refactor/humanize-and-fix-docs` (PR #2) after Run A's first attempt hung on session 19 due to O(N²) inline conflict detection. Same-session-root pairs are skipped (avoids dual-perspective false conflicts).

3. **Synaptic tagging.** For each pair of newly-stored memories from the same ingestion call, compute pairwise cosine similarity. If > 0.4, create a bidirectional association via `adapter.createOrStrengthenLink()`. In the Python SDK, an additional reinforcement also happens: if a new memory is highly similar (> 0.75) to an *existing* memory, the existing memory's stability gets a +0.05 boost (the paper's ingestion-time synaptic tagging). The TypeScript SDK does not currently apply this immediate ingestion reinforcement — only retrieval-time boosts.

4. **Optional maintenance.** If `runMaintenanceDuringIngestion: true` (default), call `tick()` to run deferred conflict resolution, cold migration, TTL expiry checks, and consolidation candidacy.

## 6. Conflict resolution architecture

Conflicts are detected at ingestion (cheap similarity check) but **resolved at maintenance** (expensive LLM call).

### Detection (during ingestion)

When a new memory is stored, search for existing memories with cosine similarity > 0.85. Add each high-similarity pair to a deferred conflict queue. Skip pairs from the same session root (this avoids treating dual-perspective ingestion — where the same conversation is ingested from two viewpoints — as conflict).

This was the critical change. Earlier versions ran the LLM conflict check *inline* during ingestion, which produced O(N²) LLM calls per ingest batch and made Run A hang during session 19. The fix: just queue pairs for later, return ingestion in O(1) extra cost.

### Resolution (during tick / maintenance)

`resolveConflictQueue()` processes up to 50 pairs per tick, sorted by similarity descending:

1. Fetch both memories. Skip if either is already superseded.
2. LLM-classify the relationship as one of: `CONTRADICTION`, `UPDATE`, `OVERLAP`, `NONE`.
3. If `CONTRADICTION` or `UPDATE`:
   - Update the existing memory's content with the new memory's content.
   - Set `existing.contradictedBy = newId`.
   - Preserve importance: `max(existing.importance, new.importance)`.
   - In Python: if existing was `core`, demote to `semantic` (drops the floor from 60% → 2%, allows it to decay naturally). The paper argues this is the right semantics: a contradicted core memory shouldn't keep its protected status.

The 0.85 threshold (raised from an earlier 0.6) cut false-positive conflict candidates from 1422 down to a manageable number on conv 0. False conflicts at low thresholds were the main reason inline resolution exploded.

## 7. Adapter contract

The core engine never touches a database directly. All persistence goes through a `MemoryAdapter` interface defined in [`spec/adapter-interface.md`](../../cognitive-memory-sdk/spec/adapter-interface.md). The contract has:

- **CRUD**: `create`, `get`, `getBatch`, `update`, `delete`, `deleteBatch`
- **Search**: `vectorSearch` (required, dense), `searchLexical` (optional, BM25 for hybrid)
- **Tiering**: `migrateToCold`, `migrateToHot`, `convertToStub`, `allActive`, `allHot`, `allCold`, plus `*Count()`
- **Links**: `createOrStrengthenLink`, `getLinkedMemories`, `deleteLink`
- **Consolidation helpers**: `findFading`, `findStable`, `markSuperseded`
- **Batch**: `batchUpdate`, `updateRetentionScores`
- **Transactions**: `transaction(callback)` (best-effort if backend doesn't support)
- **Reset**: `clear`

In-tree adapters: `InMemoryAdapter`, `JsonlFileAdapter`, `PostgresAdapter` (uses pgvector), `ConvexAdapter`. Users bring their own by implementing the contract.

The hot/cold/stub distinction is enforced by the adapter via `is_cold` and `is_stub` flags; `vectorSearch` is expected to skip cold and stub records by default. `searchLexical` is optional — adapters that don't support BM25 return `[]` and the hybrid pipeline silently degrades to dense-only.

## 8. Production deployment context

The system is deployed in `blah.chat`, a consumer chat application. Each conversation turn:

1. Extracts memories from the turn using an LLM call (debounced/batched in practice).
2. Stores them with initial importance and category.
3. Retrieves relevant memories at the start of the next agent turn, injecting them into the system prompt.
4. Runs decay recalculation periodically (currently on each retrieval event).
5. Checks for emergent core memory promotion after each retrieval cycle.

The deployment includes an append-only audit log capturing every state change: retrieval boosts, decay recalculations, association updates, core memory promotions, consolidation events. Each entry has memory ID, event type, old/new values, timestamp. This is the basis for the planned production-data validation study (Future Work in the paper).

## 9. The cognitive science backing

The architecture cites these specific results:

- **Ebbinghaus forgetting curve** (1885, replicated Murre 2015) — exponential retention decay with steepest drop early.
- **Spacing effect** (Cepeda 2006) — distributed practice produces stronger long-term retention than massed practice. → motivates the spaced-repetition factor in stability boosts.
- **Spreading activation** (Collins & Loftus 1975) — retrieving one memory partially activates semantically related ones. → motivates associative drag-along.
- **Synaptic tagging hypothesis** (Frey & Morris 1997) — biochemical tags during encoding mark memories for preferential consolidation, independent of subsequent access. → motivates importance-at-extraction.
- **Adaptive forgetting** (Richards & Frankland 2017) — the goal of memory is intelligent decision-making in noisy, changing environments, not faithful recording. → motivates floors-not-deletion.
- **Availability vs accessibility** (Tulving 1966) — apparent forgetting is usually retrieval failure, not storage loss. → motivates deep recall + cold tier.
- **Complementary Learning Systems** (McClelland 1995) — fast hippocampal vs slow neocortical, with gradual migration. → motivates hot/cold tiering.
- **Silent engrams** (Ryan 2022, Guskjölen 2024) — memories can persist biologically while being inaccessible through normal cues, recoverable only through artificial stimulation. → motivates the never-delete policy and deep recall.
- **Intrinsic forgetting** (Davis 2017) — there's evidence of *active* molecular forgetting at the synaptic level. → acknowledged limitation of the never-delete stance.

The paper is honest about the cognitive-science framing being motivating rather than mechanistic. The system isn't simulating biology; it's using biological dynamics as a useful set of design constraints.

## 10. Where the architecture is *competitive* vs *not*

Based on the empirical evaluation in the paper:

**Strengths.**
- 100% retention of identity-critical facts across a 30-day mixed-access window (LTI-Bench v2) vs FadeMem 82.1%.
- Multi-hop F1 of 48.5% on LoCoMo, ~1.7× Mem0's 28.4%. Multi-hop is the category where decay floors and emergent core have the largest plausible benefit, and that's where we win biggest.
- Power-law decay gives +3.6pp on LoCoMo conv 0 — the single largest single-feature contribution measured.
- 70.2% task-averaged accuracy on LongMemEval-S, within 1.2pp of ENGRAM (the strongest concurrent single-stage baseline at the time of running) without any benchmark-specific tuning.

**Weaknesses.**
- **Associative retrieval is partial.** LTI-Bench v2 shows the system returning 1 of 3 family-related facts when queried with "what do you know about my family?". A direct probe for any individual fact succeeds; the failure is specifically in cross-fact / cluster recall.
- **Hybrid search hurts on conversational text** (-1.1pp on conv 0). BM25 introduces noise on natural-language turns that dense embeddings handle better. Hybrid is off by default.
- **Behind newer multi-stage architectures.** TiMem (76.88%) and EverMemOS (83.0%) post-date our run window and exceed our LongMemEval-S accuracy. We're competitive with single-stage memory systems; we are not benchmark-leading on LongMemEval-S as of mid-2026.
- **Single-session-preference is the weak task on LongMemEval-S** (36.7%). Suggests preference extraction in short windows is a capability gap distinct from the long-horizon retention story.

## 11. Reading order for someone new to the architecture

If a future you (or another agent) needs to come up to speed:

1. Read this doc (you're here).
2. Skim [`sdk-internals.md`](./sdk-internals.md) for the file-by-file map and exact retrieval-pipeline line refs.
3. Read [`paper.tex`](../paper/paper.tex) sections 4 (Architecture) and 6 (Evaluation) — these are the canonical statement of the design and what we know about it empirically.
4. Read [`spec/memory-schema.md`](../../cognitive-memory-sdk/spec/memory-schema.md) for the data model in canonical form.
5. Read [`spec/adapter-interface.md`](../../cognitive-memory-sdk/spec/adapter-interface.md) for the storage contract.
6. Browse `sdks/typescript/src/core/engine.ts` (760 lines) — the centre of gravity.
7. Browse `sdks/python/src/cognitive_memory/core.py` (464 lines) for the equivalent on the Python side. Note divergences: ingestion-time stability reinforcement (Python-only) and tick frequency (Python every 5th, TS every ingestion).
