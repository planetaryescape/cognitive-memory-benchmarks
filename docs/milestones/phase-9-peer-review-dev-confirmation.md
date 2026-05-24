# Phase 9 — peer-review dev confirmation

Status: complete for dev confirmation; held-out evaluation not run yet.

## What happened

- Full LoCoMo-dev random search was launched first, but was stopped because one full-dev trial took over five hours.
- A cheaper proxy search was added: `tuning/spaces/peer_review/locomo_dev_proxy_random.json`.
- Proxy search ran 10 random configurations on one LoCoMo-dev conversation without LLM judge.
- Trial 0 won the proxy screen.
- The stopped full-dev job had already completed that same parameter vector across all 5 LoCoMo-dev conversations with judge enabled, so we reused it as the full-dev confirmation instead of rerunning the paid job.

## Artifacts

- Proxy study log: `tuning/runs/phase2/peer-review-locomo-dev-proxy-random.log`
- Proxy best trial: `locomo-0002`
- Full-dev confirmation result: `tuning/runs/locomo-0001/run-00/result.json`
- Frozen config: `tuning/spaces/peer_review/locomo_dev_tuned_frozen.json`
- Question bootstrap CI: `tuning/runs/locomo-0001/run-00/bootstrap_ci_question.json`
- Conversation bootstrap CI: `tuning/runs/locomo-0001/run-00/bootstrap_ci_conversation.json`

## Results

- Proxy best F1 on one dev conversation: 0.5121.
- Full-dev F1 across 697 category 1-4 questions: 0.5331.
- Full-dev LLM judge accuracy: 0.7059.
- Full-dev question-level 95% bootstrap CI: [0.5053, 0.5606].
- Full-dev conversation-level 95% bootstrap CI: [0.5038, 0.5782].

## Caveats

- The proxy screen is not reportable as final tuning evidence.
- The full-dev confirmation result was produced by the first full-dev search trial before the parent Optuna process was killed, so it is absent from the original full-search Optuna log but has a complete result artifact.
- Held-out LoCoMo-test and LongMemEval-S transfer have not been run.
