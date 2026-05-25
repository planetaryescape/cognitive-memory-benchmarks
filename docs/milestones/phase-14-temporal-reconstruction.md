# Phase 14 - Temporal Reconstruction Experiment

Status: implementation complete; controlled smoke passed; dev-slice LoCoMo A/B run 2026-05-24 — marginal signal, NOT adopted. Classifier precision is the blocker. Full-split run deferred.

## Hypothesis

Current Cognitive Memory has a lifecycle architecture, not a strong temporal-memory architecture. LoCoMo temporal failures should improve if retrieval distinguishes:

- when a memory was mentioned
- when the event happened
- when the fact/state was valid
- whether a plan was completed, cancelled, hypothetical, or current

## Intervention

Default-off temporal v1:

- Extract temporal metadata and event frames during SDK ingestion.
- Add `temporal_query_mode = "auto"` retrieval routing.
- For temporal queries, broaden candidates, soften retention weighting, add small temporal metadata boosts, and return evidence ordered by event time.
- Close validity windows on update/contradiction without overwriting the old memory.
- Format benchmark evidence with temporal labels when available.

## Non-goals

- No trace-fragment episode reconstruction yet.
- No paper claim update until benchmark evidence supports adoption.
- No default behavior change before A/B validation.

## Benchmark Truth Fix

LoCoMo category labels in local code were mismapped. The dataset counts match:

- `1 = multi-hop` (282)
- `2 = temporal` (321)
- `3 = open-domain` (96)
- `4 = single-hop` (841)
- `5 = adversarial`

Any pre-fix category table must be recomputed before being cited.

No-cost relabel of `locomo/results/current_sdk_20260505/primary_merged.json`
was written to `locomo/results/current_sdk_20260505/primary_merged_relabelled.json`:

- multi-hop: F1 0.3581 / judge 46.1% (n=282)
- temporal: F1 0.4847 / judge 55.5% (n=321)
- open-domain: F1 0.2370 / judge 43.8% (n=96)
- single-hop: F1 0.4877 / judge 65.4% (n=841)

This changes the diagnosis: the previously cited weak "temporal" bucket was
mostly a label artifact. Temporal reconstruction is still worth testing for
explicit `when/before/after/current` behavior, but it should not be adopted as
the answer to the headline weakness unless A/B runs show a separate gain.

## Validation Plan

1. Unit tests for relative date normalization, chronological evidence ordering, and category labels.
2. Recompute old LoCoMo aggregate labels without rerunning.
3. Run small LoCoMo dev slice with `temporal_query_mode=off` vs `auto`.
4. Inspect 30 temporal misses and classify:
   - missing answer evidence
   - missing anchor
   - unordered evidence
   - unnormalized relative time
   - plan/completion confusion
   - superseded state confusion
   - answer-model reasoning failure
   - scoring artifact
5. Full LoCoMo only if the dev slice shows real signal.

## Controlled Smoke Result

Artifact: `tuning/runs/phase14-temporal-reconstruction/controlled_smoke.json`

Result: pass.

Checks:

- Default-off mode emits no temporal evidence block.
- Auto mode orders `after` evidence chronologically:
  - Alex injured her ankle.
  - Alex started physiotherapy.
  - Alex resumed light running.
- Default-off current-state query can pick stale semantic state:
  - Jamie lives in Manchester.
- Auto mode prefers current state:
  - Jamie lives in London.

Implementation note: the smoke caught a bug where all temporal queries were
chronologically sorted, which is wrong for `now/current/still` queries. The SDK
now keeps score order for current-state queries, uses chronological order for
sequence queries, and reverse chronological order for `last/latest` queries.

## LoCoMo A/B Status

Prepared configs:

- `tuning/spaces/peer_review/temporal_reconstruction_off.json`
- `tuning/spaces/peer_review/temporal_reconstruction_auto.json`

Attempted a one-conversation LoCoMo smoke on 2026-05-21 with extraction,
dual-perspective, deep recall, and rerank enabled. It was stopped before metrics:
ingestion alone was still running several minutes in, so the run was not a
useful cheap validation. Do not cite it.

Next validation should use either a pre-ingested/cache-backed LoCoMo slice or a
small temporal-only QA slice before spending on full off-vs-auto LoCoMo.

## Adoption Gate

Adopt only if temporal evidence recall or temporal F1 improves without more than 1pp non-temporal regression, and manual audit shows fewer ordering/date/status failures.

## Dev-Slice A/B Result (2026-05-24)

Cheap ingest-once-retrieve-twice A/B on the most temporal-rich held-out
conversation (conv-42: 29 sessions, 40 temporal / 159 non-temporal Qs).
Script: `analysis/temporal_ab_dev_slice.py`. Artifact:
`tuning/runs/phase14-temporal-reconstruction/dev_slice_ab.json`.

Setup: frozen tuned config, single-perspective ingestion, no LLM rerank,
extraction+embeddings on OpenAI, answers on local LM Studio `gpt-oss-120b`,
token-F1. Same ingested store for both arms; `temporal_query_mode` flipped live
(SDK reads it at search time). The entire temporal path is gated on
`mode=="auto" AND _is_temporal_query`, so non-temporal queries are byte-identical
between arms — only classifier false positives can change a non-temporal answer.

Numbers:

| Slice | n | F1 off | F1 auto | delta |
|-------|---|--------|---------|-------|
| temporal (cat 2) | 40 | 0.296 | 0.310 | **+0.014** (3 up / 0 down / 37 same) |
| non-temporal false positives | 18 | 0.190 | 0.175 | −0.015 (2 up / 2 down) |
| projected over all 159 non-temporal | 159 | — | — | **−0.0017** |

Automated gate passes (temporal up; non-temporal within 1pp). **But this is a
noise-level result and is NOT adopted.** Reasons:

- +1.4pp temporal rests on only 3 of 40 questions; single conversation, no CI.
- Only **44/215 (20%)** of ingested memories carry `event_time`. Chronological
  ordering keys on `event_time`/`mentioned_at`, so the mechanism is starved.
- Real per-question regressions exist where the classifier over-fires.

Manual audit (mechanism):

- **Wins** are real where the question asks *when*: auto's score-boost +
  chronological ordering surfaces the *specific dated* memory (e.g. "Nate won his
  **first** tournament" replaces the generic "won a large tournament"), letting
  the answer model pin the date.
- **Regressions** all come from classifier false positives — questions that
  *mention* time but ask *what/how* ("...after someone wrote her a letter",
  "...near Fort Wayne **last summer**"). Chronological reorder demotes the
  relevant memory out of the top-k. Chronology is the wrong sort key there.

Diagnosis: the bottleneck is `_is_temporal_query` **precision** (33/40 temporal
recall is fine; 18/159 = 11% non-temporal false-positive rate is not). It fires
on any "when/after/last/how long" regardless of whether the *answer* is a time.

### Decision

- Do **not** flip the default; keep `temporal_query_mode="off"`.
- Do **not** spend on the full held-out-split run yet — the dev slice does not
  clear the bar that would justify it.
- Cheapest high-ROI next step: tighten `_is_temporal_query` precision (require
  the question to *ask for* a time/date, not merely mention one), then re-run
  this same dev slice. Secondary: investigate why only 20% of memories get
  `event_time` from extraction — the mechanism is metadata-starved upstream.
