# Phase 14 - Temporal Reconstruction Experiment

Status: implementation complete; controlled smoke passed; dev-slice A/B run twice. 2026-05-24 v1 was marginal and exposed classifier-precision as the blocker. 2026-05-26 classifier tightened (SDK `fix(temporal)`) and v2 re-run shows a clean positive signal (FP rate 11.3% -> 1.9%, temporal +2.75pp). Default still OFF pending a full-split paired run; single-conv n=40 cannot flip a global default.

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

## Dev-Slice A/B v2 — after classifier fix (2026-05-26)

Tightened `_is_temporal_query` (SDK `fix(temporal)`, Python + TS, tested): a
query is temporal only when it leads with a time/duration interrogative
(when / how long / what year / ...), is a what-happened-before/after sequence
question, or contains a whole-word current-state marker. The old list matched
"after/before/first/last/now" anywhere (and "now" inside "know"). Re-ran the
same dev slice (conv-42); artifact `dev_slice_ab_v2.json`.

| Metric | v1 | v2 |
|--------|----|----|
| Non-temporal FP rate | 11.3% (18/159) | **1.9% (3/159)** |
| Temporal recall | 82.5% (33/40) | 82.5% (33/40) |
| Temporal F1 delta (off->auto) | +1.4pp | **+2.75pp** (7 up / 1 down / 32 same) |
| Projected non-temporal regression | −0.17pp | −0.21pp |

(Absolute off-arm F1 differs across runs because each re-ingests with slight
LLM-extraction non-determinism; the within-run delta is the valid signal.)

The fix is clean:

- The 3 residual "false positives" are all genuinely temporal-phrased questions
  LoCoMo labels as cat 1/3/4 ("When did Nate get Tilly", "For how long...",
  "...currently playing"). The classifier is *correct* to fire; the residual is
  LoCoMo label noise, not classifier error.
- The 1 temporal "regression" is a token-F1 artifact (off "Week of Jan 14" vs
  auto "Jan 14"; gold "the week before Jan 21" — both essentially correct).
- Real what/how false positives (the v1 −0.27 regressions) are gone.

### Decision (v2)

- **Classifier fix adopted** (committed to the SDK) — it's a precision bug fix
  that helps any temporal work and removes non-temporal harm, independent of
  whether `temporal_query_mode` is ever defaulted on.
- **`temporal_query_mode` default stays OFF.** The dev slice now shows a clean
  positive signal, but a single conversation (n=40, no CI) cannot justify
  flipping a global default. The dev slice has done its job: it confirmed the
  classifier was the blocker and that the mechanism helps once precision is fixed.
- **To actually adopt the default**, run the full held-out split (5 convs, paired
  bootstrap CI, production feature config). That is now justified by the clean
  dev-slice signal — but it is a separate, larger spend, not part of this
  dev-slice loop. Also still worth investigating the ~20% `event_time` extraction
  yield, which caps the mechanism upstream.
