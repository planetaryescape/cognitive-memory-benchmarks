# Phase 14 - Temporal Reconstruction Experiment

Status: implementation complete; controlled smoke passed; LoCoMo A/B pending.

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
