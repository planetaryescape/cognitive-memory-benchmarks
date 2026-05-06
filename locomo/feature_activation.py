"""Analyze LoCoMo trace data to measure feature activation."""

import argparse
import json
import statistics
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Analyze LoCoMo feature activation")
    parser.add_argument(
        "--results-dir",
        default=str(Path(__file__).parent / "results" / "v6" / "parallel"),
        help="Directory containing conv*.json files",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "results" / "v6" / "feature_activation.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    out_path = Path(args.output)

    all_vector_ms = []
    all_scoring_ms = []
    all_candidate_counts = []
    all_num_retrieved = []
    conv_summaries = []

    for i in range(10):
        path = results_dir / f"conv{i}.json"
        with open(path) as f:
            data = json.load(f)

        questions = data["per_question"]
        n_questions = len(questions)

        conv_vector_ms = []
        conv_scoring_ms = []
        conv_candidates = []
        conv_retrieved = []

        for q in questions:
            trace = q["trace"]
            vs = trace["stages"]["vector_search"]
            sc = trace["stages"]["scoring"]

            conv_vector_ms.append(vs["wall_ms"])
            conv_scoring_ms.append(sc["wall_ms"])
            conv_candidates.append(vs["candidate_count"])
            conv_retrieved.append(q["num_retrieved"])

        all_vector_ms.extend(conv_vector_ms)
        all_scoring_ms.extend(conv_scoring_ms)
        all_candidate_counts.extend(conv_candidates)
        all_num_retrieved.extend(conv_retrieved)

        summary = {
            "conv": i,
            "n_questions": n_questions,
            "total_memories_retrieved": sum(conv_retrieved),
            "mean_candidates": round(statistics.mean(conv_candidates), 1),
            "mean_num_retrieved": round(statistics.mean(conv_retrieved), 1),
            "vector_search_ms": {
                "mean": round(statistics.mean(conv_vector_ms), 2),
                "p50": round(statistics.median(conv_vector_ms), 2),
                "p95": round(sorted(conv_vector_ms)[int(len(conv_vector_ms) * 0.95)], 2),
            },
            "scoring_ms": {
                "mean": round(statistics.mean(conv_scoring_ms), 2),
                "p50": round(statistics.median(conv_scoring_ms), 2),
                "p95": round(sorted(conv_scoring_ms)[int(len(conv_scoring_ms) * 0.95)], 2),
            },
        }
        conv_summaries.append(summary)

    # Global stats
    global_stats = {
        "total_questions": len(all_vector_ms),
        "candidate_count": {
            "mean": round(statistics.mean(all_candidate_counts), 1),
            "min": min(all_candidate_counts),
            "max": max(all_candidate_counts),
        },
        "num_retrieved": {
            "mean": round(statistics.mean(all_num_retrieved), 1),
            "min": min(all_num_retrieved),
            "max": max(all_num_retrieved),
        },
        "vector_search_ms": {
            "mean": round(statistics.mean(all_vector_ms), 2),
            "p50": round(statistics.median(all_vector_ms), 2),
            "p95": round(sorted(all_vector_ms)[int(len(all_vector_ms) * 0.95)], 2),
        },
        "scoring_ms": {
            "mean": round(statistics.mean(all_scoring_ms), 2),
            "p50": round(statistics.median(all_scoring_ms), 2),
            "p95": round(sorted(all_scoring_ms)[int(len(all_scoring_ms) * 0.95)], 2),
        },
    }

    # Print table
    print(f"{'Conv':>4}  {'Qs':>4}  {'Cands':>6}  {'Retr':>5}  {'VS mean':>8}  {'VS p50':>8}  {'VS p95':>8}  {'SC mean':>8}  {'SC p50':>8}  {'SC p95':>8}")
    print("-" * 90)
    for s in conv_summaries:
        vs = s["vector_search_ms"]
        sc = s["scoring_ms"]
        print(
            f"{s['conv']:>4}  {s['n_questions']:>4}  {s['mean_candidates']:>6}  {s['mean_num_retrieved']:>5}"
            f"  {vs['mean']:>8.2f}  {vs['p50']:>8.2f}  {vs['p95']:>8.2f}"
            f"  {sc['mean']:>8.2f}  {sc['p50']:>8.2f}  {sc['p95']:>8.2f}"
        )
    print("-" * 90)
    vs = global_stats["vector_search_ms"]
    sc = global_stats["scoring_ms"]
    print(
        f"{'ALL':>4}  {global_stats['total_questions']:>4}  {global_stats['candidate_count']['mean']:>6}"
        f"  {global_stats['num_retrieved']['mean']:>5}"
        f"  {vs['mean']:>8.2f}  {vs['p50']:>8.2f}  {vs['p95']:>8.2f}"
        f"  {sc['mean']:>8.2f}  {sc['p50']:>8.2f}  {sc['p95']:>8.2f}"
    )

    # Save
    output = {"global": global_stats, "per_conversation": conv_summaries}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
