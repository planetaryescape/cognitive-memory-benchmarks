# Phase 15 — NaiveRAG-on-LoCoMo baseline

Status: COMPLETE (2026-05-27).

## Purpose

Add an in-house architectural-baseline column to the LoCoMo headline. The paper
previously cited only published external baselines (FadeMem, Mem0, MemGPT) from
different codebases. `NaiveRAGAdapter` (`shared/adapter.py:601`) defines a clean
vanilla-retrieval baseline (embed every turn, cosine top-k, no decay, no
extraction, no lifecycle) but had never been run on the full corpus until now.

Running NaiveRAG with the *same* harness, prompt, answer model, and data the
cognitive-memory v0.5 row uses isolates the architectural contribution: any
delta is attributable to the memory architecture, not to the answer model or
the prompt.

## Setup

- Harness: `locomo/locomo_eval.py`
- Adapter: `naive_rag`
- Data: `locomo/data/locomo10.json` (1986 total Qs, 1540 in cat 1-4)
- Answer model: `gpt-4o-mini`, temperature 0
- Prompt mode: `mem0` (matches the cognitive-memory v0.5 headline run)
- Top-k: 60 (mem0 default)
- Judge: disabled; token F1 only
- Embeddings: `text-embedding-3-small`

Wall time: 4357s (~73 min). Cost: ~$0.30 (embeddings + answers).

Artifacts: `locomo/results/naive_rag/run_n_v0.5.{json,log}`.

## Result (full LoCoMo, n=1540 cat 1-4, LoCoMo token F1)

Both result JSONs ship with the old category labels, but the counts are
invariant; mapping by `n` (multi-hop=282, temporal=321, open-domain=96,
single-hop=841):

| Category (by n) | n | CM v0.5 (`primary_merged`) | NaiveRAG | Delta |
|-----------------|--:|---------------------------:|---------:|------:|
| **temporal** | 321 | **48.47%** | **20.54%** | **+27.93pp** |
| multi-hop | 282 | 35.81% | 40.08% | −4.27pp |
| open-domain | 96 | 23.70% | 25.04% | −1.34pp |
| single-hop | 841 | 48.77% | 55.90% | −7.13pp |
| **Overall** | **1540** | **44.77%** | **43.71%** | **+1.06pp** |

Mem0-F1 method (set-based, no stemming): NaiveRAG overall 41.65%. BLEU-1: 31.86%.

Comparator note: `primary_merged.json` is the May 2026 v0.5 run with
`dual_perspective=True, deep_recall=True, rerank=True`. Its overall 44.77% is
the closest apples-to-apples cognitive-memory number to NaiveRAG on this
harness invocation. The README/paper headline of 46.2% comes from a different
snapshot of the v0.5 tuning iteration; either way the per-category direction is
the same.

## Reading

The architecture's value is sharper and narrower than the headline suggests:

- **Temporal: +28pp.** The full lifecycle architecture (decay, valid_time,
  consolidation, retention) is genuinely where the win lives — temporal F1
  ~2.4x NaiveRAG.
- **Multi-hop, open-domain, single-hop: NaiveRAG ties or slightly wins** by
  1-7pp. On these categories, dense top-60 retrieval over raw turns already
  captures the relevant evidence, and the architecture's extra machinery
  (extraction, decay, consolidation) doesn't help — and sometimes prunes or
  reorders memories in ways that mildly hurt.
- **Overall +1.06pp** is small. The mean is dominated by single-hop (n=841 of
  1540 = 55%), where NaiveRAG wins. The architecture's temporal advantage gets
  diluted at the corpus level.

This is consistent with Phase 13's evidence-recall finding (architecture wins
biggest on open-domain and temporal, loses on single-hop). The single-hop
result is honest and well-replicated across studies.

## Implication for the paper

The current paper claims a 46.2% / 51.3%-multi-hop headline against published
FadeMem/Mem0/MemGPT numbers (different codebases). Adding the NaiveRAG column
sharpens the architectural claim:

- **Strong claim**: "On temporal questions, the lifecycle architecture roughly
  doubles NaiveRAG's F1 (48.5% vs 20.5%); on simple lookups (single-hop), it is
  on par with or slightly behind a dense-retrieval baseline."
- **Weak claim avoided**: "memory architecture beats vanilla retrieval
  everywhere" — that's not what the data says.

The honest, narrow claim is the more interesting one. It also explains why the
Phase 14 temporal-reconstruction mechanism *helped per-conv but didn't move the
aggregate*: the temporal questions are 21% of the corpus, so a small per-Q lift
on them gets buried by the larger non-temporal bulk.

## Caveats

- One NaiveRAG run; no CI / multi-seed.
- gpt-4o-mini answer model only; not validated against other answer models.
- Comparator (`primary_merged.json`) has the old category labels in its JSON;
  mapped by count above.
- The CM v0.5 row used full feature config (dp + dr + rerank); NaiveRAG had no
  features to enable.
