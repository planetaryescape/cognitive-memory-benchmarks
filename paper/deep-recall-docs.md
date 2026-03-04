# Deep Recall

## Overview

When memories are consolidated, the original memories are superseded: they're clamped to the regular decay floor, moved to cold storage, and excluded from normal retrieval. A consolidated summary takes their place in the hot index.

Deep recall is a retrieval parameter that temporarily re-includes superseded originals in the candidate set. It exists for cases where a summary isn't enough and the exact original content matters.

```typescript
// Normal retrieval — superseded originals are excluded
const results = await memory.search(query);

// Deep recall — superseded originals are included with a score penalty
const results = await memory.search(query, { deep_recall: true });
```

When `deep_recall` is `true`, superseded originals enter the candidate pool with a 0.5× multiplier on their retrieval score. This means they only surface when the query strongly matches them. Current, non-superseded memories still rank higher for any given query unless the archived content is a much better semantic match.

## Design Philosophy

The SDK is intentionally unopinionated about *when* to use deep recall. It exposes the parameter and leaves the decision to you. This is deliberate: the right trigger depends on your use case, your user expectations, and how your agent interprets intent.

Below are two common patterns for automating that decision. Pick whichever fits your architecture, or build your own.

---

## Pattern 1: LLM-Decided Deep Recall

The agent decides whether to use deep recall based on the user's query. You give the LLM a tool description that explains the option, and it sets the flag when it judges that the user is asking for specific historical detail.

**When to use this:** You're building a conversational agent where the LLM already selects tools and parameters. You trust the model to interpret user intent.

**How it works:**

1. Expose `search` as a tool with `deep_recall` as an optional boolean parameter.
2. In the tool description, explain when the model should set it to `true`.
3. The model decides per-query.

**Example tool definition:**

```json
{
  "name": "search_memory",
  "description": "Search the user's memory store. Set deep_recall to true when the user is asking for exact details about something that may have been consolidated into a summary, e.g. 'what exactly did I say about X?', 'what were the specific numbers?', 'remind me of the original wording'. Leave false for general retrieval.",
  "parameters": {
    "query": { "type": "string" },
    "deep_recall": { "type": "boolean", "default": false }
  }
}
```

**Example agent code:**

```typescript
// Inside your tool handler
async function handleSearchMemory({ query, deep_recall = false }) {
  const results = await memory.search(query, { deep_recall });
  
  // Optionally flag deep recall results so the LLM knows they're archived
  return results.map(r => ({
    ...r,
    source: r.superseded ? 'archived_original' : 'active_memory'
  }));
}
```

**Trade-offs:**

- ✅ Most flexible. Handles nuanced intent ("what was the exact phrasing?" vs "what do I know about X?").
- ✅ No wasted queries. Deep recall only fires when the model thinks it's needed.
- ⚠️ Adds another LLM judgment call. The model might miss cases where deep recall would help, or use it unnecessarily.
- ⚠️ Requires the model to understand the concept. Your tool description needs to be clear.

---

## Pattern 2: Automatic Fallback

Normal retrieval runs first. If the results are poor (nothing above a confidence threshold), the system automatically re-runs with deep recall enabled. The caller doesn't need to know about deep recall at all.

**When to use this:** You want deep recall to "just work" without the agent or user needing to think about it. Good for applications where you control the full retrieval pipeline.

**How it works:**

1. Run a normal search.
2. Check if the top result's score exceeds a threshold (e.g., 0.3).
3. If not, re-run with `deep_recall: true`.
4. Return the better result set.

**Example:**

```typescript
async function searchWithFallback(
  memory: CognitiveMemory,
  query: string,
  fallbackThreshold = 0.3
) {
  // First pass: normal retrieval
  const results = await memory.search(query);
  
  const topScore = results.length > 0 
    ? Math.max(...results.map(r => r.score)) 
    : 0;

  // If nothing scored well, try deep recall
  if (topScore < fallbackThreshold) {
    const deepResults = await memory.search(query, { deep_recall: true });
    
    if (deepResults.length > 0) {
      // Tag results so downstream code knows these came from deep recall
      return deepResults.map(r => ({ ...r, via_deep_recall: true }));
    }
  }

  return results.map(r => ({ ...r, via_deep_recall: false }));
}
```

**Trade-offs:**

- ✅ Invisible to the caller. No tool descriptions needed, no LLM judgment required.
- ✅ Guarantees deep recall fires when normal retrieval fails, which is the most common case where it's needed.
- ⚠️ Costs an extra query when normal retrieval is poor, even if deep recall won't help either (the query might just be about something the system has never seen).
- ⚠️ The threshold is a tuning parameter. Too low and you never trigger fallback; too high and you trigger it on queries that just have weak matches. Start with 0.3 and adjust based on your data.
- ⚠️ Doesn't handle the case where normal retrieval returns a decent summary but the user specifically wants the original detail. For that, you need Pattern 1.

---

## Combining Both Patterns

The patterns aren't mutually exclusive. A robust setup uses Pattern 1 as the primary mechanism (let the LLM decide when exact recall matters) with Pattern 2 as a safety net (if normal retrieval returns nothing useful, try the archives automatically).

```typescript
async function search(
  memory: CognitiveMemory,
  query: string,
  options: { deep_recall?: boolean } = {}
) {
  // If the caller explicitly requested deep recall (Pattern 1), honour it
  if (options.deep_recall) {
    return memory.search(query, { deep_recall: true });
  }

  // Otherwise, normal search with automatic fallback (Pattern 2)
  const results = await memory.search(query);
  const topScore = results.length > 0
    ? Math.max(...results.map(r => r.score))
    : 0;

  if (topScore < 0.3) {
    const deepResults = await memory.search(query, { deep_recall: true });
    if (deepResults.length > 0 && deepResults[0].score > topScore) {
      return deepResults;
    }
  }

  return results;
}
```

## Notes

- Deep recall results include a `superseded` flag and a `supersededBy` field pointing to the summary that replaced them. Use this to give context to your agent or user ("this is the original detail; the current summary is X").
- The 0.5× score penalty is configurable via `deep_recall_penalty` in the search options if you want to be more or less aggressive about surfacing archived content.
- Deep recall does not affect cold storage migration or re-indexing. A superseded original that surfaces via deep recall stays in cold storage. If you want it back in the hot index, retrieve it via its association with the summary, which triggers a normal retrieval boost.
