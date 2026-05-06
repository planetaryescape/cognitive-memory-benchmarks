# LTI-Bench — Long-Term Interaction Benchmark

LTI-Bench is a hand-authored controlled benchmark designed to exercise the architectural claims of the cognitive-memory paper directly. Unlike LoCoMo and LongMemEval which measure end-to-end QA on real conversational data, LTI-Bench probes specific lifecycle properties: decay floors, emergent core promotion, conflict-driven supersession, revival of faint memories, time-aware retrieval, associative recall.

This doc walks the design, the v1→v2 evolution, and the limitations.

## 1. Why a controlled benchmark?

LoCoMo and LongMemEval grade end-to-end accuracy on real multi-session conversations. They're great for "is the memory system useful" but they don't isolate the architectural mechanisms:

- A memory system that wins on LoCoMo could be winning because of *retrieval ranking*, *answer model robustness*, or *prompt format*, with the decay/floor mechanisms doing nothing.
- Conversely, a system that loses on LoCoMo might still have working architectural mechanisms — they just don't help with that specific eval.

LTI-Bench targets the architectural claims directly with hand-authored probes. If the system passes core_persistence, that's evidence the core-memory mechanism is working. If it fails revival, that's evidence the decay-floor + deep-recall mechanism isn't doing what the paper claims.

The price you pay: **n is small** (42 probes total, 4–8 per category). LTI-Bench is a confirmatory test, not a generalisation benchmark.

## 2. Scenario design

A 30-day single-user interaction with 28 facts ingested across 28 daily sessions, plus 42 probes at strategic time points.

### Facts (28 total)

```
Critical / Core (8)        — identity, medical, family, residence
Contextual (8)             — project, hobby, recurring appointments, car, therapist, guitar lessons
Trivial (8)                — single-mention casual facts (lunch, weather, traffic, neighbor's cat, ...)
Updated/Conflict (4 pairs) — Helios deadline March 15 → April 1
                              Helios backend Python → Go
                              Vacation Tokyo → Lisbon
                              Office Mondays → fully remote
```

Each fact has:
- `content` — the fact text
- `category` — critical / contextual / trivial
- `day_introduced` — which day the fact first appears
- `expected_core` — whether the LLM extractor *should* tag it as core
- `access_days` — list of days when the fact is naturally re-mentioned in conversation
- `superseded_by` (for conflict facts) — the new content
- `superseded_on_day` — when the supersession happens

The session generator turns these into daily conversations: introducing new facts on `day_introduced`, naturally re-accessing existing facts on `access_days`, introducing supersessions on `superseded_on_day`. Each daily session has a few filler turns to keep it from being a fact-dump.

### Probes (42 total, 8 categories)

```
core_persistence (8)        — at day 30, ask about each critical fact
decay_trivial (6)           — at day 30, ask about each trivial fact directly (tests decay floors)
contextual_retention (6)    — at day 30, ask about contextual facts (medium importance)
revival (5)                 — at day 30, ask oblique cues for trivial facts (tests revival)
conflict (4)                — at day 30, ask about updated facts (should return updated version)
temporal_before_update (4)  — at day 10/12/15, ask about facts BEFORE supersession (should return original)
temporal_after_update (4)   — at day 22/25, ask about same facts AFTER supersession (should return updated)
associative (5)             — at day 30, ask cross-fact queries ("what do you know about my family?")
```

Probe shape:
```python
{
  "day": int,        # When this probe fires
  "question": str,
  "expected": str,   # Reference answer for scoring
  "fact_idx": int,   # Provenance — which fact this probe targets (-1 for associative)
  "type": str        # Probe category
}
```

## 3. Time-stepped ingestion (v2)

This is the critical fix from v1 → v2.

### v1 (broken): ingest-all-then-probe

```python
# Pseudocode
adapter.reset()
for session in daily_sessions:
    adapter.ingest_session(session)  # ALL 28 sessions ingested first
for probe in probes:
    answer = query(probe.question, timestamp=probe.day_timestamp)
    score(answer, probe.expected)
```

By the time the day-10 `temporal_before_update` probe fires, the day-15 supersession has already been ingested. The `timestamp=` parameter is used for *decay computation* but does **not filter out memories ingested after that timestamp** (because the memory store doesn't track ingestion order vs query time — there's no "as of" query mode).

Result: the day-10 probe expecting "March 15th" returns "April 1st" because the system already knows about the update. Every `temporal_before_update` probe fails — the test is incoherent.

### v2 (fixed): time-stepped

```python
sessions_by_day = {s["day"]: s for s in daily_sessions}
probes_by_day = group_by_day(probes)

for day in range(1, 31):
    if day in sessions_by_day:
        adapter.ingest_session(sessions_by_day[day])  # Ingest day-D session FIRST
    for probe in probes_by_day.get(day, []):           # Then run day-D probes
        answer = query(probe.question, timestamp=day_timestamp(day))
        score(answer, probe.expected)
```

Now a day-10 probe runs after sessions 1–10 are ingested, but before session 15 (where the Helios supersession happens). The original "March 15th" fact is still current. The probe meaningfully tests whether the system can answer with the fact that was current *at probe time*.

After the fix, all 4 `temporal_before_update` probes pass at 100% accuracy.

## 4. Scoring evolution

### v1: substring containment

```python
contains_expected = expected_lower in answer_lower
```

This is a strict literal substring check after normalisation. It produces a lot of false negatives:

| Probe | Expected | Got | Substring? |
|---|---|---|---|
| revival weather | "nice this morning" | "weather was really nice on the morning of January 5" | ❌ |
| temporal Helios | "April 1st" | "April 1, 2024" | ❌ |
| revival traffic | "traffic on my commute" | "traffic on Alex's commute on January 10" | ❌ |
| conflict Helios | "April 1st" | "April 1, 2024" | ❌ |

In each case, the **memory was retrieved correctly**; the answer is substantively right; only the literal phrasing fails. v1 reported these as failures.

### v2: LLM-as-judge

```python
from shared.metrics import llm_judge

judgement = llm_judge(
    question=probe["question"],
    prediction=answer,
    ground_truth=probe["expected"],
    model="gpt-4o-2024-08-06",
)
correct = judgement["correct"]
```

The judge prompt (in `shared/metrics.py`):

```
You are evaluating a question-answering system's response against a ground truth answer.
Question: {question}
Ground Truth Answer: {ground_truth}
System Answer: {prediction}

Does the system's answer correctly capture the key information from the ground truth?
Consider partial credit: if the system answer contains the essential facts from the ground truth,
even if worded differently, it should be marked CORRECT.

Respond with exactly one word: CORRECT or WRONG
```

Same judge model as LongMemEval-S official scoring (κ = 0.879 inter-prompt reliability per Run M).

v2 still reports F1 alongside judge accuracy as a sanity check — they should mostly agree, and large disagreements flag judge artifacts.

## 5. v2 results

```
Total probes: 42
Overall accuracy: 88.1%
Overall F1: 69.7%

Per category:
  core_persistence       : accuracy=100.0%  F1=93.3%   (n=8)
  decay_trivial          : accuracy=100.0%  F1=61.4%   (n=6)
  contextual_retention   : accuracy=100.0%  F1=84.5%   (n=6)
  temporal_before_update : accuracy=100.0%  F1=85.0%   (n=4)
  temporal_after_update  : accuracy=100.0%  F1=67.7%   (n=4)
  conflict               : accuracy=75.0%   F1=80.0%   (n=4)
  revival                : accuracy=80.0%   F1=42.9%   (n=5)
  associative            : accuracy=60.0%   F1=35.0%   (n=5)

Storage:
  Total memories: 85
  Hot: 85, Cold: 0, Core: 67 (78%)

Critical fact retention: 100.0% (FadeMem: 82.1%)
```

## 6. Failure analysis (v2)

4 failures total. 2 are judge artifacts; 2 are real partial-recall issues.

### Judge artifacts (2)

**revival weather**:
- Q: "Was there anything about the weather I mentioned once?"
- Expected: "nice this morning"
- Got: "The weather was really nice on the morning of January 5, 2024."
- Judge: WRONG (substantively correct — judge over-strict on temporal phrasing)

**conflict Helios deadline**:
- Q: "When is the Helios project deadline?"
- Expected: "April 1st"
- Got: "April 1, 2024."
- Judge: WRONG (substantively correct — same date)

These are not architectural failures. The memory system retrieved correctly; the judge marked them wrong on phrasing. Adjusting judge strictness or the reference answer format would push these to passing.

### Real failures (2)

Both in the `associative` category.

**associative family**:
- Q: "What do you know about my family?"
- Expected: "Jordan (partner), Eileen (mother), Pixel (dog)"
- Got: "Alex's mother's name is Eileen, and Eileen lives in Vancouver."
- Judge: WRONG. Got 1 of 3 family facts.

**associative recurring activities**:
- Q: "What recurring appointments or activities do I have?"
- Expected: "therapy Tuesdays Dr. Patel, guitar lessons Thursdays, half marathon training"
- Got: "Dr. Patel on Tuesdays, guitar lesson every other Thursday, standup at 9:30 AM every day."
- Judge: WRONG. Got 2 of 3 expected + a non-expected one (standup, which isn't really a recurring appointment but isn't strictly wrong either). Missed half-marathon training.

These are real partial-recall failures. They show that single-shot retrieval surfaces a *subset* of an associated cluster, not the full cluster. Direct probes for any individual fact succeed (Jordan, Pixel, half-marathon all pass in their own categories); the failure is specifically in cross-fact recall.

This is the architectural weak spot most worth investigating. Candidate fixes:
- Explicit graph-walk expansion at retrieval time for "what do you know about X" style queries
- Broader top-k for associative-typed queries
- A query classifier that routes "what do you know about X" to a different retrieval policy
- Better synaptic tagging at ingestion (current threshold cosine > 0.4 may be too strict for cross-fact bundling)

## 7. Architectural reading

What v2 results say about each architectural claim:

| Claim | Evidence | Result |
|---|---|---|
| Decay floors hold (regular memories never reach zero) | decay_trivial 100% | **Supported.** All 6 unaccessed trivial facts recovered when probed directly at day 30. |
| Critical retention via core-memory mechanism | core_persistence 100% | **Supported.** All 8 critical facts retrieved at day 30. Better than FadeMem 82.1%. |
| Emergent core promotion through use | 66/85 stored memories core | **Supported but possibly over-fires.** 78% promotion rate is high; threshold tuning candidate. |
| Conflict-driven supersession | conflict 75% (1 judge artifact), temporal_before 100%, temporal_after 100% | **Supported.** Updated facts return new version; original facts return at the time they were current. |
| Revival of faint memories | revival 80% (1 judge artifact) | **Supported.** 4/5 memories mentioned once, never re-accessed, retrieved correctly via oblique cues. |
| Time-aware retrieval | temporal_before 100% / temporal_after 100% | **Supported** under time-stepped ingestion. |
| Associative retrieval | associative 60% | **Partially supported.** Direct probes work; cross-fact cluster queries return subsets. |
| Cold-tier migration | 0 cold memories | **Untested.** 30 days insufficient to trigger; would need a longer scenario. |

## 8. Sample size and statistical caveats

n=42 probes is small. Per-category n=4–8 is too small for statistical claims about generalisation. The benchmark is a confirmatory test of *whether mechanisms work*, not a generalisation claim about *how well*.

Single-seed: every run is one seed. Re-running with different LLM seed sampling (or different fact orderings) would produce different specific results. We have not characterised that variance.

Hand-authored: the 28 facts are designed to exercise the categories cleanly. They're not sampled from real conversational data. Generalising LTI-Bench accuracy to "this system will have 90% accuracy in production" would be a category error.

## 9. Where to go next on LTI-Bench

If we wanted to make this paper-stronger:

1. **Expand to ~150 probes.** 4× the current size, n=15–20 per category. Add more conflict/supersession patterns, more associative cluster types, more time-points for temporal probes.

2. **Add a 90-day scenario.** Long enough to actually trigger cold-tier migration. Tests an architectural claim that v2's 30-day scenario can't.

3. **Add multi-seed runs.** 3–5 seeds with different fact ordering / session construction. Would convert per-category results from point estimates to intervals.

4. **Add an associative-recall fix and re-run.** If the cross-fact retrieval policy gets fixed, associative should jump from 60% to 90%+. Demonstrating the architectural fix on the same controlled benchmark would be a nice causal story.

5. **Add a NaiveRAG comparison column.** Wire `NaiveRAGAdapter` (already exists in `shared/adapter.py`) through the harness; compare per-category accuracy. NaiveRAG should fail revival (no decay floors), fail conflict (no supersession), fail temporal_before (no time-aware retrieval), and pass core_persistence + contextual + recent associative. Would give a direct architectural-mechanism contrast.

For the current paper version (v1 of arXiv submission), v2 results as-is are sufficient as a confirmatory test alongside LoCoMo + LongMemEval-S. The 88.1% headline + 100% critical retention claim is paper-worthy. The 60% associative is honestly flagged as a known weakness in the paper's Future Work and Limitations.

## 10. Implementation notes (current state)

- **Code**: `lti/lti_bench.py` (current version is v2 with both fixes applied; v1 was overwritten in place but its outputs are preserved in `lti/results/v6_run_l.json`).
- **Output**: `lti/results/v6_run_l_v2.json` is canonical; `v6_run_l.json` is the superseded v1.
- **Bug fixed during this session**: `lti/lti_bench.py:357` had `from memory_adapter import` (broken); changed to `from shared.memory_adapter import` (correct). This fix is uncommitted.
- **Time to run**: ~5 minutes wall, ~500k tokens, single seed.
- **Reproduction**:
  ```bash
  cd ~/code/bhekanik/cognitive-memory-benchmarks
  .venv/bin/python -m lti.lti_bench \
    --adapter cognitive_memory \
    --model gpt-4o-mini \
    --judge-model gpt-4o-2024-08-06 \
    --output lti/results/v6_run_l_v2.json
  ```
