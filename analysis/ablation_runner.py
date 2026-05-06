#!/usr/bin/env python3
"""
Ablation study runner: test individual v6 features on LoCoMo conv0.

Runs 4 ablation pairs:
  H: hybrid_search on/off
  I: graph_expansion_hops 0 vs 1
  J: rerank on/off
  K: decay_model exponential vs power

Each pair runs on conv0 only (~10 min each). Results compared in a table.

Usage:
    python analysis/ablation_runner.py --data locomo/data/locomo10.json
    python analysis/ablation_runner.py --data locomo/data/locomo10.json --ablation H
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.adapter import CognitiveMemoryAdapter, _parse_timestamp
from shared.metrics import token_f1, token_f1_mem0, bleu1, LOCOMO_CATEGORIES


def run_ablation(data, conv_index, adapter_kwargs, prompt_mode="mem0", top_k=60,
                 model="gpt-4o-mini", dual_perspective=True):
    """Run LoCoMo eval on one conversation with specified adapter config."""
    adapter = CognitiveMemoryAdapter(**adapter_kwargs)

    conv = data[conv_index]
    conv_data = conv.get("conversation", {})
    speaker_a = conv_data.get("speaker_a", "Speaker A")
    speaker_b = conv_data.get("speaker_b", "Speaker B")

    # Ingest
    session_keys = sorted(
        [k for k in conv_data if k.startswith("session_") and not k.endswith(("_date_time", "_observation", "_summary"))],
        key=lambda x: int(x.split("_")[1])
    )

    adapter.reset()
    for session_key in session_keys:
        timestamp = conv_data.get(f"{session_key}_date_time", "")
        turns = conv_data.get(session_key, [])
        turn_list = [{"speaker": t.get("speaker", ""), "text": t.get("text", ""), "dia_id": t.get("dia_id", "")} for t in turns]

        if dual_perspective:
            # Ingest twice (speaker A as user, speaker B as user)
            adapter.ingest_session(turn_list, session_key, timestamp, speaker_a, speaker_b)
        else:
            adapter.ingest_session(turn_list, session_key, timestamp, speaker_a, speaker_b)

    # Query
    from openai import OpenAI
    from locomo.locomo_eval import generate_answer, PROMPT_MEM0
    client = OpenAI()

    qa_items = conv.get("qa", [])
    results = []

    last_ts = None
    for sk in session_keys:
        ts_str = conv_data.get(f"{sk}_date_time", "")
        if ts_str:
            last_ts = ts_str

    for qi, qa in enumerate(qa_items):
        category = qa.get("category", 0)
        query_result = adapter.query(qa["question"], timestamp=last_ts, top_k=top_k)

        from shared.adapter import QueryResult
        answer = generate_answer(
            question=qa["question"],
            query_result=query_result,
            client=client,
            model=model,
            prompt_mode=prompt_mode,
            speaker_a=speaker_a,
            speaker_b=speaker_b,
        )

        raw_answer = qa.get("answer", qa.get("adversarial_answer", ""))
        ground_truth = str(raw_answer) if raw_answer is not None else ""
        f1_result = token_f1(answer, ground_truth)

        results.append({
            "question_index": qi,
            "category": category,
            "f1": f1_result["f1"],
        })

    # Aggregate
    valid = [r for r in results if r.get("category", 5) <= 4]
    overall_f1 = sum(r["f1"] for r in valid) / len(valid) if valid else 0

    by_cat = {}
    for cat_id, cat_name in LOCOMO_CATEGORIES.items():
        if cat_id == 5:
            continue
        cat_results = [r for r in valid if r["category"] == cat_id]
        if cat_results:
            by_cat[cat_name] = sum(r["f1"] for r in cat_results) / len(cat_results)

    return {"overall_f1": overall_f1, "by_category": by_cat, "per_question": results}


ABLATIONS = {
    "H": {
        "name": "hybrid_search",
        "conditions": {
            "off": {"hybrid_search": False},
            "on": {"hybrid_search": True},
        },
    },
    "I": {
        "name": "graph_expansion_hops",
        "conditions": {
            "0": {"graph_hops": 0},
            "1": {"graph_hops": 1},
        },
    },
    "J": {
        "name": "rerank",
        "conditions": {
            "off": {"rerank": False},
            "on": {"rerank": True, "rerank_factor": 3},
        },
    },
    "K": {
        "name": "decay_model",
        "conditions": {
            "exponential": {"decay_model": "exponential"},
            "power": {"decay_model": "power"},
        },
    },
}


def main():
    parser = argparse.ArgumentParser(description="Ablation studies on LoCoMo conv0")
    parser.add_argument("--data", required=True, help="Path to locomo10.json")
    parser.add_argument("--conv", type=int, default=0)
    parser.add_argument("--ablation", default=None, help="Run specific ablation (H/I/J/K) or all")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--output", default="analysis/ablation_results.json")
    args = parser.parse_args()

    with open(args.data) as f:
        data = json.load(f)

    ablations_to_run = ABLATIONS
    if args.ablation:
        ablations_to_run = {args.ablation: ABLATIONS[args.ablation]}

    base_kwargs = {"llm_model": args.model, "deep_recall": True, "dual_perspective": True}
    all_results = {}

    for ablation_id, ablation_spec in ablations_to_run.items():
        print(f"\n{'='*60}")
        print(f"Ablation {ablation_id}: {ablation_spec['name']}")
        print(f"{'='*60}")

        ablation_results = {}
        for cond_name, cond_overrides in ablation_spec["conditions"].items():
            kwargs = {**base_kwargs}
            kwargs.update(cond_overrides)

            print(f"\n  Condition: {cond_name} ({cond_overrides})")
            t0 = time.time()

            result = run_ablation(data, args.conv, kwargs, model=args.model)
            elapsed = time.time() - t0

            print(f"    F1: {result['overall_f1']*100:.1f}%  ({elapsed:.0f}s)")
            for cat, f1 in result["by_category"].items():
                print(f"      {cat}: {f1*100:.1f}%")

            ablation_results[cond_name] = {
                "overall_f1": result["overall_f1"],
                "by_category": result["by_category"],
                "elapsed_seconds": elapsed,
            }

        # Compute delta
        conds = list(ablation_results.keys())
        if len(conds) == 2:
            delta = ablation_results[conds[1]]["overall_f1"] - ablation_results[conds[0]]["overall_f1"]
            print(f"\n  Delta ({conds[1]} - {conds[0]}): {delta*100:+.1f}%")
            ablation_results["delta"] = delta

        all_results[ablation_id] = {
            "name": ablation_spec["name"],
            "conditions": ablation_results,
        }

    # Save
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    output = {
        "ablations": all_results,
        "meta": {
            "conv_index": args.conv,
            "model": args.model,
            "timestamp": datetime.now().isoformat(),
        },
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved to {args.output}")

    # Print summary table
    print(f"\n{'='*60}")
    print("ABLATION SUMMARY")
    print(f"{'='*60}")
    print(f"| Feature | Off/Base | On/Alt | Delta |")
    print(f"|---------|----------|--------|-------|")
    for aid, adata in all_results.items():
        conds = adata["conditions"]
        cond_names = [k for k in conds if k != "delta"]
        if len(cond_names) == 2:
            f1_a = conds[cond_names[0]]["overall_f1"]
            f1_b = conds[cond_names[1]]["overall_f1"]
            delta = conds.get("delta", f1_b - f1_a)
            print(f"| {adata['name']} | {f1_a*100:.1f}% | {f1_b*100:.1f}% | {delta*100:+.1f}% |")


if __name__ == "__main__":
    main()
