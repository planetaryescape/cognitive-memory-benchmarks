# Lessons and Gotchas

Captured learnings from working on this project. These are the things that bit us, things that worked surprisingly well, and principles to apply next time.

## 1. Benchmark scoring

### Substring scoring is unreliable on free-form QA

LTI-Bench v1 used `expected_lower in answer_lower` for correctness. Result: 4 of 5 "failures" were judge-able-as-correct on inspection.

| Probe | Expected | Got | Substring? | Substantively correct? |
|---|---|---|---|---|
| revival weather | "nice this morning" | "weather was really nice on the morning of January 5" | ❌ | ✅ |
| temporal | "April 1st" | "April 1, 2024" | ❌ | ✅ |
| revival traffic | "traffic on my commute" | "traffic on Alex's commute on January 10" | ❌ | ✅ |
| conflict Helios | "April 1st" | "April 1, 2024" | ❌ | ✅ |

**Lesson:** Default to LLM-as-judge over substring/lexical scoring on free-form QA benchmarks. Substring fails on paraphrase, date format variants, pronoun shifts, and semantic equivalents. Wire `shared.metrics.llm_judge` (gpt-4o-2024-08-06) alongside token_f1; treat the judge as the headline metric and F1 as supplementary.

### Judge over-strictness still happens

Even with the LLM judge, 2 of 4 v2 LTI failures were over-strict ("April 1, 2024" vs "April 1st" — substantively the same date, marked WRONG). The judge prompt asks for "essential facts captured even if worded differently" but in practice gpt-4o-2024-08-06 was conservative on temporal phrasing.

**Lesson:** Even with LLM judges, surface F1 alongside accuracy. Large F1-vs-accuracy gaps (LTI revival: accuracy 80%, F1 43% — but both n=5) flag judge artifacts vs real partial recall.

### Judge reliability is load-bearing — measure it

Run M established κ = 0.919 inter-prompt agreement on 50 stratified samples. Without that number, the LongMemEval-S 70.2% headline would be hand-wavy. With it, we can defend the judge as the headline metric.

**Lesson:** If the headline depends on a judge, measure inter-prompt or inter-judge reliability as a separate run.

## 2. Inline LLM calls during ingestion are O(N²) and will hang

Run A first attempt hung at session 19 of conv 0. Diagnosis: inline conflict detection was making O(N²) LLM calls — for each new memory at session 19, check against ~hundreds of existing memories, each check is one LLM call.

**Fix architecture (deferred conflict resolution):**
1. At ingestion: cosine similarity check (cheap) — queue pairs with sim > 0.85 for resolution.
2. At maintenance tick: LLM-classify queued pairs (CONTRADICTION / UPDATE / OVERLAP / NONE).
3. Apply supersession only at tick time, batched.

**Lesson:** When LLM calls scale with the number of pairs, defer them. Inline LLM in a hot path is a footgun. If you're tempted to do it, ask "what happens at N=1000?" first.

### Threshold matters too

Initial threshold was cosine > 0.6 — produced 1422 false-positive candidates per conv 0. Raised to 0.85, count became manageable. The earlier value was costing money even *without* the inline call architecture.

**Lesson:** Similarity thresholds for "candidate for further processing" should be tuned to the false-positive rate at production scale, not chosen by intuition.

## 3. Time-stepped ingestion vs ingest-all-then-probe

LTI-Bench v1 ingested all 28 daily sessions before running any probes. Probes at day 10 fired against memory state at day 30 (because all sessions were already ingested), even though `timestamp=` was set to a day-10 date.

`timestamp=` is used by the SDK for *decay computation* (i.e., `Δt` in retention) but doesn't filter out memories ingested after the timestamp. There's no "as of T" query mode.

**Lesson:** If a benchmark queries the system at multiple time points where state should differ (because of supersession or insertion order), structure the runner to interleave ingestion and probes by simulated time. Don't rely on the `timestamp=` parameter to do time-travel queries — it doesn't.

## 4. Probe count vs sample size

LTI-Bench v1 had 17 probes total, with several categories at n=1. Statistical noise dominated; "0% accuracy on n=1" is meaningless.

**Lesson:** Even for confirmatory architectural tests, aim for n ≥ 5 per category and n ≥ 30 total. Below that, single-probe failures dominate the headline.

LTI-Bench v2 expanded to 42 probes / n=4–8 per category. Still small but interpretable.

## 5. SDK version divergence is real

Runs A–K used SDK v0.2.0 (commit `60ee27e`). Run L used v0.3.0 (post `905aba7`). The v0.3.0 fixes included:

- Stability reinforcement not persisted for non-InMemory adapters (would zero out reinforcement on every restart)
- Synaptic tagging associations not persisted
- Contradiction handling ordering bug

**Lesson:** When running benchmarks across multiple sessions weeks apart, pin the SDK version per-run and document it in the experimentlog. Treat any SDK update during the run window as a methodological caveat. Different runs may not be apples-to-apples.

We pinned the SDK version in the paper's Methodology and Code Availability sections; this is the right level of disclosure.

## 6. Documentation drift: "we have no benchmarks" → "we have benchmarks"

The Mar-4 paper had three places stating "no benchmark evaluation yet" or "evaluation planned":

1. Abstract closing line
2. Limitations section paragraph (`\paragraph{No benchmark evaluation yet.}`)
3. Future Work bullet

When the benchmark eval was actually done in March, none of these were updated for ~7 weeks. The paper was structurally wrong (claiming things planned that were done).

**Lesson:** Keep the paper as a living document. When a major Future Work item gets done, immediately update the paper sections that reference it (Abstract, Limitations, Future Work, Conclusion) — don't batch.

## 7. Stale SOTA claims age fast

The paper draft positioned 70.2% LongMemEval-S as "near ENGRAM SOTA". By the time we updated the paper (2 months later), TiMem (76.88%) and EverMemOS (83.0%) had been published. The framing was already obsolete.

**Lesson:** SOTA claims in long-horizon ML benchmarks have a short shelf life. Either:
1. Frame as "competitive with $X$-class systems" (positions on a class, not a number).
2. Pin to a date: "SOTA at the time of running, July 2025" — and accept being passed.

Avoid "near SOTA" as a permanent framing; it dates the paper.

## 8. The right time to install LaTeX is when you need to build

The Mar-4 PDF was built somewhere — possibly Overleaf or a previous machine setup. By 2026-05-05, no LaTeX engine was on the local machine. Building required `brew install tectonic` (~50 MB total).

**Lesson:** For research projects with PDF artifacts, document the build engine in the repo README. If using tectonic (recommended), a single `brew install tectonic` is sufficient. If using full TeXLive, document the dependency for arXiv submissions.

## 9. Figure PDFs need to live with the .tex

`paper.tex` references `boosting_divergence.pdf`, `monte_carlo.pdf`, `cold_storage.pdf`. The originals live in `simulations/`. Build failed initially because tectonic looked in `paper/` and didn't find them.

**Fix**: Copy the figure PDFs into `paper/`. Alternative: add `\graphicspath{{../simulations/}}` to preamble. We chose copy because arXiv submissions expect the source archive to be self-contained.

**Lesson:** For tex projects with figures generated elsewhere, decide once: copy or graphicspath. Document the choice.

## 10. Editable installs save time

The benchmarks venv uses `uv pip install -e ../cognitive-memory/sdks/python` — editable install of the SDK. This means SDK code changes are picked up immediately by benchmark runs without bumping versions or republishing.

**Lesson:** For projects where the library and consumers are co-developed, editable installs across local checkouts are the right default. Especially for research where you might want to test "what if I tweak the decay constant" without going through release.

The flip side: when running benchmarks for paper claims, capture the SDK version *and commit hash* in the experimentlog. Editable installs make it easy to introduce uncommitted changes that affect the result.

## 11. Process and PID tracking via `.pid` files

The benchmarks dir had several `.pid` files (`run_a.pid`, `run_b.pid`, etc.) tracking long-running processes. Pattern: `nohup python ... & echo $! > run_x.pid` so subsequent shells could check status.

This is rough but effective. The `check_status.py` helper reads these files and reports running/dead.

**Lesson:** For multi-hour parallel runs (Run A: 10 processes in parallel for 2h), a simple PID file pattern beats trying to remember tmux pane IDs or worrying about ssh disconnect.

## 12. Quota exhaustion is recoverable if the script supports `--resume-from`

Run A and Run B both hit OpenAI quota mid-run. Both resumed cleanly because `locomo_eval.py` and `run_longmemeval.py` accept `--resume-from <q_index>` and skip already-completed questions.

**Lesson:** For long benchmark runs, design resumability in from the start. Each question's result should be append-only (e.g., one line of JSONL per question, atomic write). The driver checks the output file at start and skips up to the last completed index.

## 13. The "near-SOTA without tuning" framing

We chose not to do benchmark-specific tuning for LongMemEval-S. With 70.2% / ENGRAM 71.4%, this is a 1.2pp gap that could plausibly close with a few task-specific knob adjustments. We didn't, and we said so in the paper.

This is a deliberate framing choice. It says "the architecture works in default config" rather than "we got 71.5% by tuning." The trade-off: we could have plausibly beaten ENGRAM with tuning, and we'd have a stronger headline. We chose the cleaner story.

**Lesson:** Decide upfront whether your headline claim is "out-of-the-box performance" or "best achievable performance." Don't slide between them in the paper. Each is defensible; mixing them isn't.

## 14. Hybrid search hurts on conversational text

Ablation H showed `hybrid_search: true` (BM25 + dense union) loses 1.1pp on LoCoMo conv 0. BM25's tokenisation and natural-language conversational text don't mix well — BM25 picks up lexical noise (frequent stopwords, proper-noun overlap) that dense embeddings handle better.

**Lesson:** Hybrid search is the default-good answer in academic benchmarks (especially document retrieval), but on conversational data with fluid pronouns and paraphrase, it can hurt. Test before turning on.

## 15. Power-law decay > exponential, by a lot

Ablation K showed power-law decay gives +3.6pp F1 on conv 0 vs exponential. This is the largest single-feature contribution in the ablation table.

This is consistent with cognitive science: human retention curves are heavy-tailed at long horizons; exponential underestimates retention for old memories. The paper's "decay floors never reach zero" claim partially captures this, but power-law captures it more precisely.

**Lesson:** When the cognitive science literature pushes one functional form, try it before committing to the alternative on convenience grounds. We had both implemented; we just had to flip the config.

We kept exponential as the SDK default because we have not characterised the gain across the full corpus and across multiple seeds. Conservative ship choice.

## 16. Figure 2's Monte Carlo is the best architectural visualisation

Figure 2 (`simulations/monte_carlo.pdf`) shows 500 randomised retrieval schedules under direct vs associative boosting. The key result: 76.8% of directly retrieved memories cross core threshold by day 90; 0% of associative-only memories ever do.

This figure is the best argument for the two-tier boosting design. The mechanism is simple (direct: +0.1, associative: +0.03), but the long-run consequence (one promotes, the other never does) is strikingly bimodal.

**Lesson:** When designing an architecture with two-tier dynamics, run a Monte Carlo across realistic randomised schedules. The aggregate behaviour is what matters; a single-trajectory plot (Figure 1) makes the point but a 500-run distribution (Figure 2) defends it.

## 17. The persistence-bug fixes were silent failures

Three persistence bugs lurked between v0.1.x and v0.2.0 fixes:
- Stability reinforcement not persisted (in-memory worked, postgres/convex didn't)
- Synaptic tagging not persisted
- Contradiction handling ordering bug

These were silent: tests passed (probably mostly using InMemoryAdapter), the system seemed to work, but in production with a non-InMemory adapter, reinforcement was being thrown away every cycle.

**Lesson:** When you have an adapter pattern, run integration tests against EVERY backing store (Postgres, Convex, JSONL, in-memory) for the operations that mutate state. The InMemoryAdapter is a happy-path liar — any state that happens to be on the in-memory object will appear to persist within a process even if the persistence-call is missing.

These bugs were caught by code review on PR #2. Without that review they'd still be in the codebase.

## 18. When a session has been quiet for 7 weeks, expect drift

The session that produced this work happened on 2026-05-05. The previous activity on this project was 2026-03-14 (~7 weeks earlier). In that gap:

- Three new SOTA-relevant papers were published (TiMem, EverMemOS, an ENGRAM revision).
- The local repos got moved (the .venv had stale absolute paths).
- The SDK gained a new version (v0.3.0) with persistence-bug fixes.
- The paper draft (Mar-4) became structurally stale relative to the eval results (Mar 9–14).

**Lesson:** When picking up research work after a long gap, the first move is *not* to start coding. The first move is:
1. Read the experimentlog and figure out where you left off.
2. Verify the environment still works (run a smoke test, e.g., `import cognitive_memory; print(cognitive_memory.__version__)`).
3. Search for new related papers (the field doesn't pause for you).
4. Update the paper's framing to reflect the current state of the field.

This session did all of these in the first hour and avoided wasting time on a stale plan.

## 19. Tectonic > MacTeX for one-shot academic builds

`brew install tectonic` is 16 MB, single binary, downloads packages on demand, handles bibtex automatically. `brew install --cask mactex` is 5 GB. For a project where you only build occasionally and don't need a full TeXLive, tectonic is the right answer.

**Lesson:** Don't reach for MacTeX by default. Use tectonic unless you specifically need a feature it lacks (rare).

## 20. Capture the framework, not just the answer

Per CLAUDE.md's "Decision Framework Capture" rule: when the user answers a question, identify whether it's a one-off or a general policy. If general, propose a framework with **Rule**, **Why**, **How to apply** lines, and ask whether to save.

This session generated several reusable rules worth capturing if the user wants:
- "Default to LLM-as-judge over substring scoring on QA benchmarks" (from §1)
- "Defer LLM calls in hot paths; never inline-O(N²) them" (from §2)
- "Time-step ingestion when probes need historical state" (from §3)
- "Pin SDK version per-benchmark-run and document in experimentlog" (from §5)
- "When a major Future Work item gets done, update the paper's Limitations / Future Work / Abstract immediately, don't batch" (from §6)

These haven't been saved as memory yet — surfaced for the user to choose from.
