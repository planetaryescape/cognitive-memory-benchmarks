# Next Steps

Explicit handoff for the next session — what's queued, what's blocked on what, and what we deliberately deferred.

## 1. State as of 2026-05-05 close-of-session

✅ Done in this session:
- Repos moved from `~/repos/` → `~/code/bhekanik/`
- Benchmarks venv recreated (uv, Python 3.14, SDK editable install)
- Bug fixed in `lti/lti_bench.py:357` (`from memory_adapter` → `from shared.memory_adapter`)
- Run L v1 (substring scoring, ingest-all-then-probe) — done, results superseded
- LTI-Bench refactored: time-stepped ingestion + LLM-as-judge + 17→42 probes + new `associative` category
- Run L v2 (canonical) — 88.1% accuracy, 100% critical retention, full per-category breakdown
- Both experimentlogs updated (run registry, changelog, full Run L details)
- Paper update plan written: `paper/paper-update-plan.md` with all 6 unresolved questions resolved
- `paper.tex` updated: new §Evaluation, abstract/intro/limitations/future-work/conclusion rewritten, Design Comparison table updated, +5 bib entries (LoCoMo, LongMemEval, ENGRAM, TiMem, EverMemOS), date bumped May 2026
- Paper rebuilt via `tectonic`: `paper/cognitive-memory-arxiv-paper-v2.pdf` (24 pages, 241 KB, citations resolved)
- `docs/` directory created with this set of operator notes

⚠️ Uncommitted across both repos:
- SDK repo: 3 untracked files (`package.json` (just `{}`), `package-lock.json`, `sdks/typescript/package-lock.json`). All probably noise.
- Benchmarks repo: significant — 2 untracked log files (`experimentlog.md`, `experimentlog_v2.md`), 3 modified files (`locomo/locomo_eval.py`, `longmemeval/results/cm_full_run.json`, `shared/adapter.py`), and ~25 untracked files including all Run A–M result JSONs, ablation scripts, post-processing scripts, paper PDFs, paper update plan, this whole `docs/` directory, `lti/lti_bench.py` changes, `lti/results/v6_run_l*.{json,log}`.

🟡 Pending decisions:
- Whether to commit the benchmarks-repo working state (everything noted above) or keep the repo as a working area with tight gitignore.
- Whether to fix the cosmetic LaTeX hbox warnings before final arXiv submission.
- Whether to copy figure PDFs into `paper/` permanently (current state) or use `\graphicspath{{../simulations/}}` and remove the copies.

## 2. Highest-priority pickups

In priority order — pick from the top.

### 2.1 Commit everything cleanly (1–2 hours)

The benchmarks repo has months of valuable research work uncommitted. Best ordering:

1. **Decide gitignore policy.** Probably want to commit the result JSONs (they're the empirical record), the post-processing scripts (analysis/, locomo/efficiency_table.py, etc.), the experimentlogs, the paper, and the docs. Probably don't want to commit `*.pid` files or `.venv/` (already gitignored).

2. **Commit in logical groups** with clear messages. Suggested grouping:
   - `chore: add experimentlogs and run registry` — experimentlog.md, experimentlog_v2.md
   - `feat: add Run A LoCoMo per-conv results and parallel runner` — locomo/results/v6/parallel/, locomo/locomo_eval.py changes
   - `feat: add Run B LongMemEval-S results` — longmemeval/results/v6/primary.json, longmemeval/results/cm_full_run.json
   - `feat: add Runs D–G post-processing scripts` — locomo/{evidence_recall,efficiency_table,feature_activation}.py, locomo/results/v6/{evidence_recall,efficiency_table,feature_activation}.json
   - `feat: add Runs H–K ablations` — analysis/ablation_runner.py, locomo/results/v6/ablations/, simulations/decay_comparison.{py,json}
   - `feat: add Run M judge reliability` — locomo/judge_reliability.py, locomo/results/v6/judge_reliability.json
   - `feat: add LTI-Bench v2 (time-stepped, llm_judge)` — lti/lti_bench.py changes, lti/results/v6_run_l_v2.{json,log}, lti/results/v6_run_l.{json,log}
   - `docs: add internal docs directory` — docs/
   - `docs: update paper.tex with §Evaluation and rebuild PDF` — paper/paper.tex, paper/references.bib, paper/paper-update-plan.md, paper/cognitive-memory-arxiv-paper-v2.pdf, paper/{boosting_divergence,monte_carlo,cold_storage}.pdf
   - `chore: cleanup adapter.py` — shared/adapter.py modifications

3. **For the SDK repo**: probably just `git clean -f` the empty `{}` package.json and the unused package-locks. Or leave them.

4. **Push.** `git push origin main` on each repo.

### 2.2 Resolve cosmetic LaTeX warnings (~30 minutes)

In `paper/paper.tex`:
- Line 317–332: FadeMem comparison table has long URLs causing underfull hbox. Solutions: `\sloppy` in scope, or `\url{}` with `\urlstyle{tt}` and breaks, or shorten the comparison text.
- Line 385: Limitations paragraph has 98pt overflow. Probably one specific embedded inline citation or punctuation. Reword the offending sentence.
- Line 590: Evaluation paragraph 2.9pt overflow — minor, may not even need fixing.
- Line 643: Code Availability long URL. Wrap in `\nolinkurl` or add explicit linebreak.

After fixing, rebuild with `cd paper && tectonic paper.tex && mv paper.pdf cognitive-memory-arxiv-paper-v2.pdf`.

### 2.3 Final paper read-through (~1 hour)

- Open the PDF, scan every page.
- Check that all 9 tables are referenced in prose (some new ones may not be).
- Check that the contributions list in the Introduction matches the abstract.
- Check Conclusion's numerical claims match Evaluation section's tables.
- Check there are no leftover `\todo{}` or commented-out paragraphs.
- Check arXiv-readiness: is the abstract a single paragraph (it is)? Are author affiliations present (they are)?

### 2.4 arXiv submission (~30 minutes once 2.2 and 2.3 are done)

- Generate source archive: `tar -czf cognitive-memory.tar.gz paper.tex references.bib *.pdf` from `paper/`.
- arXiv submission UI: title, authors, abstract (copy-paste from `\begin{abstract}`), primary class (cs.LG?), secondary class (cs.CL?), comments string.
- Capture arXiv ID once posted; update README and any future paper references.

## 3. Medium-priority work

### 3.1 Fix associative retrieval (1–2 days)

LTI-Bench v2 flagged associative retrieval as the architectural weak spot (60% accuracy on n=5 cross-fact queries). Candidate fixes ranked by ROI:

1. **Lower the `associationRetrievalThreshold`** from 0.3 → 0.2 for queries with classifier-detected "what do you know about X" pattern. Quick to test; may surface more from the cluster but also introduce noise.

2. **Increase `graphExpansionHops`** from 1 → 2 for the same query class. Already implemented, just needs a routing layer.

3. **Lower the synaptic tagging threshold** from 0.4 → 0.3 at ingestion. More aggressive cluster formation; risk of noisy associations.

4. **Add a query classifier** that routes "what do you know about X" / "tell me about X" / "what about X" patterns to a different retrieval policy with broader top-k and aggressive graph expansion. This is the "right" architectural fix but is more work.

To validate, re-run LTI-Bench v2 — associative category should jump from 60% → 90%+. Same controlled benchmark, same methodology, demonstrates causal effect of the fix.

### 3.2 Run NaiveRAG comparison on LoCoMo (1 day, ~$100 in API)

`shared/adapter.py:548` defines `NaiveRAGAdapter` but it has never been run on the full LoCoMo corpus. Adding this column to the headline F1 table would give an in-house architectural-mechanism contrast (vs Mem0/FadeMem published numbers, which come from different codebases).

If we do this, also run NaiveRAG through LTI-Bench. The expected per-category breakdown:
- core_persistence: probably passes (recent facts always retrievable)
- contextual: passes
- decay_trivial: probably passes (NaiveRAG doesn't decay, returns everything)
- revival: passes for the same reason
- conflict: FAILS — no supersession mechanism, returns both old and new
- temporal_before / temporal_after: FAILS — no time-aware retrieval
- associative: probably similar to ours (LoCoMo lacks bidirectional graph)

This contrast story would strengthen the paper's architectural claims significantly.

### 3.3 Multi-seed Run A (3 days, ~$300)

Run A on 3 different seeds, characterise variance. Convert the 44.8% F1 from a point estimate to "44.8% ± 1.X%". Same for multi-hop F1.

This is paper-quality but expensive. Defer unless we're targeting a venue that requires it (e.g., a top-tier conference vs arXiv).

### 3.4 LongMemEval-M run (2–3 days, ~$300, multi-day wall)

LongMemEval-M has ~10× the haystack of -S. Running it would let us compare directly against TiMem (76.88%) and EverMemOS (83.0%), both of which report -M numbers. Expected: we land somewhere in the middle. The point is to have the comparable number, not necessarily to win.

Currently the dataset isn't in `longmemeval/data/` — would need to download. The runner script (`run_longmemeval.py`) already supports arbitrary data files.

### 3.5 SDK release v0.3.0 to PyPI/npm (~2 hours)

The persistence-bug fixes and deferred conflict resolution are on `main` but not released. Run the release-please workflow (it's configured per `905aba7`). PyPI v0.2.0 is from 9 March; the fixes have been sitting in main since 11–12 March.

If we publish, update the paper's Code Availability section with the release date.

## 4. Low-priority / nice-to-have

### 4.1 LongMemEval-S re-run on SDK v0.3.0

We currently report Run B numbers from v0.2.0. If the persistence bugs affected LongMemEval (they probably did — the `single-session-preference` 36.7% might benefit from working stability reinforcement), re-running on v0.3.0 might bump the headline. Cost: ~11h wall, ~30M tokens.

### 4.2 LoCoMo full ablations (not just conv 0)

Runs H–K are conv 0 only. Full-corpus ablations would convert the per-feature deltas from point estimates to corpus-average estimates. Cost: ~4× Run A's cost (one run per ablation condition, all 10 convs). ~$400 + 8h wall.

### 4.3 Cross-model generalisation

Re-run with Claude or Llama answer model. Test whether the architectural advantages persist or are gpt-4o-mini-specific. Most paper-strengthening; most expensive.

### 4.4 Production-data validation study

The whole audit-log instrumentation in blah.chat is set up for this. The plan is in `paper.tex` Future Work. Requires actual user data and consent / privacy review — not just engineering.

## 5. Things explicitly NOT pursuing (and why)

- **MSC benchmark.** Mentioned in earlier draft Future Work as a target. Now lower priority because LongMemEval covers the same use case and we have those numbers.
- **MemoryBench.** Vendored at `memorybench/repo/` but not wired up. Would require integration work and may not add much over LongMemEval. Defer.
- **NaiveRAG-only paper sections.** Tempting to add a "we beat NaiveRAG by X" comparison, but our novelty is decay floors / emergent core, not "we beat naive baselines on QA." Don't dilute the architectural framing.
- **More cognitive science citations.** The paper already cites 13+ cognitive-science papers. Adding more would be padding; the existing set is already at the upper end of what's appropriate for an arXiv paper.
- **Custom adapter implementations.** Users can BYO; we don't need to ship more in-tree. The 4 we have (InMemory, JSONL, Postgres, Convex) cover most cases.

## 6. Decision frameworks worth saving (per CLAUDE.md memory rules)

Surfaced in [`lessons-and-gotchas.md`](./lessons-and-gotchas.md), §20. The user has not yet decided whether to save them as memory. Candidates:

1. Default to LLM-as-judge over substring/lexical scoring on QA benchmarks.
2. Defer LLM calls in hot paths; never inline-O(N²) them.
3. Time-step ingestion when probes need historical state.
4. Pin SDK version per-benchmark-run and document in experimentlog.
5. When a major Future Work item gets done, update Limitations / Future Work / Abstract immediately.
6. Use tectonic for one-shot academic builds (not MacTeX).
7. SOTA claims have short shelf life; frame on architectural class or pin to date.

The user can choose any subset to save with `/capture` or by asking explicitly.

## 7. The "fast resume" cheat sheet

If you're picking this up in a future session and want to be productive in 5 minutes:

```bash
cd ~/code/bhekanik/cognitive-memory-benchmarks

# Verify environment
.venv/bin/python -c "import cognitive_memory; print('SDK:', cognitive_memory.__version__)"
# Should print "SDK: 0.3.0"

# Look at recent logs
head -20 experimentlog_v2.md          # remaining-work tracker
git log --oneline -10                  # recent commits

# Read this docs index
cat docs/README.md
```

If anything in the docs/ index is stale (file moved, run results changed, etc.), update the relevant doc. The docs are themselves a working area, not a publication artifact.
