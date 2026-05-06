# Reviewer Feedback: Memory Lifecycle and SDK Scope

Source: user discussion after reviewer feedback, 2026-02-26, plus later pasted transcript.

## Canonicality

Do not infer chronology from pasted conversations. Treat them as context only.

- Code is canonical for implementation behavior.
- `experimentlog.md` and `experimentlog_v2.md` are canonical for benchmark/result claims.
- Paper/docs can lag code and logs.
- Only treat pasted conversation as corrective when it explicitly says current code/docs are wrong, then verify locally.

## Problem

Reviewers raised a valid engineering concern: if Cognitive Memory never forgets, total stored memory grows forever. Cold storage keeps stale memories out of the hot vector index, but it does not bound total storage. Some cold memories may never be recalled again, so indefinite retention creates storage and maintenance cost.

## Useful framing

The defensible claim is not "never delete." It is "never delete abruptly."

Cognitive Memory's important distinction from hard-pruning systems is graceful degradation:

1. Hot searchable memory
2. Fading memory
3. Cold storage
4. Possible revival through deep recall or associations
5. TTL-based conversion to a lightweight stub after prolonged cold dormancy

This keeps the core idea intact: old memories can become relevant again, and a recalled cold memory should get a strong spaced-repetition boost. But it also acknowledges practical deployment limits and the neuroscience basis for permanent forgetting.

Richards & Frankland-style adaptive forgetting supports this: memory is for useful future decision-making, not perfect archival storage. Permanent forgetting can be adaptive because it reduces overfitting to stale detail.

## Current architecture

Cold-storage TTL is current truth. The SDK has a cold-storage TTL path (`coldStorageTtlDays` / `cold_storage_ttl_days`, default 180 days) that converts expired cold memories into stubs. The paper may still contain older absolute "never delete" language, so verify the current source before editing.

Current framing:

- Memory enters cold storage after prolonged low retention.
- A configurable dormancy timer starts, currently 180 days by default.
- Any retrieval, association traversal, or deep-recall hit resets the timer and can migrate the memory back to hot storage.
- If the timer expires, run one final consolidation pass.
- Delete the full original but retain a lightweight summary stub or trace.

This bounds storage by:

- active/hot memories
- cold memories younger than TTL
- tiny summary stubs

When writing public docs or the paper, present TTL as part of the architecture. Products can tune the TTL, but the default architecture is not "store full cold memories forever."

Open doc/paper alignment issue:

- `docs/sdk-internals.md` documents `coldStorageTtlDays = 180`.
- `docs/architecture.md` mentions TTL expiry during maintenance.
- `paper/paper.tex` may still say memories "never reach zero" and originals are "preserved rather than deleted."
- Resolve by distinguishing retention floors from storage retention: memories do not abruptly vanish from the hot retrieval model, but cold storage degrades to stubs after TTL.

## Product positioning

Reviewers also framed the system as optimizing for "more human" agents at the cost of retrieval latency. Better framing:

- Decay is broadly useful for any persistent-memory agent because it improves signal-to-noise.
- A one-year-old stale preference should not rank equally with a current, frequently used preference.
- Advanced features like cold storage revival, associative traversal, deep recall, and core promotion are most valuable for relationship-oriented agents: companions, coaches, personal assistants, therapeutic tools, and long-term collaborators.
- Purely transactional retrieval agents may only need decay and scoring, not the full cognitive stack.

Latency framing:

- Normal hot-path retrieval is comparable to ordinary vector search plus scoring.
- Cold retrieval and deep recall should be explicit or triggered only when the app needs richer recall.
- The extra cost is a product choice, not mandatory overhead for every query.

## SDK configurability decision

Feature flags are tempting but risky because the mechanisms are coupled. Examples:

- Decay can stand alone.
- Retrieval boosting depends on stability/decay semantics.
- Associations depend on co-retrieval and boosting.
- Core promotion depends on stability, access counts, and sessions.
- Deep recall depends on cold storage and consolidation.

If configurability is added later, prefer coherent presets over many independent toggles:

- `minimal`: decay + retrieval scoring
- `standard`: minimal + associations + core promotion
- `full`: standard + cold storage + consolidation + deep recall

Allow advanced overrides only with validation. Invalid combinations should fail loudly.

Current decision: leave the SDK as-is for now. Add configurability only after real user demand appears.

## Benchmark baselines

Use `experimentlog.md` as the source of truth.

Canonical comparison points currently captured there:

- LoCoMo Run A: overall F1 44.8%, multi-hop F1 48.5%.
- Published multi-hop baselines: FadeMem 29.43%, Mem0 28.37%, MemGPT 9.46%.
- LongMemEval-S Run B: task-averaged accuracy 70.2%.
- LTI-Bench Run L v2: overall 88.1% accuracy, F1 69.7%, critical retention 100%, 66/85 core.
- LTI critical-retention comparison: 100% vs FadeMem 82.1%.

Do not use benchmark values from pasted chats unless they match the experiment logs.

## Security/process note

One pasted transcript included an API key. Never store, repeat, or use pasted credentials. Benchmark instructions should use `OPENAI_API_KEY` from the local shell environment only.

## Docs/paper implications

Potential future edits:

- Soften absolute "never delete" language.
- Emphasize graceful degradation and revival windows.
- Distinguish current behavior from possible production retention policies.
- Name target use cases explicitly.
- Clarify that decay is generally useful, while full cognitive recall is most valuable for long-term relationship agents.

Do not update implementation from this note alone.
