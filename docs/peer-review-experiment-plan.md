# Peer-Review Experiment Plan

This plan is for a venue submission, not the current arXiv-ready paper. It converts the current claim from "competitive raw architecture" into a cleaner claim: heuristic defaults are competitive, disciplined tuning improves held-out performance, and ablations identify which lifecycle mechanisms carry signal.

## Rules

- Tune only on declared dev splits.
- Freeze one config before LoCoMo-test or LongMemEval-S transfer.
- Do not tune prompt wording in this campaign.
- Do not report a held-out result, change parameters, then report the same held-out split as clean.
- Report negative results and overlapping confidence intervals plainly.
- Treat these as protocol splits, not pristine benchmark holdouts. Full benchmark results were already inspected before this split existed.

## Split Creation

Create split metadata:

```bash
.venv/bin/python tuning/scripts/create_peer_review_splits.py
```

Create materialized split files for the existing runners:

```bash
.venv/bin/python tuning/scripts/create_peer_review_splits.py --materialize --force
```

Default split output: `tuning/splits/peer_review_20260511/`.

LoCoMo is split by conversation. LongMemEval-S is stratified by `question_type` and abstention flag.

## Frozen Rows

Run the heuristic baseline on both splits first:

```bash
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark locomo \
  --config tuning/spaces/peer_review/heuristic_default.json \
  --phase peer_review_baseline \
  --score-keys aggregate.overall.mean_f1 aggregate.overall.llm_accuracy \
  -- \
  --data tuning/splits/peer_review_20260511/locomo_dev.json \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --prompt-mode mem0 \
  --dual-perspective \
  --deep-recall \
  --rerank --rerank-factor 3 \
  --top-k 60 \
  --use-judge \
  --quiet
```

Repeat with `locomo_test.json` only after the tuning config is frozen.

## Random Search

Run a bounded random search on LoCoMo-dev:

```bash
.venv/bin/python tuning/scripts/run_optuna.py \
  --space tuning/spaces/peer_review/locomo_dev_random.json
```

If full LoCoMo-dev is too slow, use the proxy screen first:

```bash
.venv/bin/python tuning/scripts/run_optuna.py \
  --space tuning/spaces/peer_review/locomo_dev_proxy_random.json
```

The proxy screen is not reportable as final tuning evidence. It only selects candidates for full-dev confirmation.

Inspect the study and write the single frozen winner to `tuning/spaces/peer_review/locomo_dev_tuned_frozen.json`. Do not edit it after evaluating test or transfer.

## Held-Out And Transfer

Evaluate the frozen config once on LoCoMo-test:

```bash
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark locomo \
  --config tuning/spaces/peer_review/locomo_dev_tuned_frozen.json \
  --phase peer_review_locomo_test_once \
  --score-keys aggregate.overall.mean_f1 aggregate.overall.llm_accuracy \
  -- \
  --data tuning/splits/peer_review_20260511/locomo_test.json \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --prompt-mode mem0 \
  --dual-perspective \
  --deep-recall \
  --rerank --rerank-factor 3 \
  --top-k 60 \
  --use-judge \
  --quiet
```

Evaluate the same config unchanged on LongMemEval-S:

```bash
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark longmemeval \
  --config tuning/spaces/peer_review/locomo_dev_tuned_frozen.json \
  --phase peer_review_longmemeval_transfer \
  --score-keys aggregate.task_averaged_accuracy aggregate.overall_accuracy aggregate.abstention_accuracy \
  -- \
  --data tuning/splits/peer_review_20260511/longmemeval_s_test.json \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --top-k 20 \
  --deep-recall \
  --rerank --rerank-factor 3 \
  --max-workers 53 \
  --quiet
```

## Ablations

Run these on held-out splits with the same answer model, embedding model, prompt, and retrieval budget:

- Full tuned system: `locomo_dev_tuned_frozen.json`.
- No core promotion: `tuning/spaces/peer_review/ablations/no_core_promotion.json` layered on the tuned winner values.
- No reinforcement: `tuning/spaces/peer_review/ablations/no_reinforcement.json` layered on the tuned winner values.
- No retention weighting: `tuning/spaces/peer_review/ablations/no_retention_weighting.json` layered on the tuned winner values.
- No associative graph expansion: `tuning/spaces/peer_review/ablations/no_associative_graph.json` layered on the tuned winner values.
- No consolidation/deep recall: `tuning/spaces/peer_review/ablations/no_consolidation_deep_recall.json` layered on the tuned winner values.
- Vector-only baseline: same runner, `--adapter naive_rag`, same `--top-k` and answer prompt.

Current config files express the ablation deltas only. Before running the final campaign, create merged frozen ablation configs that start from `locomo_dev_tuned_frozen.json` and then apply each ablation override. This avoids accidentally comparing each ablation against SDK defaults instead of the tuned full system.

```bash
.venv/bin/python tuning/scripts/merge_trial_configs.py \
  tuning/spaces/peer_review/locomo_dev_tuned_frozen.json \
  tuning/spaces/peer_review/ablations/no_core_promotion.json \
  --output tuning/spaces/peer_review/frozen_ablations/no_core_promotion.json
```

## Uncertainty

Question-level LoCoMo CI:

```bash
.venv/bin/python analysis/bootstrap_ci.py \
  tuning/runs/<trial>/run-00/result.json \
  --metric locomo-f1 \
  --unit question
```

Conversation-level LoCoMo CI:

```bash
.venv/bin/python analysis/bootstrap_ci.py \
  tuning/runs/<trial>/run-00/result.json \
  --metric locomo-f1 \
  --unit conversation
```

LongMemEval-S task-level CI:

```bash
.venv/bin/python analysis/bootstrap_ci.py \
  tuning/runs/<trial>/run-00/result.json \
  --metric longmemeval-accuracy \
  --unit task
```

## Paper Claim If It Works

Use measured wording only:

"Reported arXiv results use heuristic or lightly tuned defaults. For peer-review experiments, we tuned on a declared LoCoMo development split, froze the configuration, and evaluated once on held-out LoCoMo conversations and unchanged LongMemEval-S transfer. Ablations under the same harness isolate the contribution of core promotion, reinforcement, retention weighting, associative expansion, and deep recall."

If tuning does not improve or does not transfer, say that. The result is still valuable because it bounds benchmark sensitivity and clarifies which lifecycle mechanisms matter.
