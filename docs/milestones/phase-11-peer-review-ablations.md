# Phase 11 - peer-review ablations

Status: ablation configs prepared; benchmark execution blocked by OpenAI quota.

## Completed prep

- Frozen full-system reference: `tuning/runs/locomo-0012/run-00/result.json`
- Frozen ablation configs: `tuning/spaces/peer_review/frozen_ablations/`
- JSON validation passed for all frozen ablation configs.
- The source frozen config remains unchanged: `tuning/spaces/peer_review/locomo_dev_tuned_frozen.json`

Prepared configs:

- `tuning/spaces/peer_review/frozen_ablations/no_core_promotion.json`
- `tuning/spaces/peer_review/frozen_ablations/no_reinforcement.json`
- `tuning/spaces/peer_review/frozen_ablations/no_retention_weighting.json`
- `tuning/spaces/peer_review/frozen_ablations/no_associative_graph.json`
- `tuning/spaces/peer_review/frozen_ablations/no_consolidation_deep_recall.json`

## Blocked attempt

- Trial attempted: `locomo-0013`
- Row attempted: heuristic default on LoCoMo-test
- Split: `tuning/splits/peer_review_20260511/locomo_test.json`
- Failure: OpenAI `429 insufficient_quota` during the first extraction call
- Failure log: `tuning/runs/locomo-0013/run-00/stderr.log`
- Stdout before failure: `tuning/runs/locomo-0013/run-00/stdout.log`

No ablation metric should be reported from `locomo-0013`; it did not produce `result.json`.

## Resume commands

Do not retry until OpenAI quota is restored.

Heuristic default:

```bash
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark locomo \
  --config tuning/spaces/peer_review/heuristic_default.json \
  --phase peer_review_locomo_test_heuristic_default \
  --score-keys aggregate.overall.mean_f1 aggregate.overall.llm_accuracy aggregate.by_category.multi-hop.mean_f1 aggregate.by_category.temporal.mean_f1 \
  -- \
  --data tuning/splits/peer_review_20260511/locomo_test.json \
  --adapter cognitive_memory \
  --model gpt-4o-mini \
  --prompt-mode mem0 \
  --dual-perspective \
  --deep-recall \
  --rerank \
  --rerank-factor 3 \
  --top-k 60 \
  --use-judge \
  --quiet
```

Frozen ablations:

```bash
for name in no_core_promotion no_reinforcement no_retention_weighting no_associative_graph no_consolidation_deep_recall; do
  .venv/bin/python tuning/scripts/run_trial.py \
    --benchmark locomo \
    --config "tuning/spaces/peer_review/frozen_ablations/${name}.json" \
    --phase "peer_review_locomo_test_${name}" \
    --score-keys aggregate.overall.mean_f1 aggregate.overall.llm_accuracy aggregate.by_category.multi-hop.mean_f1 aggregate.by_category.temporal.mean_f1 \
    -- \
    --data tuning/splits/peer_review_20260511/locomo_test.json \
    --adapter cognitive_memory \
    --model gpt-4o-mini \
    --prompt-mode mem0 \
    --dual-perspective \
    --deep-recall \
    --rerank \
    --rerank-factor 3 \
    --top-k 60 \
    --use-judge \
    --quiet
done
```

Vector-only baseline:

```bash
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark locomo \
  --phase peer_review_locomo_test_vector_only \
  --score-keys aggregate.overall.mean_f1 aggregate.overall.llm_accuracy aggregate.by_category.multi-hop.mean_f1 aggregate.by_category.temporal.mean_f1 \
  -- \
  --data tuning/splits/peer_review_20260511/locomo_test.json \
  --adapter naive_rag \
  --model gpt-4o-mini \
  --prompt-mode mem0 \
  --top-k 60 \
  --use-judge \
  --quiet
```

CI commands after each successful LoCoMo ablation:

```bash
.venv/bin/python analysis/bootstrap_ci.py \
  tuning/runs/<trial>/run-00/result.json \
  --metric locomo-f1 \
  --unit question \
  --output tuning/runs/<trial>/run-00/bootstrap_ci_question.json

.venv/bin/python analysis/bootstrap_ci.py \
  tuning/runs/<trial>/run-00/result.json \
  --metric locomo-f1 \
  --unit conversation \
  --output tuning/runs/<trial>/run-00/bootstrap_ci_conversation.json
```

## Reporting rule

Report `locomo-0012` as the only completed held-out LoCoMo-test full-system result until these ablations finish. Report ablations as pending/quota-blocked, not as missing because of code failure.

## Off-spec local model smoke

To avoid additional OpenAI chat spend, we ran a one-conversation LoCoMo-test smoke with local chat via LM Studio and OpenAI embeddings. This is not a benchmark-spec result because extraction, reranking, answer generation, and any judge calls would use a different chat model. It is useful only as an architecture-control sanity check under the same local model.

- Local chat endpoint: `http://10.26.1.33:1234/v1`
- Local chat model: `openai/gpt-oss-120b`
- Embeddings: OpenAI `text-embedding-3-small`
- Split slice: first conversation from `tuning/splits/peer_review_20260511/locomo_test.json`
- Judge: disabled; compare token F1 only

Rows completed:

- Full tuned system: `locomo-0014`
- Vector-only baseline: `locomo-0015`
- Heuristic default: `locomo-0016`
- No reinforcement: `locomo-0019`
- No associative graph: `locomo-0020`
- No consolidation/deep recall: `locomo-0022`
- No core promotion: `locomo-0023`
- No retention weighting: `locomo-0024`

Results on the same conversation/model:

- Full tuned: overall 0.5283, multi-hop 0.5976, temporal 0.2918.
- Vector-only: overall 0.5142, multi-hop 0.1809, temporal 0.2841.
- Heuristic default: overall 0.4481, multi-hop 0.4501, temporal 0.2750.
- No reinforcement: overall 0.5122, multi-hop 0.5723, temporal 0.1147.
- No associative graph: overall 0.5170, multi-hop 0.5206, temporal 0.2500.
- No consolidation/deep recall: overall 0.4731, multi-hop 0.5261, temporal 0.1625.
- No core promotion: overall 0.5110, multi-hop 0.5415, temporal 0.2590.
- No retention weighting: overall 0.5262, multi-hop 0.5737, temporal 0.2637.

Full tuned deltas over controls:

- Versus vector-only: +0.0141 overall, +0.4168 multi-hop, +0.0077 temporal.
- Versus heuristic default: +0.0802 overall, +0.1476 multi-hop, +0.0168 temporal.
- Versus no reinforcement: +0.0161 overall, +0.0253 multi-hop, +0.1771 temporal.
- Versus no associative graph: +0.0113 overall, +0.0770 multi-hop, +0.0418 temporal.
- Versus no consolidation/deep recall: +0.0552 overall, +0.0715 multi-hop, +0.1293 temporal.
- Versus no core promotion: +0.0174 overall, +0.0562 multi-hop, +0.0328 temporal.
- Versus no retention weighting: +0.0022 overall, +0.0240 multi-hop, +0.0281 temporal.

Interpretation: this supports the architecture-control direction, especially on multi-hop questions, but it is a single-conversation off-spec smoke and should not be reported as a LoCoMo benchmark result. The tuned full row outperformed vector-only, heuristic default, and every local ablation on this same local model and split slice. The largest overall ablation deltas are no consolidation/deep recall and heuristic default. The largest multi-hop deltas are vector-only, heuristic default, no associative graph, and no consolidation/deep recall. The largest temporal deltas are no reinforcement and no consolidation/deep recall.

Non-reportable local attempts:

- `locomo-0017`: no-reinforcement row reached answer generation, then timed out on an LM Studio chat call after ingestion; no `result.json`.
- `locomo-0018`: retry failed immediately with `ConnectTimeout` to `http://10.26.1.33:1234/v1`; endpoint was not reachable from this machine; no `result.json`.
- `locomo-0021`: no-consolidation/deep-recall row was aborted by the user; no `result.json`.

Use `OPENAI_CHAT_TIMEOUT='600'` for any future LM Studio rows to avoid losing long runs to slow local completions. If the endpoint connect probe fails, do not start a benchmark row.

Re-run command for the full-system local smoke:

```bash
OPENAI_CHAT_BASE_URL='http://10.26.1.33:1234/v1' \
OPENAI_CHAT_API_KEY='lm-studio' \
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark locomo \
  --config tuning/spaces/peer_review/locomo_dev_tuned_frozen.json \
  --phase peer_review_local_lmstudio_locomo_test_full_smoke \
  --score-keys aggregate.overall.mean_f1 aggregate.by_category.multi-hop.mean_f1 aggregate.by_category.temporal.mean_f1 \
  -- \
  --data tuning/splits/peer_review_20260511/locomo_test.json \
  --adapter cognitive_memory \
  --model openai/gpt-oss-120b \
  --prompt-mode mem0 \
  --dual-perspective \
  --deep-recall \
  --rerank \
  --rerank-factor 3 \
  --top-k 60 \
  --max-conversations 1 \
  --quiet
```

Re-run command for the vector-only local smoke:

```bash
OPENAI_CHAT_BASE_URL='http://10.26.1.33:1234/v1' \
OPENAI_CHAT_API_KEY='lm-studio' \
.venv/bin/python tuning/scripts/run_trial.py \
  --benchmark locomo \
  --phase peer_review_local_lmstudio_locomo_test_vector_smoke \
  --score-keys aggregate.overall.mean_f1 aggregate.by_category.multi-hop.mean_f1 aggregate.by_category.temporal.mean_f1 \
  -- \
  --data tuning/splits/peer_review_20260511/locomo_test.json \
  --adapter naive_rag \
  --model openai/gpt-oss-120b \
  --prompt-mode mem0 \
  --top-k 60 \
  --max-conversations 1 \
  --quiet
```
