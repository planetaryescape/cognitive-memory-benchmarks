#!/usr/bin/env python3
"""
Judge Reliability Data Prep.

Samples 50 QA pairs from LoCoMo results stratified by category
and correct/incorrect for human annotation.

Usage:
    python analysis/judge_reliability.py --results locomo/results/v6/primary.json
"""

import argparse
import json
import random
from pathlib import Path


def sample_for_annotation(results_path: str, n: int = 50, seed: int = 42) -> list[dict]:
    with open(results_path) as f:
        data = json.load(f)

    per_question = data.get("per_question", [])

    # Filter to categories 1-4 with judge data
    judged = [r for r in per_question if r.get("category", 5) <= 4 and "llm_correct" in r]

    if not judged:
        print("No judged results found. Run with --use-judge first.")
        return []

    random.seed(seed)

    # Stratify by category and correct/incorrect
    from collections import defaultdict
    buckets = defaultdict(list)
    for r in judged:
        key = (r["category"], r.get("llm_correct", False))
        buckets[key].append(r)

    # Proportional sampling
    total = len(judged)
    sampled = []

    for key, items in buckets.items():
        k = max(1, round(n * len(items) / total))
        k = min(k, len(items))
        sampled.extend(random.sample(items, k))

    # Trim or pad to exactly n
    if len(sampled) > n:
        sampled = random.sample(sampled, n)
    elif len(sampled) < n:
        remaining = [r for r in judged if r not in sampled]
        extra = min(n - len(sampled), len(remaining))
        sampled.extend(random.sample(remaining, extra))

    # Format for annotation
    annotation_items = []
    for i, r in enumerate(sampled):
        annotation_items.append({
            "id": i + 1,
            "question": r["question"],
            "ground_truth": r["ground_truth"],
            "prediction": r["prediction"],
            "category": r.get("category_name", ""),
            "llm_judge_verdict": "CORRECT" if r.get("llm_correct") else "WRONG",
            "f1_score": round(r.get("f1", 0), 3),
            "human_verdict": "",  # To be filled by annotator
            "human_notes": "",
        })

    return annotation_items


def main():
    parser = argparse.ArgumentParser(description="Judge reliability data prep")
    parser.add_argument("--results", required=True)
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--output", default="analysis/judge_reliability_sample.json")
    args = parser.parse_args()

    items = sample_for_annotation(args.results, n=args.n)

    if not items:
        return

    print(f"Sampled {len(items)} items for annotation")

    # Stats
    from collections import Counter
    cats = Counter(i["category"] for i in items)
    verdicts = Counter(i["llm_judge_verdict"] for i in items)

    print(f"\nDistribution:")
    print(f"  By category: {dict(cats)}")
    print(f"  By verdict: {dict(verdicts)}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(items, f, indent=2)
    print(f"\nSaved to {args.output}")
    print(f"\nNext: have 2-3 humans annotate the 'human_verdict' field (CORRECT/WRONG)")
    print(f"Then compute Cohen's kappa between LLM judge and each human.")


if __name__ == "__main__":
    main()
