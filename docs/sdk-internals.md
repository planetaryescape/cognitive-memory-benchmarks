# SDK Internals — File Map and Pipeline Walkthrough

This is the code-level companion to [`architecture.md`](./architecture.md). It maps each architectural concept to specific files, classes, and line numbers. Line refs are accurate as of SDK v0.3.0 (post-`905aba7`).

The SDK lives in `~/code/bhekanik/cognitive-memory/sdks/{typescript,python}/`. Both SDKs implement the same architecture; the canonical contracts are in `~/code/bhekanik/cognitive-memory/spec/`.

## 1. Top-level layout

```
cognitive-memory/
├── docs/                    # Public Astro docs site (NOT operator notes; that's this dir)
├── spec/
│   ├── memory-schema.md     # Canonical Memory object (Python + TypeScript side-by-side)
│   └── adapter-interface.md # Canonical adapter contract
├── sdks/
│   ├── typescript/
│   │   └── src/
│   │       ├── index.ts                # Public API surface (71 lines)
│   │       ├── core/
│   │       │   ├── types.ts            # All TS types + DEFAULT_CONFIG (739 lines)
│   │       │   ├── decay.ts            # Eq. 1 retention computation (108 lines)
│   │       │   ├── engine.ts           # CognitiveEngine: retrieval pipeline (760 lines)
│   │       │   ├── extraction.ts       # LLM extraction + conflict + rerank prompts (399 lines)
│   │       │   ├── CognitiveMemory.ts  # Public class wiring the pieces (681 lines)
│   │       │   ├── embeddings.ts       # OpenAI / Hash embedding providers (152 lines)
│   │       │   ├── clustering.ts       # Greedy similarity clustering (40 lines)
│   │       │   └── validation.ts       # Unit-interval assertion (19 lines)
│   │       ├── adapters/
│   │       │   ├── base.ts             # MemoryAdapter abstract class (190 lines)
│   │       │   ├── memory.ts           # InMemoryAdapter (463 lines)
│   │       │   ├── jsonl.ts            # File-backed adapter (756 lines)
│   │       │   ├── postgres.ts         # pgvector adapter (737 lines)
│   │       │   └── convex.ts           # Convex adapter (453 lines)
│   │       └── utils/
│   │           ├── scoring.ts          # Heuristic scoring (importance, topics)
│   │           └── embeddings.ts       # Vector math helpers (cosine, euclid)
│   └── python/
│       └── src/cognitive_memory/
│           ├── __init__.py             # Public re-exports (65 lines)
│           ├── types.py                # Memory dataclass + enums (216 lines)
│           ├── core.py                 # CognitiveMemory class (464 lines)
│           ├── engine.py               # Retrieval engine (798 lines)
│           ├── extraction.py           # LLM extraction (350 lines)
│           ├── embeddings.py           # OpenAI provider (107 lines)
│           ├── _sync.py                # Async-to-sync facade (135 lines)
│           └── adapters/
│               ├── base.py             # MemoryAdapter ABC
│               └── memory.py           # InMemoryAdapter
└── package.json / Makefile / release-please-config.json / LICENSE / README.md
```

## 2. Public API surface

The TypeScript public surface is minimal:

```ts
// from sdks/typescript/src/index.ts
export { CognitiveMemory } from "./core/CognitiveMemory";
export { CognitiveEngine, calculateRetention, updateStability, ... } from "./core";
export { InMemoryAdapter, JsonlFileAdapter, PostgresAdapter, ConvexAdapter, MemoryAdapter } from "./adapters";
export { OpenAIEmbeddingProvider, HashEmbeddingProvider } from "./core";
export { extractFromConversation, detectConflict, rerankCandidates, compressMemories } from "./core";
export type { Memory, MemoryInput, RetrievalQuery, SearchResponse, SearchResult, SearchTrace, StageTrace,
              CognitiveMemoryConfig, ResolvedCognitiveMemoryConfig, ... } from "./core";
```

Python mirrors this through `cognitive_memory/__init__.py` exporting `CognitiveMemory`, `Memory`, `CognitiveMemoryConfig`, the adapter classes, and the embedding provider.

## 3. Configuration

All tunables live in `CognitiveMemoryConfig` (TS: `core/types.ts:316`, Python: equivalent dataclass). Every field has a default in `DEFAULT_CONFIG` (TS: `core/types.ts:549`).

Key defaults to memorise:

| Knob | Default | Notes |
|---|---|---|
| `decayModel` | `"exponential"` | v6 added `"power"` option |
| `powerDecayGamma` | `1.4427` | = 1/ln(2) |
| `defaultStability` | `0.3` | Initial stability for new memories (extraction adjusts up) |
| `coreRetentionFloor` | `0.60` | Eq. 1 floor for core |
| `regularRetentionFloor` | `0.02` | Eq. 1 floor for regular |
| `retrievalScoreExponent` | `0.3` | α in `score = relevance · retention^α` |
| `directBoost` | `0.1` | Direct retrieval stability increment |
| `associativeBoost` | `0.03` | Associative retrieval stability increment |
| `coreAccessThreshold` | `10` | Promotion criterion 1 |
| `coreStabilityThreshold` | `0.85` | Promotion criterion 2 |
| `coreSessionThreshold` | `3` | Promotion criterion 3 (cross-session test) |
| `associationRetrievalThreshold` | `0.3` | Below this weight, association won't be followed at retrieval |
| `associationDecayConstantDays` | `90` | Exponential association decay |
| `consolidationRetentionThreshold` | `0.20` | Below this, candidate for consolidation |
| `consolidationGroupSize` | `5` | Min cluster size to consolidate |
| `consolidationSimilarityThreshold` | `0.70` | Pairwise cosine for clustering |
| `coldMigrationDays` | `7` | Days at floor before hot→cold |
| `coldStorageTtlDays` | `180` | TTL once in cold |
| `deepRecallPenalty` | `0.5` | Multiplier on superseded scores in deep recall |
| `hybridSearch` | `false` | v6; turn on for BM25 + dense union |
| `kSparse` | `30` | BM25 candidate count |
| `rerankEnabled` | `false` | v6; turn on for LLM rerank |
| `kRerank` | `10` | Top-k sent to rerank LLM |
| `graphExpansionHops` | `1` | v6; 0 = disabled |
| `bridgeDiscovery` | `false` | v6 |
| `runMaintenanceDuringIngestion` | `true` | If false, must call `tick()` manually |
| `extractionMode` | `"semantic"` | `"raw"` and `"hybrid"` are alternatives |
| `extractionModel` | `"gpt-4o-mini"` | |
| `embeddingModel` | `"text-embedding-3-small"` | 1536 dims |

Decay rates per category (TS: `core/types.ts:557`):

```
episodic:   45 days
semantic:   120 days
procedural: ∞ (no decay; updated only by correction)
core:       120 days
```

## 4. Decay math (`core/decay.ts`)

The whole file is 108 lines. Two exported functions:

### `calculateRetention(params, config?)` — `decay.ts:48`

Exact implementation:

```ts
const baseDecay = getBaseDecayRate(category, rates);
if (category === "procedural" || baseDecay === Infinity) return 1.0;

const floor = getRetentionFloor(category, config);
const daysSinceAccess = (now - lastAccessed) / (1000 * 60 * 60 * 24);
const importanceBoost = Math.min(3.0, 1.0 + importance * 2.0);
const S = Math.max(stability, 0.01);
const effectiveRate = S * importanceBoost * baseDecay;

const raw = decayModel === "power"
  ? (1 + daysSinceAccess / effectiveRate) ** -gamma
  : Math.exp(-daysSinceAccess / effectiveRate);

return Math.max(floor, Math.min(1, raw));
```

This is Equation 1 in the paper. Note the `S = max(stability, 0.01)` clamp to avoid division-by-zero when stability hasn't been set yet.

### `updateStability(currentStability, daysSinceLastAccess, boost, maxMultiplier, intervalDays)` — `decay.ts:95`

Spaced-repetition aware:

```ts
const spacingFactor = Math.min(maxMultiplier, days / intervalDays);
return Math.min(1.0, currentStability + boost * spacingFactor);
```

A memory accessed today and last accessed 14 days ago: spacingFactor = min(2, 14/7) = 2. With direct boost 0.1, stability gains 0.2. Capped at 1.0.

## 5. Retrieval pipeline (`core/engine.ts`)

The 760-line `engine.ts` is the centre of gravity. The retrieval pipeline runs from `CognitiveEngine.search()` at line 331.

### Pipeline stages with line refs

| Stage | Where | Lines | What |
|---|---|---|---|
| Hybrid candidates | `search()` | 347–382 | `vectorSearch()` + optional `searchLexical()` union, dedupe, compute dense sim for lexical-only |
| Score + filter | `search()` | 384–432 | `computeRetention()`, score = `relevance · retention^α`, deep-recall penalty, expired-transient filter, sort |
| LLM rerank | `search()` → `rerankCandidates()` | 437–478 | Optional; sends top kRerank to LLM, reorders; tokens to trace |
| Direct selection | `search()` | 481 | `scored.slice(0, topK)` |
| Associative + graph | `search()` → `getAssociatedMemories()` / `expandGraph()` | 483–541 | Decay association weights, fetch linked, optional multi-hop BFS, optional bridge discovery |
| Boost + promote | `search()` → `applyDirectBoost()` / `applyAssociativeBoost()` / `checkCorePromotion()` / `strengthenAssociation()` | 543–586 | Stability+, hot migration if cold, core promotion check, association strengthening, **persist via `adapter.updateMemory()` lines 578–585** |
| Combine + return | `search()` | 588–606 | Merge direct + associative, sort, top-k, attach evidence chains |

### Other key functions in `engine.ts`

| Function | Line | Purpose |
|---|---|---|
| `computeRetention(memory, now)` | early | Same as `calculateRetention` from decay.ts; cached on memory.retention in TS |
| `scoreMemory(memory, relevance, now)` | early | `relevance · retention^α`, applies superseded penalty |
| `applyDirectBoost(memory, now)` | 99 | `stability += directBoost · spacingFactor`; bumps accessCount, lastAccessed |
| `applyAssociativeBoost(memory, now)` | 112 | Same with `associativeBoost`; weaker reinforcement |
| `checkCorePromotion(memory)` | 129 | Returns true if all three thresholds hit |
| `strengthenAssociation(a, b)` | ~150 | `weight += associationStrengthenAmount`, capped at 1.0 |
| `getAssociatedMemories(direct, now)` | 175 | Decay weights, filter, sync-fetch from adapter |
| `expandGraph(anchors, hops)` | 227 | Multi-hop BFS, returns bridge memories with multiplied weights |
| `findBridgePaths(anchors, maxPaths)` | ~520 | Finds short paths between top results |
| `tick()` | ~600 | Maintenance: cold migration, TTL expiry, consolidation candidacy |
| `consolidate()` | ~660 | Find fading clusters, LLM-summarise, mark originals superseded, link summary↔originals |

## 6. Ingestion pipeline (`core/CognitiveMemory.ts` + `core/extraction.ts`)

### Public entry points (`CognitiveMemory.ts`)

| Method | Line | Purpose |
|---|---|---|
| `store(input)` | ~100 | Add a single memory directly (pre-extracted) |
| `extractAndStore(text, sessionId, llm)` | 122 | Full ingestion pipeline (extraction → embed → store → conflict queue → synaptic tagging → optional tick) |
| `search(query, llm?)` | ~300 | Retrieval; calls `engine.search()` |
| `retrieve(query)` | ~390 | Backwards-compatible simpler search; no rerank |
| `tick(llm?)` | 470 | Maintenance: `resolveConflictQueue()` + `engine.tick()` |
| `resolveConflictQueue(llm)` | 489 | Process up to 50 queued pairs, LLM-classify, supersede contradictions |

### Ingestion stages with line refs (TS)

| Stage | Where | Lines | What |
|---|---|---|---|
| LLM extract | `extractAndStore()` | 138–177 | Call `extractFromConversation()`; parse JSON; build Memory objects with `stability = 0.1 + importance · 0.3` |
| Embed + create | `extractAndStore()` | 146–154 | `embedWithRetry()` then `adapter.create()` |
| Deferred conflict | `extractAndStore()` | 157–174 | Search similar (cosine > 0.85), skip same session root, queue `(newId, existingId, sim)` for tick |
| Synaptic tagging | `extractAndStore()` | 194–217 | For each pair of new memories with cosine > 0.4, `adapter.createOrStrengthenLink()` (weight = `sim · 0.5` in TS) |
| Optional tick | `extractAndStore()` | 220–222 | If `runMaintenanceDuringIngestion`, call `tick()` |

### `extraction.ts` exports

| Function | Lines | Purpose |
|---|---|---|
| `extractFromConversation(text, llm, config)` | early | LLM extraction call; returns `Memory[]` |
| `extractRawTurns(text)` | ~180 | Non-LLM fallback; line-by-line episodic memories |
| `detectConflict(a, b, llm)` | ~230 | LLM classify: `CONTRADICTION` / `UPDATE` / `OVERLAP` / `NONE` |
| `compressMemories(group, llm)` | ~280 | LLM summarisation for consolidation |
| `rerankCandidates(query, candidates, llm)` | 343 | LLM relevance rerank for top-k |

Prompts are constants in this file: `EXTRACTION_PROMPT` (lines 52–91), `CONFLICT_PROMPT` (lines 93–102), `CONSOLIDATION_PROMPT`, `RERANK_PROMPT`. They're exported from the package, so users can override.

## 7. Adapter contract (`adapters/base.ts`)

`MemoryAdapter` is abstract with the following required methods (full sigs in `spec/adapter-interface.md`):

```ts
// CRUD
abstract create(memory: Omit<Memory, "id" | "createdAt" | "updatedAt">): Promise<string>;
abstract getMemory(id: string): Promise<Memory | null>;
abstract getMemories(ids: string[]): Promise<Memory[]>;
abstract queryMemories(filters: MemoryFilters): Promise<Memory[]>;
abstract updateMemory(id: string, updates: Partial<Memory>): Promise<void>;
abstract deleteMemory(id: string): Promise<void>;

// Search
abstract vectorSearch(embedding: number[], filters?: MemoryFilters): Promise<ScoredMemory[]>;
searchLexical(query: string, filters?: MemoryFilters): Promise<ScoredMemory[]> { return []; }  // optional, default empty

// Links
abstract createOrStrengthenLink(sourceId: string, targetId: string, strength: number): Promise<void>;
abstract getLinkedMemories(memoryId: string, minStrength?: number): Promise<(Memory & { linkStrength: number })[]>;
abstract getLinkedMemoriesMultiple(ids: string[], minStrength?: number): Promise<...>[];
abstract deleteLink(sourceId: string, targetId: string): Promise<void>;

// Tiering
abstract migrateToCold(memoryId: string, coldSince: number): Promise<void>;
abstract migrateToHot(memoryId: string): Promise<void>;
abstract convertToStub(memoryId: string, stubContent: string): Promise<void>;
abstract allActive(): Promise<Memory[]>;
abstract allHot(): Promise<Memory[]>;
abstract allCold(): Promise<Memory[]>;
abstract hotCount(): Promise<number>;
abstract coldCount(): Promise<number>;
abstract stubCount(): Promise<number>;
abstract totalCount(): Promise<number>;

// Consolidation
abstract findFading(threshold: number): Promise<Memory[]>;
abstract findStable(threshold: number, minAccessCount: number): Promise<Memory[]>;
abstract markSuperseded(memoryIds: string[], summaryId: string): Promise<void>;

// Batch + retention
abstract batchUpdate(memories: Memory[]): Promise<void>;
abstract updateRetentionScores(updates: Map<string, number>): Promise<void>;

// Tx + reset
abstract transaction<T>(callback: (a: MemoryAdapter) => Promise<T>): Promise<T>;
abstract clear(): Promise<void>;
```

`MemoryFilters` (also in `base.ts`):

```ts
{
  userId?: string;
  categories?: MemoryCategory[];
  minRetention?: number;
  minImportance?: number;
  createdAfter?: number;
  createdBefore?: number;
  limit?: number;
  offset?: number;
  includeSuperseded?: boolean;
}
```

In-tree adapters and their backends:

| Adapter | File | Backend | Notes |
|---|---|---|---|
| `InMemoryAdapter` | `adapters/memory.ts` | JS Map | For tests and dev. Loses data on restart. |
| `JsonlFileAdapter` | `adapters/jsonl.ts` | JSONL files | Append-only, file-rotation logic |
| `PostgresAdapter` | `adapters/postgres.ts` | Postgres + pgvector | Production option |
| `ConvexAdapter` | `adapters/convex.ts` | Convex DB | Used by blah.chat production |

## 8. Python ↔ TypeScript divergences

The two SDKs are functionally equivalent but have a few intentional and unintentional differences:

### Schema differences

| TS | Python | Notes |
|---|---|---|
| `Memory.metadata.{associations, sessionIds, isCold, ...}` (nested) | `Memory.{associations, session_ids, is_cold, ...}` (flat) | Python is flat for research-prototype reasons; TS groups for cleaner application API |
| `userId` field on Memory | passed via API, not on Memory | Python is single-tenant; TS multi-tenant |
| `retention` field cached | Computed on-the-fly | Performance vs simplicity tradeoff |
| `updatedAt` field | Not present | TS-only |

### Behaviour differences

1. **Ingestion-time stability reinforcement**: Python applies `existing_mem.stability += 0.05` for memories with cosine > 0.75 to a newly-stored memory (`core.py:204`). TypeScript does not — it only reinforces at retrieval time. This was added back in PR #2 ("refactor/humanize-and-fix-docs") as part of the persistence-bug fixes; the absence on the TS side is a known divergence to fix.

2. **Tick frequency**: Python runs maintenance every 5th ingestion (`core.py:242`). TypeScript runs on every ingestion when `runMaintenanceDuringIngestion: true` (`CognitiveMemory.ts:221`).

3. **Synaptic tagging weight**:
   - TypeScript (`CognitiveMemory.ts:211`): `weight = sim * 0.5` (linear in similarity)
   - Python: `weight = min(0.5, base_weight + (sim - threshold) * 0.5)` (clamped, scales with excess)

4. **Conflict queue size**: Python processes up to 50 pairs per `_resolve_conflict_queue()` call (`core.py:353`); TypeScript processes the whole queue per tick. Python's batch limit is the safer choice for large queues.

These divergences should converge over time. The Python SDK has been the testbed for the deferred conflict architecture; TS is catching up.

## 9. Tests and benchmarks

The SDK has tests at `cognitive-memory/sdks/typescript/tests/` and `cognitive-memory/sdks/python/tests/`. Benchmarks live in the *other* repo (`cognitive-memory-benchmarks/`) and are described in [`benchmarks-overview.md`](./benchmarks-overview.md).

The benchmarks repo imports the SDK in editable mode:

```bash
cd cognitive-memory-benchmarks
uv pip install -e . -e ../cognitive-memory/sdks/python
```

For dev work that mixes SDK changes with benchmark runs, the editable install means you don't need to bump versions or re-publish — just edit and re-run.

## 10. v6 feature flags

The feature set added in PR #1 (`feat/sdk-v6-implementation`) and tagged at v0.2.0:

- `decayModel: "exponential" | "power"` — Eq. 1 vs Eq. 1'
- `powerDecayGamma: number` — γ for power-law (default 1/ln(2))
- `hybridSearch: boolean` — BM25 + dense union; requires `searchLexical()` adapter support
- `kSparse: number` — BM25 candidate count
- `filterExpiredTransients: boolean` — selective expiry for plan/transient_state
- `includeExpiredInDeepRecall: boolean` — bypass expiry in deep recall mode
- `rerankEnabled: boolean` — LLM reranking of top-k
- `kRerank: number` — top-k size sent to rerank LLM
- `rerankModel: string | null` — defaults to extractionModel
- `graphExpansionHops: 0 | 1 | 2` — multi-hop BFS in retrieval
- `bridgeDiscovery: boolean` — find multi-path chains between top results
- `maxBridgePaths`, `minBridgeEdgeWeight` — bridge tuning

Plus the instrumentation hooks: `SearchTrace`, `StageTrace` types, populated when `RetrievalQuery.trace: true`. This is what the benchmark efficiency table (Run F) reads from.

## 11. Versions

- v0.1.x — pre-v6, stable for early users
- **v0.2.0** (commit `60ee27e`, 9 March 2026) — v6 features merged. **Used by Runs A–K.**
- **v0.3.0** (post `905aba7`, current local) — persistence-bug fixes (`refactor/humanize-and-fix-docs`, PR #2) and deferred conflict-resolution refactor. **Used by Run L.**

The persistence bugs fixed between v0.2.0 and v0.3.0:
- Stability reinforcement not persisted for non-InMemory adapters.
- Synaptic tagging associations not persisted.
- Contradiction-handling ordering bug (category demotion happened before the `is core?` check, making the check always false).

These bugs affect the architectural claims that LTI-Bench tests directly (decay floors with reinforcement, associative retrieval, conflict-driven supersession). LoCoMo / LongMemEval / oracle / decay / efficiency / ablations / judge-reliability runs (A–K, M) are not affected because they don't depend on those mechanisms working end-to-end with a non-InMemory adapter.
