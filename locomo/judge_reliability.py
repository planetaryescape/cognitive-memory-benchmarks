#!/usr/bin/env python3
"""
Run M — Judge Reliability (inter-judge agreement).

Samples 50 QA pairs stratified by category × correctness from Run A,
re-judges with an alternative prompt, computes Cohen's kappa between
the original and alternative judge verdicts.

Usage:
    python locomo/judge_reliability.py \
        --results-dir locomo/results/v6/parallel \
        --output locomo/results/v6/judge_reliability.json
"""

import argparse
import json
import random
import time
from collections import defaultdict
from pathlib import Path

from openai import OpenAI


# Alternative judge prompt — rephrased to test sensitivity
ALT_JUDGE_PROMPT = """Given the following question and two answers, determine if the system answer
is semantically equivalent to the reference answer.

Question: {question}
Reference answer: {ground_truth}
System answer: {prediction}

Two answers are equivalent if they convey the same core fact(s), even if
the wording, level of detail, or phrasing differs. Minor omissions of
non-essential details should still count as equivalent.

Reply with a single word: EQUIVALENT or DIFFERENT"""


def load_judged_results(results_dir: str) -> list[dict]:
    """Load and merge all per-question results that have judge verdicts."""
    results_dir = Path(results_dir)
    all_q = []

    if results_dir.is_dir():
        for p in sorted(results_dir.glob("conv*.json")):
            with open(p) as f:
                data = json.load(f)
            all_q.extend(data.get("per_question", []))
    else:
        with open(results_dir) as f:
            data = json.load(f)
        all_q = data.get("per_question", [])

    return [q for q in all_q if q.get("category", 5) <= 4 and "llm_correct" in q]


def stratified_sample(judged: list[dict], n: int = 50, seed: int = 42) -> list[dict]:
    """Proportional stratified sample across category × correctness buckets."""
    random.seed(seed)

    buckets = defaultdict(list)
    for r in judged:
        key = (r["category"], r.get("llm_correct", False))
        buckets[key].append(r)

    total = len(judged)
    sampled = []

    for key, items in sorted(buckets.items()):
        k = max(1, round(n * len(items) / total))
        k = min(k, len(items))
        sampled.extend(random.sample(items, k))

    if len(sampled) > n:
        random.shuffle(sampled)
        sampled = sampled[:n]
    elif len(sampled) < n:
        sampled_set = {id(r) for r in sampled}
        remaining = [r for r in judged if id(r) not in sampled_set]
        extra = min(n - len(sampled), len(remaining))
        sampled.extend(random.sample(remaining, extra))

    return sampled


def alt_judge(question: str, prediction: str, ground_truth: str,
              client: OpenAI, model: str = "gpt-4o-mini") -> dict:
    """Run alternative judge prompt."""
    prompt = ALT_JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        prediction=prediction,
    )

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10,
            )
            raw = resp.choices[0].message.content.strip().upper()
            correct = "EQUIVALENT" in raw
            return {"correct": correct, "raw_response": raw}
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise


def cohens_kappa(y1: list[bool], y2: list[bool]) -> float:
    """Compute Cohen's kappa between two binary raters."""
    n = len(y1)
    if n == 0:
        return 0.0

    # Observed agreement
    agree = sum(1 for a, b in zip(y1, y2) if a == b)
    p_o = agree / n

    # Expected agreement by chance
    p1_pos = sum(y1) / n
    p2_pos = sum(y2) / n
    p_e = p1_pos * p2_pos + (1 - p1_pos) * (1 - p2_pos)

    if p_e == 1.0:
        return 1.0

    return (p_o - p_e) / (1 - p_e)


def main():
    parser = argparse.ArgumentParser(description="Run M — Judge Reliability")
    parser.add_argument("--results-dir", required=True,
                        help="Path to parallel results dir or single results JSON")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--output", default="locomo/results/v6/judge_reliability.json")
    args = parser.parse_args()

    client = OpenAI()

    # Load and sample
    judged = load_judged_results(args.results_dir)
    print(f"Loaded {len(judged)} judged questions")

    sampled = stratified_sample(judged, n=args.n)
    print(f"Sampled {len(sampled)} items")

    # Distribution
    from collections import Counter
    cats = Counter((s["category"], s.get("llm_correct", False)) for s in sampled)
    for k in sorted(cats):
        print(f"  cat={k[0]} correct={k[1]}: {cats[k]}")

    # Re-judge with alternative prompt
    results = []
    t0 = time.time()

    for i, item in enumerate(sampled):
        alt = alt_judge(
            question=item["question"],
            prediction=item["prediction"],
            ground_truth=item["ground_truth"],
            client=client,
            model=args.model,
        )

        results.append({
            "question": item["question"],
            "ground_truth": item["ground_truth"],
            "prediction": item["prediction"],
            "category": item.get("category", 0),
            "category_name": item.get("category_name", ""),
            "original_verdict": item.get("llm_correct", False),
            "alt_verdict": alt["correct"],
            "alt_raw": alt["raw_response"],
            "agree": item.get("llm_correct", False) == alt["correct"],
        })

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(sampled)} done...")

    elapsed = time.time() - t0

    # Compute metrics
    original = [r["original_verdict"] for r in results]
    alternative = [r["alt_verdict"] for r in results]

    agreement = sum(r["agree"] for r in results) / len(results)
    kappa = cohens_kappa(original, alternative)

    # Per-category
    cat_metrics = {}
    cat_groups = defaultdict(list)
    for r in results:
        cat_groups[r["category_name"]].append(r)

    for cat_name, cat_results in cat_groups.items():
        o = [r["original_verdict"] for r in cat_results]
        a = [r["alt_verdict"] for r in cat_results]
        cat_metrics[cat_name] = {
            "n": len(cat_results),
            "agreement": sum(r["agree"] for r in cat_results) / len(cat_results),
            "kappa": cohens_kappa(o, a),
        }

    # Disagreement analysis
    disagreements = [r for r in results if not r["agree"]]

    output = {
        "summary": {
            "n": len(results),
            "raw_agreement": round(agreement, 4),
            "cohens_kappa": round(kappa, 4),
            "original_positive_rate": round(sum(original) / len(original), 4),
            "alt_positive_rate": round(sum(alternative) / len(alternative), 4),
        },
        "by_category": cat_metrics,
        "disagreements": disagreements,
        "all_results": results,
        "meta": {
            "model": args.model,
            "elapsed_seconds": round(elapsed, 1),
            "alt_prompt": ALT_JUDGE_PROMPT.strip(),
        },
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'='*50}")
    print("JUDGE RELIABILITY RESULTS")
    print(f"{'='*50}")
    print(f"  N = {len(results)}")
    print(f"  Raw agreement: {agreement*100:.1f}%")
    print(f"  Cohen's kappa: {kappa:.3f}")
    print(f"  Original positive rate: {sum(original)/len(original)*100:.1f}%")
    print(f"  Alt positive rate: {sum(alternative)/len(alternative)*100:.1f}%")
    print(f"  Disagreements: {len(disagreements)}")
    print(f"\nPer-category:")
    for cat_name, m in sorted(cat_metrics.items()):
        print(f"  {cat_name:15s}: agree={m['agreement']*100:.0f}% kappa={m['kappa']:.3f} (n={m['n']})")
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
