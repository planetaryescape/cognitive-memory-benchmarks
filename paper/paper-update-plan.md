# Paper Update Plan

> Historical update plan. Keep for decision history, but verify any benchmark or competitor claim against `../experimentlog.md`, `../experimentlog_v2.md`, and `../docs/context/v6-paper-review-and-competitors.md` before using it in the paper.

paper.tex is a Mar-4 draft. It pre-dates Runs A–M (Mar 9–14). Abstract, Limitations, and Future Work all promise benchmark eval as future. **Scope: major rewrite + new Evaluation section. Not a numeric refresh.**

Date stamp: bump from `February 2026` → release date (TBD).

---

## 1. Section-level edits to existing tex

### Abstract (line 40)
- Drop: "An empirical evaluation with user data is planned as a follow-up study."
- Drop: "An empirical evaluation using production data is planned as follow-up work." (intro line)
- Add 2–3 sentence summary of headline results: LoCoMo F1=45.6% (multi-hop 48.9%, 1.7× Mem0); LongMemEval-S 70.2% task-avg (within 1.2pp of ENGRAM SOTA without tuning); ablations identify power-law decay (+3.6pp) as biggest single gain.

### Design Comparison with FadeMem table (line 308)
- Row "Evaluation": change `Production deployment; benchmark evaluation planned` → `LoCoMo, LongMemEval-S, controlled LTI-Bench (this work)`.

### Limitations (line 374, paragraph at 383)
- Delete `\paragraph{No benchmark evaluation yet.}` block entirely — replaced by Evaluation section.
- Add new limitations paragraphs (see §3 below): LongMemEval-S only (not -M / -Oracle); single-seed runs; conv0-only ablations; gpt-4o-mini answer/extraction model only.

### Future Work (line 393)
- Remove "Benchmark evaluation" bullet (done).
- Add forward-looking: cross-model generalisation (Claude/Llama answer models); multi-seed runs; production deployment retrospectives; longer-horizon LTI variants.

### Code Availability (line 409)
- Add benchmarks repo URL: `github.com/planetaryescape/cognitive-memory-benchmarks`.
- Add SDK version pin: v0.2.0, commit `60ee27e`.

---

## 2. New section: Evaluation

Insert between `Design Comparison with FadeMem` (ends ~339) and `Implementation` (starts 340). Or — better — between `Implementation` and `Limitations`, so reader sees architecture → impl → results.

**Proposed structure:**

### 2.1 Setup
- Models: gpt-4o-mini extraction/answer, text-embedding-3-small embeddings, gpt-4o-2024-08-06 LongMemEval judge
- SDK v0.2.0 (commit 60ee27e), default v6 config (decay=exponential, hybrid_search=False, graph hops=1, rerank on)
- Hardware: M-series Mac, 128GB RAM
- Adapters: cognitive_memory (ours), naive_rag (baseline)

### 2.2 LoCoMo (Run A) — primary result
- 10 conversations, 1540 QA, mem0 prompt, dual-perspective ingestion, deep-recall, rerank×3, k=60, deferred conflict resolution
- **Headline table**: per-category F1 (single-hop / multi-hop / temporal / open-domain / adversarial) vs Mem0 / FadeMem / Naive RAG
- F1=45.6% overall, 48.9% multi-hop (1.7× Mem0's 28.4%)
- Per-conv breakdown table (conv0–conv9) — already in experimentlog Run A

### 2.3 LongMemEval-S (Run B)
- 500 questions, 53 haystack sessions/question, 6 task types
- Top-k=20, deep-recall, rerank
- **Table**: task-avg + per-task accuracy (single-session-{user,assistant,preference}, multi-session, temporal, knowledge-update) + abstention
- 70.2% task-avg vs ENGRAM 71.4% / full-context 56.2%
- Note: -S only (rationale in Limitations)

### 2.4 Oracle Ceiling (Run E)
- Ground-truth evidence as context, Mem0 prompt for fair comparison
- F1=63.9% (LoCoMo scoring) / 61.0% (Mem0 scoring)
- Run A achieves 71.4% of LoCoMo oracle ceiling

### 2.5 Decay Comparison (Run C)
- Power-law vs exponential on conv0
- Power-law +3.6pp F1 — supports paper's decay floor argument

### 2.6 Ablations (Runs H–K, conv0)
| Feature | Off | On | Δ |
|---|---|---|---|
| rerank | 43.2% | 45.0% | +1.8pp |
| graph_expansion (1 hop) | 44.4% | 45.0% | +0.6pp |
| hybrid_search | 45.0% | 43.9% | −1.1pp |
| power-law decay | 26.8% | 30.4% | +3.6pp (Run C) |

Discussion: power-law decay is the single biggest contributor; hybrid hurts (likely BM25 noise on conversational text); confirms paper's central decay argument.

### 2.7 Retrieval Quality (Run D)
- Evidence Recall@k on LoCoMo: R@5=24.9%, R@10=28.6%, R@20=31.8%, R@60=36.3%, n=1535
- Discussion: retrieval is the bottleneck; F1 of 45.6% achieved despite R@60 of only 36.3% suggests answer model robustness.

### 2.8 Efficiency (Run F)
- Extraction 14.1s/turn, vector search 54ms mean, scoring 0.69ms
- Note rerank/answer cost is deployment-dependent (not in SDK trace)

### 2.9 Feature Activation (Run G)
- 540 candidates/query average pre-filter, 60 retrieved
- Activation rates for graph expansion / validity filtering / bridge paths

### 2.10 Judge Reliability (Run M)
- 50 stratified QA pairs, alternative judge prompt
- κ=0.919, 96% raw agreement, 2 disagreements (both single-hop)
- Establishes judge as load-bearing for LoCoMo headline numbers

### 2.11 LTI-Bench (Run L) — TBD
- Synthetic 30-day scenario, 16 controlled facts
- Tests: decay / revival / core persistence / associative retrieval / conflict resolution / storage efficiency
- Direct test of paper's central architectural claims (decay floors, core memory promotion)

---

## 3. New Limitations content

- **LongMemEval scope**: -S only. -M/-Oracle skipped due to cost (~10× tokens, multi-day wall) and because -S already lands within 1.2pp of SOTA without tuning.
- **Single-seed**: each run is one seed. Variance not characterised.
- **Ablations on conv0 only**: full-corpus ablations skipped for cost. Effect sizes reported as point estimates, not population estimates.
- **Single answer model** (gpt-4o-mini): cross-model generalisation untested.
- **Extraction quality bound**: Run D Recall@60 of 36.3% suggests retrieval is below ceiling; F1 may be answer-model-dependent.

---

## 4. New BibTeX entries needed (references.bib)

Currently missing — add:
- `engram` — ENGRAM (LongMemEval SOTA) — find canonical citation
- `maharana2024locomo` — LoCoMo dataset paper (Maharana et al. 2024)
- `wu2024longmemeval` — LongMemEval paper (Wu et al. 2024)
- `openai2024gpt4o` — gpt-4o model card / report
- BM25 — `robertson2009bm25` (likely)

---

## 5. New figures/tables (work list)

| Asset | Source data | Format |
|---|---|---|
| LoCoMo headline table | experimentlog Run A "Per-Category Results" + baseline columns | LaTeX `tabular` |
| LoCoMo per-conv breakdown | locomo/results/v6/parallel/conv*.json aggregates | LaTeX `tabular` |
| LongMemEval-S task table | longmemeval/results/v6/primary.json | LaTeX `tabular` |
| Ablation table | experimentlog Ablation Summary | LaTeX `tabular` |
| Recall@k curve | run_d evidence_recall results | tikz or pdf |
| Efficiency table | locomo/results/v6/efficiency_table.json | LaTeX `tabular` |
| LTI-Bench results | TBD (Run L pending) | TBD |

---

## 6. Order of operations

1. **Run L** — LTI-Bench (pending). Required before paper update — adds §2.11 numbers.
2. **Add bib entries** — ENGRAM, LoCoMo, LongMemEval, gpt-4o, BM25.
3. **Generate tables** — pull numbers from json result files into a `tables.tex` include or inline.
4. **Insert §2 Evaluation** — between Implementation and Limitations.
5. **Rewrite Abstract + Intro closing paragraph** — drop "planned" language, add headline numbers.
6. **Edit Limitations + Future Work** — drop benchmark-related claims, add new caveats.
7. **Edit Design Comparison row + date stamp**.
8. **Rebuild PDF** (`pdflatex paper.tex` × 2 + `bibtex paper`).
9. **Diff old vs new PDF**, commit, optionally upload to arXiv.

---

## 7. Definition of done

- [ ] Run L results in experimentlog.md and v2
- [ ] §2 Evaluation section drafted with all run results
- [ ] Abstract + Intro updated, no "planned evaluation" language remains
- [ ] Limitations section reflects actual scope (no "no benchmark eval")
- [ ] Future Work no longer lists benchmark eval
- [ ] Design Comparison table row updated
- [ ] All cited works have bib entries (engram, locomo, longmemeval especially)
- [ ] PDF rebuilds clean, no missing-ref warnings
- [ ] Paper version + date bumped

---

## Resolved questions

### Q1 — ENGRAM citation
**Resolution**: Cite as `wu2025engram`, arXiv:2511.12960 (Nov 2025). Title "ENGRAM: Effective, Lightweight Memory Orchestration for Conversational Agents".

**Important downstream finding**: ENGRAM is no longer SOTA. As of Jan 2026, two newer systems beat it on LongMemEval-S:
- **TiMem** — 76.88% (gpt-4o-mini)
- **EverMemOS** — 83.0% overall

Our 70.2% (Mar 2026 result) is no longer "near-SOTA" — it's "near-ENGRAM". Paper framing must update:
- Replace "near ENGRAM SOTA" with "competitive with ENGRAM-class single-stage memory systems"
- Add TiMem and EverMemOS to Related Work as concurrent / newer systems and acknowledge they outperform our result on LongMemEval-S
- Reposition our contribution as **architectural** (decay floors, emergent core) rather than benchmark-leading

### Q2 — §Evaluation placement
**Resolution**: Insert between `Implementation` and `Limitations` (i.e. after line 374, before "Limitations and Open Questions").

**Why**: Standard ML paper flow — Method → Implementation → Evaluation → Limitations → Future Work. Reader knows the architecture and how it's deployed before seeing how it performs. Keeps Design Comparison adjacent to Architecture as a theoretical contrast section.

### Q3 — Single PDF revision or arXiv v2?
**Resolution**: Single fresh PDF, treated as **arXiv v1** when posted.

**Why**: The Mar-4 PDF was a draft, never posted to arXiv (no arXiv ID anywhere in tex / repo). No `\arxivversion` field, no submission log. So this is the first public revision, not a v2.

### Q4 — Naive RAG baseline column?
**Resolution**: **Drop** for v1. Use Mem0's published numbers as the comparison baseline (already in tex repo bib).

**Why**: NaiveRAG runs on full LoCoMo were never executed (Run A was cognitive_memory only). Adding the column requires a fresh ~$X parallel run — engineering overhead with limited paper benefit. Mem0 + full-context (LongMemEval) baselines are sufficient; both use comparable backbones. Move to Future Work as an in-house ablation candidate.

### Q5 — Run D Recall@k as table or figure?
**Resolution**: **Table**.

**Why**: 4 data points (k ∈ {5, 10, 20, 60}) doesn't justify a figure. Table is denser, embeds inline, no PDF figure machinery, no caption overhead.

### Q6 — Single-seed for v1?
**Resolution**: **Yes, ship single-seed**. Document as a Limitations bullet.

**Why**:
- Comparators (Mem0, FadeMem, ENGRAM, TiMem) all report single-seed results — multi-seed adds engineering effort without comparability gain.
- Cost: full LoCoMo Run A took ~2h parallel + significant tokens. 3 seeds = 3× that. LongMemEval-S = 11h × 3 = 33h, plus quota risk.
- Multi-seed is meaningful future work, not a blocker.

---

## New issues surfaced during resolution

1. **Stale SOTA framing throughout paper** — every "near-SOTA" or "competitive with SOTA" claim about LongMemEval-S needs to be reframed as "competitive with ENGRAM" with explicit acknowledgement of newer systems (TiMem, EverMemOS). This affects: Abstract, Run B description, Key Findings.

2. **Run-time SDK divergence** — Runs A–K used SDK v0.2.0 (commit 60ee27e). Run L v2 (and any rerun) uses v0.3.0 with persistence-bug fixes and deferred conflict resolution. Worth a short Methodology paragraph noting which runs used which SDK version, or a footnote.

3. **Newer baseline citations needed** — bib entries:
   - `wu2025engram` — arXiv:2511.12960
   - `maharana2024locomo` — arXiv:2402.17753 (ACL 2024, pages 13851–13870)
   - `wu2024longmemeval` — arXiv:2410.10813 (ICLR 2025)
   - `timem2026` and/or `evermemos2026` — find canonical refs before posting
