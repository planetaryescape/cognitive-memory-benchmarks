# arXiv Submission Handoff

Everything you need to submit the paper in one sitting. Open arXiv in one tab,
this checklist in another, and copy-paste.

## Before you start

- **arXiv account** with login working at https://arxiv.org/user — you need to
  be logged in.
- **Endorsement**: first-time submitters to `cs.AI` may need an endorsement
  code from an existing arXiv author in that category. Check
  https://arxiv.org/user/endorse if prompted.
- **Source bundle** (this build): `paper/arxiv-source/cognitive-memory-arxiv-source-20260526.tar.gz`
  (995 KB, source-only — paper.tex, references.bib, 3 PNG figures).
  arXiv builds the PDF from source; do not include `paper.pdf`.

## Decide first: incorporate new results, or submit as-is?

The current paper.tex does **not** include this session's findings:

- Phase 13 retrieval-evidence recall (Full > vector-only/ablations on every
  metric; +20pp open-domain, +10pp temporal evidence recall; deep-recall
  load-bearing). Validated κ=0.754.
- Phase 14 temporal reconstruction: classifier-precision fix landed; dev-slice
  shows +2.75pp temporal with 1.9% non-temporal FP (clean signal but n=40);
  default stays off pending the full held-out-split run (currently in flight).

These are **paper-relevant positive findings**. If you want them in v1, ask me
to add a §6.x "Controlled retrieval evidence" subsection + Phase 14 footnote
first, then re-tar and re-submit. If you submit now, they go in v2.

Submitting as-is is defensible: the current paper's claims stand independently
and the new results extend rather than contradict them.

## Submission flow (~10 min)

1. Go to **https://arxiv.org/submit**. Click "Start new submission".

2. **License**: select **CC BY 4.0** (recommended; matches the repo licenses).

3. **Article type**: "New submission" → "Standard arXiv".

4. **Upload files**: drag-drop or browse to
   `paper/arxiv-source/cognitive-memory-arxiv-source-20260526.tar.gz`. arXiv
   will extract and pre-process. Wait for "Process" to finish; verify the
   generated PDF preview (28 pages, 1.1 MB).

5. **Metadata** — copy-paste exactly:

   - **Title**:
     ```
     Cognitive Memory for AI Agents: Preservation-First Decay, Core Promotion, and Retrieval-Driven Reinforcement
     ```

   - **Authors** (one per row, `Last, First`):
     ```
     Khumalo, Bhekani
     ```

   - **Abstract** (single paragraph; do NOT add `\\begin{abstract}` wrappers):
     ```
     Most AI memory systems focus on extraction and retrieval, leaving the stored-memory lifecycle under-specified. We present cognitive-memory, an open-source agent-memory architecture that treats forgetting as reduced accessibility rather than immediate deletion. Memories decay through configurable curves, are reinforced on retrieval, can earn core status through sustained cross-session use, and migrate between hot, cold, and stub states with reversible consolidation and explicit deep recall. On LoCoMo, a v0.5 tuned configuration reaches 46.2% overall F1 and 51.3% multi-hop F1; on LongMemEval-S, a May 2026 current-refresh run reaches 71.6% task-averaged accuracy. A controlled LTI-Bench scenario recovers all identity-critical facts after 30 days, but a floors-off ablation shows unchanged critical retention, suggesting stability accumulation and softened retention weighting are more load-bearing than floor-clamping in this horizon. These results position cognitive-memory as a competitive single-stage memory architecture and expose open questions around longer-horizon decay, core-promotion thresholds, and associative retrieval.
     ```

   - **Comments**:
     ```
     28 pages, 10 tables, 3 figures. Code and benchmark artifacts available at https://github.com/planetaryescape/cognitive-memory and https://github.com/planetaryescape/cognitive-memory-benchmarks.
     ```

   - **Primary category**: `cs.AI`
   - **Cross-list**: `cs.CL`
   - **MSC / ACM class**: leave blank (none required).
   - **Report number / DOI / Journal ref**: leave blank.

6. **Preview**: review the generated PDF page-by-page. Watch for: missing
   citations, broken figures, layout regressions. The local `tectonic` build
   was clean except for 3 cosmetic underfull-hbox warnings on line 417 (loose
   lines; arXiv-acceptable).

7. **Submit**. arXiv will queue the submission; first-time submissions may sit
   in moderation for hours to a day before announcement.

8. After it appears, capture the **arXiv ID** (`arXiv:YYMM.NNNNN`) and:
   - update the SDK + benchmarks READMEs with the citation,
   - reference it in any future paper updates.

## If something goes wrong

- **"endorsement required for cs.AI"**: go to https://arxiv.org/user/endorse,
  request endorsement (you'll be given a code an existing cs.AI author can use
  to vouch for you), wait, retry.
- **PDF preview broken**: re-tar from
  `paper/arxiv-source/cognitive-memory-arxiv-source/` (excluding any stray
  `paper.pdf`). Run `tectonic paper.tex` locally first to reproduce.
- **Identity verification block**: arXiv may require ORCID linkage; bind your
  ORCID under "User → Configure".

## Files referenced

| What | Path |
|---|---|
| Source bundle | `paper/arxiv-source/cognitive-memory-arxiv-source-20260526.tar.gz` |
| Source directory | `paper/arxiv-source/cognitive-memory-arxiv-source/` |
| Metadata draft | `paper/arxiv-metadata.md` |
| Locally built PDF | `paper/paper.pdf` |
