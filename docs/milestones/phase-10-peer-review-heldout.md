# Phase 10 — peer-review held-out evaluation

Status: LoCoMo-test complete; LongMemEval-S transfer blocked by OpenAI quota.

## Frozen config

- Config: `tuning/spaces/peer_review/locomo_dev_tuned_frozen.json`
- Selection source: proxy trial `locomo-0002`, confirmed on LoCoMo-dev by `locomo-0001`
- Discipline rule: no parameter edits after this point before held-out reporting.

## LoCoMo-test result

- Trial: `locomo-0012`
- Result: `tuning/runs/locomo-0012/run-00/result.json`
- Split: `tuning/splits/peer_review_20260511/locomo_test.json`
- Conversations: 5 held-out conversations
- Category 1-4 questions: 843
- Overall F1: 0.5012
- LLM judge accuracy: 0.6726
- Multi-hop F1: 0.5489
- Temporal F1: 0.2372
- Wall time: 24740.7s (~6h52m)

## LoCoMo-test uncertainty

- Question bootstrap CI: `tuning/runs/locomo-0012/run-00/bootstrap_ci_question.json`
- Question-level 95% CI: [0.4759, 0.5264]
- Conversation bootstrap CI: `tuning/runs/locomo-0012/run-00/bootstrap_ci_conversation.json`
- Conversation-level 95% CI: [0.4605, 0.5494]

## LongMemEval-S transfer blocker

- Trial attempted: `longmemeval-0001`
- Split: `tuning/splits/peer_review_20260511/longmemeval_s_test.json`
- Questions: 301
- Failure: OpenAI `429 insufficient_quota`
- Failure log: `tuning/runs/longmemeval-0001/run-00/stderr.log`
- Stdout before failure: `tuning/runs/longmemeval-0001/run-00/stdout.log`

This is an account/billing-quota blocker, not a frozen-config change. Do not retry until quota is restored.

Resume command after quota is restored:

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

Then compute transfer CIs:

```bash
.venv/bin/python analysis/bootstrap_ci.py \
  tuning/runs/<longmemeval-trial>/run-00/result.json \
  --metric longmemeval-accuracy \
  --unit question \
  --output tuning/runs/<longmemeval-trial>/run-00/bootstrap_ci_question.json

.venv/bin/python analysis/bootstrap_ci.py \
  tuning/runs/<longmemeval-trial>/run-00/result.json \
  --metric longmemeval-accuracy \
  --unit task \
  --output tuning/runs/<longmemeval-trial>/run-00/bootstrap_ci_task.json
```
