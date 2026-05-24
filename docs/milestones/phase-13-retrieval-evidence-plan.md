# Phase 13 - retrieval-level evidence recall plan

Status: subset and minimum annotation packet regenerated after Phase 12 full-split local rows completed; manual annotation pending.

## Purpose

Answer the cleaner architecture question that answer F1 cannot isolate:

Does the full memory architecture retrieve the right evidence more often than vector-only and targeted mechanism ablations?

This complements Phase 12 end-to-end local answer F1. Phase 12 fixes the answer model, prompts, embeddings, question set, and retrieval budget. Phase 13 additionally evaluates retrieved evidence directly, before answer generation can hide or amplify retrieval mistakes.

## Evidence source

LoCoMo includes evidence dialog IDs for almost every held-out category 1-4 question.

Held-out LoCoMo-test counts from `tuning/splits/peer_review_20260511/locomo_test.json` using the corrected LoCoMo category mapping (`1=multi-hop`, `2=temporal`, `3=open-domain`, `4=single-hop`):

- Multi-hop: 168 questions, 168 with evidence.
- Temporal: 158 questions, 157 with evidence.
- Open-domain: 53 questions, 51 with evidence.
- Single-hop: 464 questions, 464 with evidence.
- Standard category 1-4 total: 843 questions.
- Evidence-labeled category 1-4 total: 840 questions.

## Selected subset

Regenerated deterministic 100-question evidence subset:

- JSON: `tuning/runs/phase13-retrieval-evidence/locomo_evidence_subset_100.json`
- Markdown: `tuning/runs/phase13-retrieval-evidence/locomo_evidence_subset_100.md`

Selection:

- 40 multi-hop
- 30 temporal
- 15 single-hop
- 15 open-domain
- Seed: `20260514`

Generation command:

```bash
.venv/bin/python analysis/locomo_evidence_subset.py \
  --data tuning/splits/peer_review_20260511/locomo_test.json \
  --manifest tuning/splits/peer_review_20260511/manifest.json \
  --output tuning/runs/phase13-retrieval-evidence/locomo_evidence_subset_100.json \
  --markdown tuning/runs/phase13-retrieval-evidence/locomo_evidence_subset_100.md
```

Observed output:

```json
{"candidate_counts": {"multi-hop": 168, "open-domain": 51, "single-hop": 464, "temporal": 157}, "category_counts": {"multi-hop": 40, "open-domain": 15, "single-hop": 15, "temporal": 30}, "selected_count": 100}
```

## Tooling added

- Subset generator: `analysis/locomo_evidence_subset.py`
- Annotation packet builder: `analysis/locomo_retrieval_annotation_packet.py`
- Manual retrieval scorer: `analysis/locomo_manual_retrieval_score.py`
- Tests:
  - `analysis/test_locomo_evidence_subset.py`
  - `analysis/test_locomo_retrieval_annotation_packet.py`
  - `analysis/test_locomo_manual_retrieval_score.py`

Verification:

```bash
.venv/bin/python -m pytest \
  analysis/test_locomo_evidence_subset.py \
  analysis/test_locomo_retrieval_annotation_packet.py \
  analysis/test_locomo_manual_retrieval_score.py \
  analysis/test_paired_locomo_delta.py \
  analysis/test_bootstrap_ci.py
```

Result: 14 passed.

## Rows to compare

Minimum retrieval evidence comparison:

- Full tuned: `tuning/runs/locomo-0029/run-00/result.json`
- Vector-only: `tuning/runs/locomo-0026/run-00/result.json`
- No associative graph: `tuning/runs/locomo-0032/run-00/result.json`
- No consolidation/deep recall: `tuning/runs/locomo-0033/run-00/result.json`
- No reinforcement: `tuning/runs/locomo-0031/run-00/result.json`

Optional add-ons if annotation time permits:

- Heuristic default: `tuning/runs/locomo-0030/run-00/result.json`
- No core promotion: `tuning/runs/locomo-0034/run-00/result.json`
- No retention weighting: `tuning/runs/locomo-0035/run-00/result.json`

## Annotation packet

Generated minimum comparison packet:

- JSON: `tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet.json`
- Markdown: `tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet.md`
- Rows: Full tuned, vector-only, no associative graph, no consolidation/deep recall, no reinforcement.
- Top-k shown per row: 20.

Generation command:

```bash
.venv/bin/python analysis/locomo_retrieval_annotation_packet.py \
  --subset tuning/runs/phase13-retrieval-evidence/locomo_evidence_subset_100.json \
  --row Full=tuning/runs/locomo-0029/run-00/result.json \
  --row Vector-only=tuning/runs/locomo-0026/run-00/result.json \
  --row 'No associative graph=tuning/runs/locomo-0032/run-00/result.json' \
  --row 'No consolidation/deep recall=tuning/runs/locomo-0033/run-00/result.json' \
  --row 'No reinforcement=tuning/runs/locomo-0031/run-00/result.json' \
  --top-k 20 \
  --output tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet.json \
  --markdown tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet.md
```

Observed output:

```json
{"items": 100, "top_k": 20}
```

The JSON packet is the source to annotate. The Markdown is only a readable guide.

## Annotation rule

For each retrieved memory, fill `covers_evidence_ids` with the LoCoMo evidence IDs that the memory fully or partially supports.

Example:

```json
{
  "rank": 3,
  "text": "Maria started aerial yoga and said it was great.",
  "covers_evidence_ids": ["D1:3"],
  "annotation_notes": "Captures activity and sentiment."
}
```

Leave `covers_evidence_ids` empty for irrelevant memories.

Complete-evidence recall for a question is satisfied when the union of covered IDs in top-k contains every evidence ID for that question.

## Scoring after annotation

Command:

```bash
.venv/bin/python analysis/locomo_manual_retrieval_score.py \
  tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet_annotated.json \
  --k-values 10 20 \
  --output tuning/runs/phase13-retrieval-evidence/retrieval_scores.json \
  --markdown tuning/runs/phase13-retrieval-evidence/retrieval_scores.md
```

Metrics:

- Recall@10 and Recall@20: average fraction of required evidence IDs covered by top-k retrieved memories.
- Complete@10 and Complete@20: fraction of questions where all required evidence IDs were covered by top-k retrieved memories.
- MRR: reciprocal rank of first retrieved memory covering any required evidence.

Report overall and by category, especially multi-hop and temporal.

## Interpretation rule

Strong architecture evidence would look like:

- Full tuned > vector-only on multi-hop complete evidence recall.
- Full tuned > no associative graph on multi-hop evidence recall.
- Full tuned > no consolidation/deep recall on overall or temporal evidence recall.
- Full tuned > no reinforcement on temporal or long-range evidence recall.

Mixed evidence should be reported as mixed. If no core promotion or retention weighting effects remain weak, do not claim strong validation for those mechanisms.

## Paper framing

Use this as controlled architecture evidence, not cross-paper benchmark evidence.

Suggested claim if results support it:

Controlled retrieval-level annotations show that the full memory architecture retrieves complete evidence more often on multi-hop and temporal held-out questions than vector-only retrieval and targeted mechanism ablations, supporting memory architecture as a first-class optimization target beyond answer-model choice.
