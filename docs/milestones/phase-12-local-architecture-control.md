# Phase 12 - local architecture-control campaign

Status: complete. All full held-out local-model rows finished, and paired bootstrap deltas were generated.

Update 2026-05-15: first campaign stopped after vector-only completed because the full cognitive row exposed a SDK datetime comparison bug. SDK patch applied in `../cognitive-memory-sdk/sdks/python/src/cognitive_memory/engine.py`; targeted SDK tests pass.

## Claim split

- Benchmark-spec rows answer cross-paper comparability.
- This local architecture-control campaign answers whether memory-system configuration changes outcomes when the model, embeddings, prompts, question set, and retrieval budget are fixed.
- The local rows are not less legitimate evidence; they are a different instrument. They should not be mixed into headline benchmark comparisons.

## Purpose

Run the same local LM Studio architecture-control experiment that previously covered one held-out LoCoMo-test conversation across the entire held-out LoCoMo-test split.

Reviewer objections this is meant to address:

- The answer model carried the result.
- One conversation was lucky.
- The mechanism claims are vibes.
- Ablation effects are not paired or uncertainty-bounded.

## Fixed protocol

- Data: `tuning/splits/peer_review_20260511/locomo_test.json`
- Split size: 5 held-out LoCoMo-test conversations, 1,095 total questions before category filtering.
- Standard score subset: categories 1-4 only.
- Chat model: local LM Studio `openai/gpt-oss-120b`.
- Chat endpoint: `http://localhost:1234/v1`.
- Chat timeout: `OPENAI_CHAT_TIMEOUT=600`.
- Chat API key: `lm-studio`.
- Embeddings: OpenAI `text-embedding-3-small` retained by the SDK.
- Prompt mode: `mem0`.
- Answer temperature: default `0`.
- Retrieval budget: `--top-k 60` for all rows.
- Judge: disabled; token F1 only.
- Full/cognitive rows use `--dual-perspective --deep-recall --rerank --rerank-factor 3`; ablation configs can override adapter flags where intended.

## Rows

- Full tuned: `tuning/spaces/peer_review/locomo_dev_tuned_frozen.json`
- Vector-only: `naive_rag`, no config
- Heuristic default: `tuning/spaces/peer_review/heuristic_default.json`
- No reinforcement: `tuning/spaces/peer_review/frozen_ablations/no_reinforcement.json`
- No associative graph: `tuning/spaces/peer_review/frozen_ablations/no_associative_graph.json`
- No consolidation/deep recall: `tuning/spaces/peer_review/frozen_ablations/no_consolidation_deep_recall.json`
- No core promotion: `tuning/spaces/peer_review/frozen_ablations/no_core_promotion.json`
- No retention weighting: `tuning/spaces/peer_review/frozen_ablations/no_retention_weighting.json`

## New tooling

- Campaign runner: `tuning/scripts/run_local_architecture_control.py`
- Paired analysis: `analysis/paired_locomo_delta.py`
- Paired analysis tests: `analysis/test_paired_locomo_delta.py`
- Existing CI tests still covered by `analysis/test_bootstrap_ci.py`.

Tested:

```bash
.venv/bin/python -m pytest analysis/test_bootstrap_ci.py analysis/test_paired_locomo_delta.py
```

Result: 7 passed.

Dry-run command tested:

```bash
.venv/bin/python tuning/scripts/run_local_architecture_control.py \
  --dry-run \
  --row full \
  --row vector_only \
  --max-conversations 1 \
  --campaign-log tuning/runs/phase12-local-architecture-control/dry_run_campaign.jsonl
```

## Campaign start

Started at `2026-05-14T07:45:13Z`.

Background PID: `68050`.

Launch command:

```bash
nohup .venv/bin/python tuning/scripts/run_local_architecture_control.py \
  --endpoint "http://localhost:1234/v1" \
  --api-key "lm-studio" \
  --model "openai/gpt-oss-120b" \
  --timeout 600 \
  --campaign-log "tuning/runs/phase12-local-architecture-control/campaign.jsonl" \
  > "tuning/runs/phase12-local-architecture-control/campaign.out" 2>&1 &
```

Current first row at start: full tuned, expected trial `locomo-0025`.

Initial trial logs:

- `tuning/runs/locomo-0025/run-00/stdout.log`
- `tuning/runs/locomo-0025/run-00/stderr.log`

Campaign logs:

- `tuning/runs/phase12-local-architecture-control/campaign.jsonl`
- `tuning/runs/phase12-local-architecture-control/campaign.out`
- `tuning/runs/phase12-local-architecture-control/dry_run_campaign.jsonl`

## First campaign outcome

- Campaign PID: `68050`
- Campaign log: `tuning/runs/phase12-local-architecture-control/campaign.jsonl`
- Full tuned row: `locomo-0025`
- Full tuned status: failed after `48761.6s` with no `result.json`.
- Failure log: `tuning/runs/locomo-0025/run-00/stderr.log`
- Root cause: SDK compared offset-naive benchmark/search time against offset-aware LLM-extracted `valid_until`.
- Exact exception: `TypeError: can't compare offset-naive and offset-aware datetimes`.
- Stack location: `cognitive_memory/engine.py`, `_is_expired`.

Vector-only completed before stopping the campaign:

- Trial: `locomo-0026`
- Result: `tuning/runs/locomo-0026/run-00/result.json`
- Overall F1: `0.41342004778360464`
- Multi-hop F1: `0.18335388240451533`
- Temporal F1: `0.2818894915003092`
- Runtime: `12700.0s`

The campaign briefly started heuristic default as `locomo-0027` before it was stopped. Its orphaned `locomo.locomo_eval` child process was terminated manually. Treat `locomo-0027` as aborted/non-reportable; no `result.json` should be reported.

SDK fix:

- File: `/Users/bhekanik/code/bhekanik/cognitive-memory/cognitive-memory-sdk/sdks/python/src/cognitive_memory/engine.py`
- Added mixed naive/aware datetime comparison handling for expiry checks.
- Regression test: `/Users/bhekanik/code/bhekanik/cognitive-memory/cognitive-memory-sdk/sdks/python/tests/test_sdk.py`
- Verification: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_sdk.py -q`
- Result: 15 passed.

## Restart after SDK fix

Restarted remaining cognitive rows after excluding already-completed vector-only.

- New campaign PID: `98500`
- Campaign log: `tuning/runs/phase12-local-architecture-control/campaign_after_datetime_fix.jsonl`
- Process output: `tuning/runs/phase12-local-architecture-control/campaign_after_datetime_fix.out`
- Stop behavior: `--stop-on-error`
- Rows: full tuned, heuristic default, no reinforcement, no associative graph, no consolidation/deep recall, no core promotion, no retention weighting.
- First restarted trial: `locomo-0028` full tuned.

Launch command:

```bash
nohup .venv/bin/python tuning/scripts/run_local_architecture_control.py \
  --endpoint "http://localhost:1234/v1" \
  --api-key "lm-studio" \
  --model "openai/gpt-oss-120b" \
  --timeout 600 \
  --stop-on-error \
  --row full \
  --row heuristic_default \
  --row no_reinforcement \
  --row no_associative_graph \
  --row no_consolidation_deep_recall \
  --row no_core_promotion \
  --row no_retention_weighting \
  --campaign-log "tuning/runs/phase12-local-architecture-control/campaign_after_datetime_fix.jsonl" \
  > "tuning/runs/phase12-local-architecture-control/campaign_after_datetime_fix.out" 2>&1 &
```

This restart was stopped before completion because it did not yet include per-conversation checkpointing. Treat `locomo-0028` as aborted/non-reportable unless it has a `result.json` with `status: complete`.

## Guardrails added after the lost full row

Problem: `locomo-0025` ran for more than 13 hours and failed before final result serialization, so no partial results were preserved. This would be especially expensive with paid chat models.

Guardrails now in place:

- LoCoMo writes an atomic `result.json` checkpoint after every completed conversation whenever `--output` is set.
- Checkpoint files use top-level `status: partial` and `aggregate.meta.status: partial`.
- Complete runs overwrite the same file with `status: complete`.
- Campaign runner performs a deterministic SDK expiry preflight before any expensive row.
- Campaign runner still probes the local OpenAI-compatible endpoint and model list before starting rows.
- Campaign runner should be used with `--stop-on-error` for long rows.

Files changed:

- `locomo/locomo_eval.py`
- `locomo/test_locomo_eval_checkpoint.py`
- `tuning/scripts/run_local_architecture_control.py`
- `tuning/scripts/test_run_local_architecture_control.py`

Verification:

```bash
.venv/bin/python -m pytest \
  locomo/test_locomo_eval_checkpoint.py \
  tuning/scripts/test_run_local_architecture_control.py \
  analysis/test_bootstrap_ci.py \
  analysis/test_paired_locomo_delta.py
```

Result: 11 passed.

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_sdk.py -q
```

Run from `/Users/bhekanik/code/bhekanik/cognitive-memory/cognitive-memory-sdk/sdks/python`. Result: 15 passed.

Preflight dry-run:

```bash
.venv/bin/python tuning/scripts/run_local_architecture_control.py \
  --dry-run \
  --row full \
  --campaign-log tuning/runs/phase12-local-architecture-control/preflight_dry_run.jsonl
```

Result: SDK expiry preflight returned `sdk-expiry-preflight-ok` and the LM Studio model probe succeeded.

## Guardrailed restart

Restarted after checkpointing and SDK preflight guardrails were added.

- New campaign PID: `3694`
- Campaign log: `tuning/runs/phase12-local-architecture-control/campaign_after_guardrails.jsonl`
- Process output: `tuning/runs/phase12-local-architecture-control/campaign_after_guardrails.out`
- First guarded trial: `locomo-0029` full tuned.
- Preflight event: line 1 of `campaign_after_guardrails.jsonl`, return code `0`, stdout `sdk-expiry-preflight-ok`.
- Checkpoint behavior: `tuning/runs/locomo-0029/run-00/result.json` should appear after the first completed conversation with `status: partial`; final result should have `status: complete`.

Launch command:

```bash
nohup .venv/bin/python tuning/scripts/run_local_architecture_control.py \
  --endpoint "http://localhost:1234/v1" \
  --api-key "lm-studio" \
  --model "openai/gpt-oss-120b" \
  --timeout 600 \
  --stop-on-error \
  --row full \
  --row heuristic_default \
  --row no_reinforcement \
  --row no_associative_graph \
  --row no_consolidation_deep_recall \
  --row no_core_promotion \
  --row no_retention_weighting \
  --campaign-log "tuning/runs/phase12-local-architecture-control/campaign_after_guardrails.jsonl" \
  > "tuning/runs/phase12-local-architecture-control/campaign_after_guardrails.out" 2>&1 &
```

## Resumability added

Checkpointing preserves partial outputs, but resume support is what prevents recomputing completed conversations.

Added:

- `locomo/locomo_eval.py --resume`: loads existing `--output` checkpoint and continues from the next missing conversation.
- `tuning/scripts/run_trial.py --trial-id locomo-NNNN`: reuses an existing trial directory instead of creating a new one.
- `run_trial.py` backs up old `stdout.log` and `stderr.log` before a resumed attempt, preserving failure logs.
- `tuning/scripts/run_local_architecture_control.py --resume-trial row=locomo-NNNN`: resumes a specific row's existing trial.
- Campaign-generated LoCoMo commands now include `--resume` by default.

Verification:

```bash
.venv/bin/python -m pytest \
  locomo/test_locomo_eval_checkpoint.py \
  tuning/scripts/test_run_trial.py \
  tuning/scripts/test_run_local_architecture_control.py \
  analysis/test_bootstrap_ci.py \
  analysis/test_paired_locomo_delta.py
```

Result: 23 passed.

Dry-run verified resume command generation:

```bash
.venv/bin/python tuning/scripts/run_local_architecture_control.py \
  --dry-run \
  --row full \
  --resume-trial full=locomo-0029 \
  --campaign-log tuning/runs/phase12-local-architecture-control/resume_dry_run.jsonl
```

Generated command includes both `--trial-id locomo-0029` and LoCoMo `--resume`.

If current full row `locomo-0029` fails after one or more conversation checkpoints, resume it with:

```bash
.venv/bin/python tuning/scripts/run_local_architecture_control.py \
  --endpoint "http://localhost:1234/v1" \
  --api-key "lm-studio" \
  --model "openai/gpt-oss-120b" \
  --timeout 600 \
  --stop-on-error \
  --row full \
  --resume-trial full=locomo-0029 \
  --campaign-log "tuning/runs/phase12-local-architecture-control/campaign_resume_locomo_0029.jsonl"
```

If resuming manually without the campaign wrapper, use:

```bash
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark locomo \
  --trial-id locomo-0029 \
  --config tuning/spaces/peer_review/locomo_dev_tuned_frozen.json \
  --phase peer_review_local_lmstudio_locomo_test_full_split_full_tuned_resume \
  --score-keys aggregate.overall.mean_f1 aggregate.by_category.multi-hop.mean_f1 aggregate.by_category.temporal.mean_f1 \
  -- \
  --data tuning/splits/peer_review_20260511/locomo_test.json \
  --adapter cognitive_memory \
  --model openai/gpt-oss-120b \
  --prompt-mode mem0 \
  --top-k 60 \
  --resume \
  --quiet \
  --dual-perspective \
  --deep-recall \
  --rerank \
  --rerank-factor 3
```

Monitor commands:

```bash
ps -p 68050 -o pid=,stat=,etime=,command=
```

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
for line in Path('tuning/runs/phase12-local-architecture-control/campaign.jsonl').read_text().splitlines():
    event = json.loads(line)
    print(event['ts_utc'], event['event'], event.get('row'), event.get('returncode'))
PY
```

## Existing one-conversation paired smoke

Generated paired bootstrap/win-loss summaries for existing one-conversation smoke rows:

- JSON: `tuning/runs/phase12-local-architecture-control/smoke_paired_deltas.json`
- Markdown: `tuning/runs/phase12-local-architecture-control/smoke_paired_deltas.md`

Command:

```bash
.venv/bin/python analysis/paired_locomo_delta.py \
  --full tuning/runs/locomo-0014/run-00/result.json \
  --row Vector-only=tuning/runs/locomo-0015/run-00/result.json \
  --row 'Heuristic default=tuning/runs/locomo-0016/run-00/result.json' \
  --row 'No reinforcement=tuning/runs/locomo-0019/run-00/result.json' \
  --row 'No associative graph=tuning/runs/locomo-0020/run-00/result.json' \
  --row 'No consolidation/deep recall=tuning/runs/locomo-0022/run-00/result.json' \
  --row 'No core promotion=tuning/runs/locomo-0023/run-00/result.json' \
  --row 'No retention weighting=tuning/runs/locomo-0024/run-00/result.json' \
  --metrics overall single-hop multi-hop temporal open-domain \
  --output tuning/runs/phase12-local-architecture-control/smoke_paired_deltas.json \
  --markdown tuning/runs/phase12-local-architecture-control/smoke_paired_deltas.md
```

## Final full-split campaign outcome

Completed at `2026-05-21T11:32:03Z` with `failures: 0` in `tuning/runs/phase12-local-architecture-control/campaign_resume_after_embedding_connection.jsonl`.

Final row artifacts:

- Full tuned: `tuning/runs/locomo-0029/run-00/result.json`
- Vector-only: `tuning/runs/locomo-0026/run-00/result.json`
- Heuristic default: `tuning/runs/locomo-0030/run-00/result.json`
- No reinforcement: `tuning/runs/locomo-0031/run-00/result.json`
- No associative graph: `tuning/runs/locomo-0032/run-00/result.json`
- No consolidation/deep recall: `tuning/runs/locomo-0033/run-00/result.json`
- No core promotion: `tuning/runs/locomo-0034/run-00/result.json`
- No retention weighting: `tuning/runs/locomo-0035/run-00/result.json`

Final F1 rows, standard category 1-4 subset (`n=843`):

| Row | Trial | Overall | Multi-hop | Temporal | Open-domain | Single-hop |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Full tuned | `locomo-0029` | 0.4593 | 0.4091 | 0.5375 | 0.3016 | 0.4689 |
| Vector-only | `locomo-0026` | 0.4134 | 0.4354 | 0.1834 | 0.2819 | 0.4988 |
| Heuristic default | `locomo-0030` | 0.4079 | 0.3584 | 0.4470 | 0.2592 | 0.4296 |
| No reinforcement | `locomo-0031` | 0.4708 | 0.4110 | 0.5618 | 0.3210 | 0.4785 |
| No associative graph | `locomo-0032` | 0.4661 | 0.3840 | 0.5617 | 0.3167 | 0.4803 |
| No consolidation/deep recall | `locomo-0033` | 0.4341 | 0.3713 | 0.4946 | 0.3304 | 0.4481 |
| No core promotion | `locomo-0034` | 0.4795 | 0.4358 | 0.5482 | 0.3085 | 0.4915 |
| No retention weighting | `locomo-0035` | 0.4801 | 0.4221 | 0.5679 | 0.3242 | 0.4890 |

Paired full-minus-control analysis outputs:

- JSON: `tuning/runs/phase12-local-architecture-control/paired_deltas_all_rows.json`
- Markdown: `tuning/runs/phase12-local-architecture-control/paired_deltas_all_rows.md`

Command used:

```bash
.venv/bin/python analysis/paired_locomo_delta.py \
  --full tuning/runs/locomo-0029/run-00/result.json \
  --row vector_only=tuning/runs/locomo-0026/run-00/result.json \
  --row heuristic_default=tuning/runs/locomo-0030/run-00/result.json \
  --row no_reinforcement=tuning/runs/locomo-0031/run-00/result.json \
  --row no_associative_graph=tuning/runs/locomo-0032/run-00/result.json \
  --row no_consolidation_deep_recall=tuning/runs/locomo-0033/run-00/result.json \
  --row no_core_promotion=tuning/runs/locomo-0034/run-00/result.json \
  --row no_retention_weighting=tuning/runs/locomo-0035/run-00/result.json \
  --metrics overall multi-hop temporal open-domain single-hop \
  --n-boot 10000 \
  --seed 20260514 \
  --output tuning/runs/phase12-local-architecture-control/paired_deltas_all_rows.json \
  --markdown tuning/runs/phase12-local-architecture-control/paired_deltas_all_rows.md
```

Overall paired deltas, full minus control:

| Control | Control F1 | Delta | 95% CI | W/L/T |
| --- | ---: | ---: | --- | ---: |
| Vector-only | 0.413 | +0.046 | [0.019, 0.072] | 280/255/308 |
| Heuristic default | 0.408 | +0.051 | [0.031, 0.072] | 228/169/446 |
| No reinforcement | 0.471 | -0.011 | [-0.032, 0.009] | 193/220/430 |
| No associative graph | 0.466 | -0.007 | [-0.029, 0.015] | 211/224/408 |
| No consolidation/deep recall | 0.434 | +0.025 | [0.003, 0.048] | 227/198/418 |
| No core promotion | 0.479 | -0.020 | [-0.042, 0.000] | 200/223/420 |
| No retention weighting | 0.480 | -0.021 | [-0.042, 0.001] | 197/219/427 |

Interpretation:

- Full tuned beats vector-only, heuristic default, and no-consolidation/deep-recall on overall F1 with paired CIs above zero.
- Full tuned has a strong temporal advantage over vector-only (+0.354, 95% CI [0.282, 0.424]) and heuristic default (+0.090, 95% CI [0.037, 0.146]).
- Reinforcement, associative graph, core promotion, and retention weighting are weak/mixed or negative under this local off-spec setup. Do not claim strong validation for those mechanisms from this campaign.
- These rows are off-spec local architecture controls. They should not be mixed into headline benchmark comparisons against Mem0, FadeMem, ENGRAM, or other published rows.

Additional failure/fix provenance:

- `locomo-0033` initially failed on SDK month-relative date parsing (`ValueError: day 31 must be in range 1..30 for month 9 in year 2023`). Fixed in `/Users/bhekanik/code/bhekanik/cognitive-memory/cognitive-memory-sdk/sdks/python/src/cognitive_memory/extraction.py`; verification: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_temporal_reconstruction.py` returned 3 passed.
- `locomo-0033` later failed on transient OpenAI embeddings connection error and resumed successfully from its checkpoint.
- No `status: partial` row is reported as a final result.

## Retrieval-level evidence recall follow-up

This campaign covers end-to-end answer F1 under fixed local-model conditions. It does not yet prove that the retrieved evidence itself improved.

Next retrieval-isolation task:

- Select 50-100 held-out questions, biased toward multi-hop and temporal.
- Label required evidence spans or memory facts for each question.
- Compare full tuned, vector-only, no associative graph, no consolidation/deep recall, and no reinforcement.
- Report Recall@10, Recall@20, MRR, and complete-evidence recall for multi-hop questions.
- Keep this separate from answer F1 because it answers a cleaner causal question: whether the architecture retrieves the right evidence more often.
