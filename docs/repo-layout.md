# Repo Layout — Where Everything Lives

Two repos work together: the **SDK** (the published library) and the **benchmarks** (research code, paper, eval scripts). Both moved to `~/code/bhekanik/` on 2026-05-05 from the old `~/repos/` location.

## 1. The two repos

| Repo | Path | GitHub | Purpose |
|---|---|---|---|
| SDK | `~/code/bhekanik/cognitive-memory/` | `planetaryescape/cognitive-memory` | Published TS+Python SDK + Astro docs site |
| Benchmarks | `~/code/bhekanik/cognitive-memory-benchmarks/` | `planetaryescape/cognitive-memory-benchmarks` | Eval scripts, run results, paper.tex, experiment logs |

Plus one loose file:
- `~/code/bhekanik/cognitive-memory-sdk-v6-implementation-spec.md` — the v6 spec doc (185 lines). Reference for what got built in PR #1; not part of either repo. Could be copied into either repo's docs if you want it canonical.

## 2. SDK repo (`cognitive-memory/`)

```
cognitive-memory/
├── README.md
├── LICENSE
├── Makefile
├── package.json              # NB: untracked, just `{}` — abandoned npm init cruft, safe to delete
├── package-lock.json         # untracked
├── release-please-config.json
├── docs/                     # PUBLIC Astro docs site (NOT operator notes)
│   ├── astro.config.mjs
│   ├── package.json
│   ├── src/                  # MDX pages
│   ├── public/
│   ├── dist/                 # Build output
│   └── README.md
├── spec/                     # Canonical specs (markdown)
│   ├── memory-schema.md      # Memory object schema
│   └── adapter-interface.md  # Storage adapter contract
└── sdks/
    ├── typescript/
    │   ├── package.json      # NB: untracked package-lock.json
    │   ├── src/              # Source (see sdk-internals.md)
    │   ├── tests/
    │   ├── dist/
    │   └── ...
    └── python/
        ├── pyproject.toml
        ├── src/cognitive_memory/  # Source (see sdk-internals.md)
        ├── dist/
        └── tests/
```

### Branches and version state

```
* main                              ← clean, tracking origin/main
  docs/update-conflict-and-ingestion-docs   (merged via PR #3)
  refactor/humanize-and-fix-docs            (merged via PR #2)
  feat/sdk-v6-implementation                (merged via PR #1)
  remotes/origin/release-please--branches--main  (auto-managed)
```

Latest commits (descending):
- `905aba7` fix: configure npm auth for publish step
- `28c0151` Merge PR #4 (release-please)
- `e5d1127` chore: release main
- `131f556`/`3aad9f3` ci: add workflow_dispatch trigger
- `9c9fb85` Merge PR #3 (deferred-conflict docs update)
- `c6296fb` refactor: defer conflict detection from ingestion to tick
- `db393f9` chore: remove Python adapter stubs and phantom deps
- `300d6a0` refactor: remove deprecated MemoryType backward compat
- `a698f45` fix: persist memory mutations for non-InMemory adapters
- `60ee27e` chore: bump Python SDK version to 0.2.0 and fix SyncCognitiveMemory search signature ← **Runs A–K SDK**
- `9bf2e11` docs: document v6 features
- `7b7c15b` feat: wire v6 features through CognitiveMemory public API
- `34e1bc6` feat: add v6 retrieval pipeline
- `13a8dcf` feat: update extraction prompts for semantic types and add LLM reranking
- `89cf2f9` feat: add v6 data model

### Untracked files in SDK repo

```
package.json                          ← just `{}`, safe to delete
package-lock.json                     ← from accidental npm init
sdks/typescript/package-lock.json     ← may be gitignored elsewhere; check before committing
```

### Publish state

- **TypeScript**: `cognitive-memory` on npm.
- **Python**: `cognitive-memory` on PyPI.
- **Release-please**: configured for both. PRs auto-open with version bumps. The `905aba7` commit fixed npm auth.

## 3. Benchmarks repo (`cognitive-memory-benchmarks/`)

```
cognitive-memory-benchmarks/
├── README.md
├── pyproject.toml             # cognitive-memory-benchmarks 0.1.0
├── Makefile                   # (none — no build automation)
├── .venv/                     # uv-managed; recreated 2026-05-05 against SDK editable
├── experimentlog.md           # 525 lines, full run registry + changelog (UNTRACKED)
├── experimentlog_v2.md        # 149 lines, "remaining work" tracker (UNTRACKED)
├── check_status.py            # quick status helper
├── metrics.py                 # entry-point shim (canonical lives in shared/)
├── docs/                      # ← THIS DIR: operator notes (you're here)
├── paper/                     # arXiv paper source + build artifacts
│   ├── paper.tex              # 652 lines (was 421 pre-update)
│   ├── references.bib         # +5 entries: maharana2024locomo, wu2024longmemeval, patel2025engram, li2026timem, hu2026evermemos
│   ├── deep-recall-docs.md
│   ├── paper-update-plan.md   # ← the plan we executed for paper updates
│   ├── boosting_divergence.pdf
│   ├── monte_carlo.pdf
│   ├── cold_storage.pdf
│   ├── cognitive-memory-arxiv-paper.pdf      # Mar 4 build (kept for diff)
│   └── cognitive-memory-arxiv-paper-v2.pdf   # 5 May 2026 build, 24 pages, 241 KB
├── shared/                    # Cross-benchmark utilities
│   ├── adapter.py             # MemoryAdapter implementations (CognitiveMemoryAdapter, NaiveRAGAdapter, ...)
│   ├── memory_adapter.py      # Compatibility re-export (TS-style import path)
│   └── metrics.py             # token_f1, normalize_answer, llm_judge, retrieval_precision_at_k
├── locomo/                    # LoCoMo benchmark (Run A, D, E, F, G, H–K, M)
│   ├── locomo_eval.py         # Main eval driver
│   ├── data/locomo10.json     # 10 conversations, 1540 QA, evidence annotations
│   ├── results/v6/
│   │   ├── parallel/conv{0..9}.json  # Run A per-conv full results (per_question + aggregate)
│   │   ├── parallel/conv{0..9}.log   # stderr logs
│   │   ├── parallel/evidence_recall.json  # Run D
│   │   ├── ablations/{baseline, h_hybrid_on, i_hops0, j_rerank_off}.json  # Runs H–K
│   │   ├── debug_conv0.json   # debug run (76 min, F1 46.8%)
│   │   ├── efficiency_table.json  # Run F
│   │   ├── feature_activation.json  # Run G
│   │   ├── judge_reliability.json   # Run M
│   │   ├── oracle_ceiling.json      # Run E (LoCoMo prompt)
│   │   └── oracle_ceiling_mem0.json # Run E (Mem0 prompt re-run)
│   ├── efficiency_table.py    # post-processing (UNTRACKED)
│   ├── evidence_recall.py     # post-processing (UNTRACKED)
│   ├── feature_activation.py  # post-processing (UNTRACKED)
│   ├── judge_reliability.py   # Run M driver (UNTRACKED)
│   └── oracle_ceiling.py      # Run E driver (UNTRACKED)
├── longmemeval/               # LongMemEval-S benchmark (Run B)
│   ├── run_longmemeval.py
│   ├── data/longmemeval_s_cleaned.json   # 500 questions, 53 haystack/q
│   └── results/{cm_full_run.json, v6/primary.json}
├── lti/                       # LTI-Bench (Run L)
│   ├── lti_bench.py           # Synthetic 30-day controlled benchmark
│   └── results/
│       ├── v6_run_l.json      # v1 (superseded — substring scoring)
│       ├── v6_run_l.log       # v1 log
│       ├── v6_run_l_v2.json   # CANONICAL v2 results
│       └── v6_run_l_v2.log    # v2 log
├── memorybench/               # MemoryBench (not yet run)
├── simulations/               # Monte Carlo and decay simulations
│   ├── monte_carlo.py
│   ├── monte_carlo.pdf        # Figure 2 in paper
│   ├── boosting_divergence.pdf  # Figure 1 in paper
│   ├── cold_storage_sim.py
│   ├── cold_storage.pdf       # Figure 3 in paper
│   ├── decay_comparison.py    # Run C (UNTRACKED)
│   └── decay_comparison.json  # Run C results (UNTRACKED)
└── analysis/                  # Cross-benchmark analysis scripts (all UNTRACKED)
    ├── ablation_runner.py
    ├── efficiency_table.py
    ├── judge_reliability.py
    └── utilization_probe.py
```

### Branches

```
* main  ← clean tracking origin/main
```

Latest commit: `d6c28c1`. Most v6 work happened with `M` (modified) tracked files and many new untracked files — none of the post-March-9 work has been committed to the benchmarks repo yet.

### Tracked vs untracked status (as of 2026-05-05)

```
modified:    locomo/locomo_eval.py
modified:    longmemeval/results/cm_full_run.json
modified:    shared/adapter.py
untracked:   experimentlog.md, experimentlog_v2.md
untracked:   analysis/{ablation_runner,efficiency_table,judge_reliability,utilization_probe}.py
untracked:   locomo/{efficiency_table,evidence_recall,feature_activation,judge_reliability,oracle_ceiling}.py
untracked:   locomo/results/v6/* (all per-conv JSONs, ablations, post-processing outputs)
untracked:   longmemeval/results/v6/primary.json
untracked:   simulations/decay_comparison.{py,json}
untracked:   memorybench/repo/  (cloned vendor)
untracked:   docs/  (this dir)
untracked:   paper/paper-update-plan.md
untracked:   paper/cognitive-memory-arxiv-paper-v2.pdf
untracked:   paper/{boosting_divergence,monte_carlo,cold_storage}.pdf  (copied from simulations/)
untracked:   lti/results/v6_run_l*.{json,log}
```

There's significant uncommitted research work here. Whether to commit it depends on whether you want this repo to be reproducible (commit everything) or just a working area (keep .gitignore tight).

## 4. Build / dev environment

### SDK

- TypeScript: standard `npm`/`pnpm` workflow inside `sdks/typescript/`. `package.json` has build/test scripts.
- Python: `pyproject.toml` with hatchling backend. Built via `python -m build` or installed editable via `pip install -e .`.

### Benchmarks venv

```bash
cd ~/code/bhekanik/cognitive-memory-benchmarks
uv venv --python 3.14 .venv
uv pip install -e . -e ../cognitive-memory/sdks/python
```

The venv was rebuilt fresh on 2026-05-05 because the previous `.venv` had hardcoded `~/repos/...` paths from before the move.

Python: 3.14.4 from `/opt/homebrew/opt/python@3.14`.

### Paper

```bash
cd ~/code/bhekanik/cognitive-memory-benchmarks/paper
tectonic paper.tex
```

Tectonic was installed via `brew install tectonic` (~16MB binary, ~50MB total with deps). Single-binary, no system TeXLive dependency, downloads packages on demand. Handles bibtex automatically.

Figure PDFs (`boosting_divergence.pdf`, `monte_carlo.pdf`, `cold_storage.pdf`) live in `simulations/` canonically and are *copied* into `paper/` for self-contained build. Alternative: add `\graphicspath{{../simulations/}}` to paper.tex preamble; current setup chose copy for arXiv submission self-containment.

## 5. Key paths to remember

```bash
# SDK
~/code/bhekanik/cognitive-memory/sdks/typescript/src/core/engine.ts          # The retrieval pipeline
~/code/bhekanik/cognitive-memory/sdks/typescript/src/core/types.ts           # Schema + DEFAULT_CONFIG
~/code/bhekanik/cognitive-memory/sdks/python/src/cognitive_memory/core.py    # Python equivalent
~/code/bhekanik/cognitive-memory/spec/memory-schema.md                       # Canonical schema
~/code/bhekanik/cognitive-memory/spec/adapter-interface.md                   # Adapter contract

# Benchmarks
~/code/bhekanik/cognitive-memory-benchmarks/experimentlog.md                 # Full run registry
~/code/bhekanik/cognitive-memory-benchmarks/experimentlog_v2.md              # "Remaining work" tracker
~/code/bhekanik/cognitive-memory-benchmarks/paper/paper.tex                  # Paper source
~/code/bhekanik/cognitive-memory-benchmarks/paper/paper-update-plan.md       # Paper update plan
~/code/bhekanik/cognitive-memory-benchmarks/paper/cognitive-memory-arxiv-paper-v2.pdf  # Latest build
~/code/bhekanik/cognitive-memory-benchmarks/lti/lti_bench.py                 # LTI-Bench (recently refactored)
~/code/bhekanik/cognitive-memory-benchmarks/shared/metrics.py                # llm_judge lives here
~/code/bhekanik/cognitive-memory-benchmarks/shared/adapter.py                # Bench adapters

# Run results (LoCoMo)
~/code/bhekanik/cognitive-memory-benchmarks/locomo/results/v6/parallel/conv{0..9}.json
~/code/bhekanik/cognitive-memory-benchmarks/locomo/results/v6/ablations/{baseline,h_hybrid_on,i_hops0,j_rerank_off}.json

# Run results (LongMemEval)
~/code/bhekanik/cognitive-memory-benchmarks/longmemeval/results/v6/primary.json

# Run results (LTI)
~/code/bhekanik/cognitive-memory-benchmarks/lti/results/v6_run_l_v2.json
```
