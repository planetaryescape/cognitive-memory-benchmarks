#!/usr/bin/env python3
"""
Decay Form Comparison: Exponential vs Power-law.

Runs LoCoMo conv0 with both decay models, compares F1 and retention curves.

Usage:
    python simulations/decay_comparison.py --data locomo/data/locomo10.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.metrics import token_f1, token_f1_mem0, LOCOMO_CATEGORIES


def run_with_decay_model(data, conv_index, decay_model, model="gpt-4o-mini", top_k=20):
    """Run LoCoMo eval on one conversation with specified decay model."""
    from cognitive_memory import SyncCognitiveMemory, CognitiveMemoryConfig

    config = CognitiveMemoryConfig(
        extraction_model=model,
        embedding_model="text-embedding-3-small",
        run_maintenance_during_ingestion=False,
        core_access_threshold=3,
        core_stability_threshold=0.50,
        core_session_threshold=2,
        decay_model=decay_model,
    )
    if decay_model == "power":
        config.power_decay_gamma = 1.4427

    mem = SyncCognitiveMemory(config=config, embedder="openai")

    conv = data[conv_index]
    conv_data = conv.get("conversation", {})
    speaker_a = conv_data.get("speaker_a", "Speaker A")
    speaker_b = conv_data.get("speaker_b", "Speaker B")

    # Ingest sessions
    session_keys = sorted(
        [k for k in conv_data if k.startswith("session_") and not k.endswith(("_date_time", "_observation", "_summary"))],
        key=lambda x: int(x.split("_")[1])
    )

    from shared.adapter import _parse_timestamp

    for session_key in session_keys:
        timestamp_key = f"{session_key}_date_time"
        timestamp = conv_data.get(timestamp_key, "")
        ts = _parse_timestamp(timestamp)

        turns = conv_data.get(session_key, [])
        lines = []
        for t in turns:
            role = "User" if t["speaker"] == speaker_a else "Assistant"
            lines.append(f"{role} ({t['speaker']}): {t['text']}")
        date_header = f"[This conversation took place on {timestamp}]\n" if timestamp else ""
        conversation_text = date_header + "\n".join(lines)

        mem.extract_and_store(
            conversation_text=conversation_text,
            session_id=session_key,
            timestamp=ts,
        )
        mem.tick(ts)

    # Query and score
    qa_items = conv.get("qa", [])
    results = []
    retention_data = []

    # Collect retention values for all memories at query time
    last_session_ts = None
    for sk in session_keys:
        ts_key = f"{sk}_date_time"
        ts_str = conv_data.get(ts_key, "")
        if ts_str:
            last_session_ts = _parse_timestamp(ts_str)

    query_ts = last_session_ts or datetime.now()

    # Sample retention values across all memories
    all_mems = list(mem.adapter.hot.values())
    for m in all_mems:
        if not m.is_stub:
            retention = mem.engine.compute_retention(m, query_ts)
            age_days = (query_ts - m.created_at).total_seconds() / 86400 if m.created_at else 0
            retention_data.append({
                "age_days": age_days,
                "retention": retention,
                "stability": m.stability,
                "category": m.category.value,
            })

    from openai import OpenAI
    client = OpenAI()

    for qi, qa in enumerate(qa_items):
        category = int(qa.get("category", 0))

        ground_truth = qa.get("answer", qa.get("adversarial_answer", ""))
        if not ground_truth or category == 5:
            continue

        search_response = mem.search(
            query=qa["question"],
            top_k=top_k,
            timestamp=query_ts,
            session_id="query",
        )
        search_results = search_response.results

        # Generate answer
        if not search_results:
            memories_text = "(No relevant memories found)"
        else:
            memories_text = "\n".join(f"{i+1}. {r.memory.content}" for i, r in enumerate(search_results))

        prompt = f"""Below are memories from previous conversations.

{memories_text}

Based on the above memories, write an answer in the form of a short phrase for the following question. Answer with exact words from the memories whenever possible. Say "unknown" only if the memories contain absolutely nothing relevant.

Question: {qa['question']} Short answer:"""

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=32,
        )
        answer = resp.choices[0].message.content.strip()

        f1_result = token_f1(answer, str(ground_truth))

        results.append({
            "question_index": qi,
            "category": category,
            "f1": f1_result["f1"],
            "prediction": answer,
            "ground_truth": str(ground_truth),
        })

    # Aggregate
    valid = [r for r in results if r.get("category", 5) <= 4]
    overall_f1 = sum(r["f1"] for r in valid) / len(valid) if valid else 0

    stats = mem.get_stats()

    return {
        "decay_model": decay_model,
        "overall_f1": overall_f1,
        "per_question": results,
        "retention_curve": retention_data,
        "stats": stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Decay form comparison")
    parser.add_argument("--data", required=True, help="Path to locomo10.json")
    parser.add_argument("--conv", type=int, default=0, help="Conversation index")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--output", default="simulations/decay_comparison.json")
    args = parser.parse_args()

    with open(args.data) as f:
        data = json.load(f)

    print(f"Decay Comparison: conv{args.conv}, model={args.model}")

    # Run exponential
    print("\n--- Exponential decay ---")
    t0 = time.time()
    exp_results = run_with_decay_model(data, args.conv, "exponential", args.model)
    exp_time = time.time() - t0
    print(f"  F1: {exp_results['overall_f1']*100:.1f}%  ({exp_time:.0f}s)")

    # Run power-law
    print("\n--- Power-law decay ---")
    t0 = time.time()
    pow_results = run_with_decay_model(data, args.conv, "power", args.model)
    pow_time = time.time() - t0
    print(f"  F1: {pow_results['overall_f1']*100:.1f}%  ({pow_time:.0f}s)")

    # Compare
    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")
    print(f"Exponential F1: {exp_results['overall_f1']*100:.1f}%")
    print(f"Power-law F1:   {pow_results['overall_f1']*100:.1f}%")
    print(f"Delta:          {(pow_results['overall_f1'] - exp_results['overall_f1'])*100:+.1f}%")

    # Retention curve stats
    exp_retentions = [r["retention"] for r in exp_results["retention_curve"]]
    pow_retentions = [r["retention"] for r in pow_results["retention_curve"]]
    print(f"\nRetention stats:")
    print(f"  Exp: mean={sum(exp_retentions)/len(exp_retentions):.3f}, min={min(exp_retentions):.3f}")
    print(f"  Pow: mean={sum(pow_retentions)/len(pow_retentions):.3f}, min={min(pow_retentions):.3f}")

    # Save
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    output = {
        "exponential": exp_results,
        "power_law": pow_results,
        "comparison": {
            "exp_f1": exp_results["overall_f1"],
            "pow_f1": pow_results["overall_f1"],
            "delta": pow_results["overall_f1"] - exp_results["overall_f1"],
        },
        "meta": {
            "conv_index": args.conv,
            "model": args.model,
            "timestamp": datetime.now().isoformat(),
        },
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
