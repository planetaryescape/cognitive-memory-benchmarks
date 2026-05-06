# Paper Status, Build, and Section Map

The paper is `paper/paper.tex` (target: arXiv). Latest build: `paper/cognitive-memory-arxiv-paper-v2.pdf` (25 pages, 1.1 MB, 2026-05-06). A tested source bundle is at `paper/arxiv-source/cognitive-memory-arxiv-source-20260506.tar.gz`. The previous build `cognitive-memory-arxiv-paper.pdf` (Mar 4, 17 pages) is kept on disk for diffing.

## 1. State

- **Title**: Cognitive Memory for AI Agents: Decay Floors, Emergent Core Memories, and Retrieval-Driven Reinforcement
- **Author**: Bhekani Khumalo (Independent Researcher), `hello@bhekani.com`
- **Date stamp**: May 2026 (was February 2026 in pre-update build)
- **Pages**: 25 (was 17)
- **arXiv version**: v1 when posted (paper has never been on arXiv; the Mar-4 build was a draft)
- **Status**: Updated 2026-05-06 with current-refresh LoCoMo/oracle/derived/LTI artifacts and recorded LongMemEval-S provenance. Build clean. Only cosmetic underfull hbox warnings remain.

## 2. Section map

| § | Section | Lines | Purpose |
|---|---|---|---|
| 1 | Introduction | 44–55 | Stateless LLMs problem, dead-zone framing, contributions list (5 contributions including evaluation) |
| 2 | Related Work | 56–93 | Taxonomic foundations, memory architectures, forgetting mechanisms, **NEW: concurrent and post-dating systems (ENGRAM, TiMem, EverMemOS)**, cognitive science foundations |
| 3 | Architecture | 96–301 | Memory representation, decay model (Eq. 1 + power-law variant), decay floors, core memory detection, retrieval scoring (Eq. 3), two-tier boosting (with Figs. 1 and 2 from simulations/), associative graph, consolidation, tiered storage (Fig. 3) |
| 4 | Design Comparison with FadeMem | 303–339 | Side-by-side comparison table (Evaluation row updated to point at §6) |
| 5 | Implementation | 340–372 | Adapter pattern, production deployment in blah.chat, audit log |
| **6** | **Evaluation** ⭐ NEW | 376–595 | Setup, LoCoMo, LongMemEval-S, Oracle Ceiling, Decay Comparison, Ablations, Retrieval Quality, Efficiency, Judge Reliability, LTI-Bench — 10 subsections, 6 tables |
| 7 | Limitations and Open Questions | 596–620 | Reframed: was "no benchmark eval", now Single-seed, LongMemEval-S only, conv-0 ablations, controlled LTI-Bench small-sample, SDK version straddle, plus retained limitations on parameters, never-delete debate, core thresholds, associative graph scaling, consolidation underspecification |
| 8 | Future Work | 621–636 | Reframed: was "do benchmark eval", now production-data validation, multi-seed, associative retrieval strengthening, cross-model generalisation, LongMemEval-M/Oracle |
| 9 | Conclusion | 638–642 | Updated closing paragraph with actual numbers (44.8% F1, 70.2% LongMemEval-S, etc.) |
| — | Code Availability | 644–652 | SDK + benchmarks repo URLs, npm/PyPI, and artifact provenance via `experimentlog.md` |

## 3. Tables and figures

| # | Asset | Source | Lines |
|---|---|---|---|
| Table 1 | Memory object schema | hand-written in tex | 102–119 |
| Table 2 | Base decay rates by category | hand-written in tex | 145–158 |
| Table 3 | Design comparison FadeMem vs ours | hand-written in tex | 308–334 |
| Table 4 | LoCoMo headline F1 vs Mem0 | NEW, from experimentlog | 405–414 |
| Table 5 | LongMemEval-S per-task accuracy | NEW, from longmemeval/results/v6/primary.json | 423–447 |
| Table 6 | Ablation per-feature delta | NEW, from ablations/ + Run C | 467–479 |
| Table 7 | Evidence Recall@k | NEW, from Run D | 491–500 |
| Table 8 | Per-stage timing | NEW, from Run F | 511–520 |
| Table 9 | LTI-Bench per-category | NEW, from Run L v2 | 555–580 |
| Figure 1 | Boosting divergence (single trajectory) | `paper/boosting_divergence.png` rendered from `simulations/boosting_divergence.pdf` | 233–238 |
| Figure 2 | Monte Carlo boosting analysis | `paper/monte_carlo.png` rendered from `simulations/monte_carlo.pdf` | 244–250 |
| Figure 3 | Tiered storage scaling | `paper/cold_storage.png` rendered from `simulations/cold_storage.pdf` | 294–298 |

Figures are *copied* into `paper/` for self-contained build (arXiv submission convention: source archive should be standalone). Alternative would be `\graphicspath{{../simulations/}}` but copying is simpler.

## 4. Bib entries

`paper/references.bib` has the full bibliography. Recent additions (2026-05-05 update):

| Cite key | Paper | Year | Used for |
|---|---|---|---|
| `maharana2024locomo` | LoCoMo dataset paper | 2024 (ACL) | Citing LoCoMo benchmark |
| `wu2024longmemeval` | LongMemEval | 2025 (ICLR) | Citing LongMemEval benchmark |
| `patel2025engram` | ENGRAM | 2025 (arXiv 2511.12960) | Concurrent baseline (LongMemEval SOTA at run time) |
| `li2026timem` | TiMem | 2026 (arXiv 2601.02845) | Post-dating system that exceeds our LongMemEval-S |
| `hu2026evermemos` | EverMemOS | 2026 (arXiv 2601.02163) | Post-dating system that exceeds our LongMemEval-S |

These are needed because the original Mar-4 paper had:
- No LoCoMo or LongMemEval citation (claimed no benchmark eval)
- No ENGRAM citation (didn't exist yet at Mar-4 draft time)
- No TiMem / EverMemOS citation (post-dated everything)

## 5. Build pipeline

### Tooling

- **Engine**: `tectonic` (single binary, ~16 MB). Installed via `brew install tectonic` on 2026-05-05.
- **Why tectonic** (not pdflatex/MacTeX): single binary, no system TeX install, downloads packages on demand, handles bibtex automatically, designed for reproducible academic builds. Trade-off: first run downloads packages (one-time, ~30 s).

### Build commands

```bash
cd ~/code/bhekanik/cognitive-memory-benchmarks/paper
tectonic paper.tex
# Output: paper.pdf
mv paper.pdf cognitive-memory-arxiv-paper-v2.pdf
```

Tectonic does multiple passes automatically (LaTeX, BibTeX, LaTeX, LaTeX) for cross-references. First run downloads ~50 small font and style files; subsequent runs are instant.

### Warnings to expect

The current build emits these warnings (all cosmetic, none are errors):

```
warning: paper.tex:316–331: Underfull \hbox in FadeMem comparison table
warning: paper.tex:384: Underfull \hbox in SDK provenance paragraph
warning: paper.tex:613: Underfull \hbox in preservation-first paragraph
warning: paper.tex:644: Underfull \hbox in Code Availability
```

These are typographic looseness warnings, not overflow or unresolved-reference errors.

### Build verification

After build, verify content rendered correctly:

```bash
cd ~/code/bhekanik/cognitive-memory-benchmarks/paper
pdftotext cognitive-memory-arxiv-paper-v2.pdf - | grep -E "ENGRAM|LongMemEval|TiMem|EverMemOS|44\.8|48\.5|70\.2|88\.1|69\.7|LTI-Bench"
# Should show citations as [Patel and Patel, 2025], [Li et al., 2026], [Hu et al., 2026]
```

If citations show as `[ENGRAM authors, 2025]` etc, the bib entries have placeholder authors and need fixing.

## 6. The Mar-4 → May-5 diff in plain English

### What was deleted

- Abstract paragraph: "An empirical evaluation with user data is planned as a follow-up study."
- Intro closing line: "An empirical evaluation using production data is planned as follow-up work."
- Limitations paragraph: "No benchmark evaluation yet" (entire paragraph).
- Future Work bullet: "Benchmark evaluation. Evaluating on MSC, LoCoMo, and LTI-Bench…"
- Design Comparison row: "Production deployment; benchmark evaluation planned"
- Conclusion sentence: "Whether they produce better outcomes than the alternatives is an empirical question we have not yet answered."
- FadeMem section sentence: "its benchmark evaluations demonstrating empirical improvements" (replaced — we have evals now too).

### What was added

- 5th contribution in the contributions list (the evaluation itself).
- "Concurrent and post-dating systems" paragraph in Related Work covering ENGRAM, TiMem, EverMemOS.
- Updated Design Comparison "Evaluation" row pointing at §6.
- Implementation closing now references §6 and §sec:future.
- New §6 Evaluation section with 10 subsections and 6 tables (the bulk of the diff).
- New Limitations paragraphs: single-seed, LongMemEval-S only/current-refresh provenance, conv-0 ablations, and LTI small-sample.
- New Future Work bullets: production data, multi-seed/full corpus ablations, associative retrieval strengthening, cross-model generalisation, LongMemEval-M/Oracle.
- Updated Conclusion paragraph with actual numbers.
- Code Availability extended: benchmarks repo URL, PyPI, and artifact provenance through `experimentlog.md`.

### Net change

- Lines: 421 → 652 (+231 lines)
- Pages: 17 → 24 (+7 pages)
- Sections: 8 → 9 (added §Evaluation)
- Tables: 3 → 9 (added 6 tables)
- Bib entries: ? → ?+5

## 7. The "we are no longer SOTA" reframing

The Mar-4 paper had no benchmark numbers, so framing was about architectural commitments alone. The May-5 update has numbers, and they don't put us at the top of the LongMemEval-S leaderboard:

- ENGRAM (Nov 2025) — 71.4% — concurrent baseline, what we lined up against
- **Ours** — 70.2% — within 1.2pp without benchmark-specific tuning
- TiMem (Jan 2026) — 76.88%
- EverMemOS (Jan 2026) — 83.0%

The newer systems (TiMem, EverMemOS) are *multi-stage* architectures (TiMem has a Temporal Memory Tree with semantic-guided consolidation; EverMemOS has episodic→semantic→reconstructive phases). Our system is *single-stage* — one router/retriever path. The framing in the new paper:

1. "Competitive with ENGRAM-class single-stage memory systems."
2. "Newer multi-stage architectures (TiMem, EverMemOS) exceed our LongMemEval-S accuracy. We acknowledge them so the result is not over-claimed."
3. "Our contribution is architectural (decay floors, emergent core, two-tier boosting), not benchmark-leading."

This is a deliberate positioning choice. It's defensible because:
- ENGRAM was SOTA at the time we ran. We compared against the right baseline.
- Our architectural contributions are independently interesting (decay floors, emergent core promotion are not in TiMem/EverMemOS).
- LTI-Bench (controlled architectural test) is where the architectural claims are exercised directly.
- Multi-hop F1 on LoCoMo is 1.7× Mem0 — that's a meaningful narrow win.

## 8. What's left to do on the paper

Before posting to arXiv, in priority order:

1. **Fix bib entry author lists** (DONE in current build) — was placeholders, now proper authors.
2. **Cosmetic hbox cleanup** (mostly done) — current build has underfull warnings only, no overfull boxes.
3. **Add table cross-references** in prose — e.g., explicitly cite Tables 5–9 inline. Currently they're at-end-of-paragraph; some are not cited at all in the prose. Check.
4. **Re-read Introduction + Abstract** — make sure they read naturally given the empirical addition. Don't just be a list of "we now have benchmarks."
5. **Sanity-check citations** — `pdftotext | grep` after a final build to confirm all citations resolved (no `[?]` markers).
6. **arXiv metadata**: title, authors, abstract, comments, primary class. The arXiv submission UI asks for these separately from the PDF.
7. **Final visual proof read** — open the PDF, scan every page, look for table overflow, broken figure refs, weird spacing.

Lower priority but worth flagging:
- The `paper-update-plan.md` lists 6 unresolved questions; all are now resolved (see end of that doc). The decisions are baked into the paper but the plan doc itself is preserved as audit trail.
- `paper/deep-recall-docs.md` is an internal reference doc that informed the deep-recall section; not used in build.
- `paper/cognitive-memory-arxiv-paper.pdf` is the Mar-4 draft kept for diff. Don't delete until we're sure the new version is final.

## 9. arXiv submission checklist

When ready to post:

- [x] All bib entries have real authors, no `{X authors}` placeholders.
- [x] PDF rebuilds clean.
- [x] Figure PNGs are all in `paper/` (boosting_divergence, monte_carlo, cold_storage); they are rendered from the canonical simulation PDFs to avoid Type 3 fonts in the final arXiv PDF.
- [x] No untracked LaTeX intermediates (`.aux`, `.log`, `.bbl`) get bundled into the source archive.
- [x] arXiv metadata draft: `paper/arxiv-metadata.md`.
- [x] Source archive — `paper/arxiv-source/cognitive-memory-arxiv-source-20260506.tar.gz` builds cleanly from a fresh extraction.
- [ ] Once submitted, capture the arXiv ID and add it to `\arxivversion` field if the next revision adds one.

## 10. The plan doc

`paper/paper-update-plan.md` is the executable plan we worked from. Sections:

- Section-level edits to existing tex (abstract, design comparison row, limitations, future work, code availability)
- New §Evaluation outline (now implemented as paper.tex §6)
- New Limitations content (now in paper.tex)
- New BibTeX entries needed (now added)
- Order of operations (Run L → bib → tables → §Eval → Abstract → Limitations → Future Work → Design row → date → build)
- Definition of done (checklist)
- Resolved questions (all 6 answered: ENGRAM citation, §placement, single PDF as v1, drop NaiveRAG column, Recall@k as table, single-seed acceptable for v1)
- New issues surfaced (stale SOTA framing, SDK version divergence, newer baseline citations)

The plan should still be readable as a reference for "what was the rationale" if questions come up about specific paper changes.
