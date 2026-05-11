# Paper Update Plan

> Historical audit note. The May 2026 paper refresh is complete. Do not use this
> file as active guidance for manuscript numbers or benchmark status.

Current source-of-truth files:

- Manuscript: `paper/paper.tex`
- Latest PDF: `paper/cognitive-memory-arxiv-paper-v2.pdf`
- arXiv source bundle: `paper/arxiv-source/cognitive-memory-arxiv-source-20260507.tar.gz`
- Paper status map: `docs/paper.md`
- Benchmark registry: `docs/benchmarks-overview.md`
- Reproducibility record: `docs/current-refresh-20260505.md`
- Chronological logs: `experimentlog.md`, `experimentlog_v2.md`

## Completed Refresh

The original March draft pre-dated the benchmark refresh and described empirical
evaluation as future work. The current May 2026 manuscript now includes:

- a full Evaluation section,
- updated abstract, introduction, limitations, future work, conclusion, and code availability,
- LoCoMo current-refresh result: 44.8% overall F1, 48.5% multi-hop F1,
- LongMemEval-S current-refresh result: 71.6% task-averaged accuracy, 72.6% overall accuracy,
- LTI-Bench v2 result: 88.1% accuracy, 69.7% F1, 100% critical-fact retention,
- oracle evidence context, evidence recall, efficiency, feature activation, judge reliability, decay comparison, and ablation analyses,
- updated related work for ENGRAM, TiMem, EverMemOS, LoCoMo, and LongMemEval,
- sober framing: competitive architectural contribution, not a current leaderboard claim.

## Final Decisions

- Submit as arXiv v1. The March PDF was never posted.
- Use `cs.AI` as the primary category; cross-list to `cs.CL` and `cs.LG` if desired.
- Report only logged current-refresh artifacts in the paper.
- Treat historical Runs A-K/L/M as provenance, not active paper numbers.
- Keep single-seed and conv0-only ablation caveats in Limitations.
- Frame LongMemEval-S as competitive with ENGRAM-class single-stage systems while acknowledging newer TiMem/EverMemOS results.
- Keep NaiveRAG full-corpus comparison, LongMemEval-M, and multi-seed runs as future work.

## Remaining Before Submission

- Final human PDF proofread.
- arXiv UI metadata entry from `paper/arxiv-metadata.md`.
- Verify generated arXiv preview matches local PDF.
- After submission, record the arXiv ID in repo docs.
