#!/usr/bin/env python3
"""
V6 Feature Utilization Probe.

Analyzes trace data to measure how often v6 features activated:
- Graph expansion (1-hop association traversal)
- Bridge path discovery
- Validity-based filtering (expired plan/transient_state)
- Reranking
- Memory semantic type distribution

Usage:
    python analysis/utilization_probe.py --results locomo/results/v6/primary.json
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def analyze_utilization(results_path: str) -> dict:
    with open(results_path) as f:
        data = json.load(f)

    per_question = data.get("per_question", [])

    # Counters
    total = len(per_question)
    with_trace = 0
    graph_expansion_fired = 0
    bridge_paths_found = 0
    validity_filtered = 0
    rerank_fired = 0

    graph_expansion_counts = []
    bridge_path_counts = []

    for r in per_question:
        trace = r.get("trace")
        if not trace:
            continue
        with_trace += 1

        stages = trace.get("stages", {})

        # Graph expansion
        assoc_stage = stages.get("associations") or stages.get("graph_expansion")
        if assoc_stage:
            candidate_count = assoc_stage.get("candidate_count", 0)
            meta = assoc_stage.get("metadata", {})
            associated = meta.get("associated_added", 0)
            if associated > 0:
                graph_expansion_fired += 1
                graph_expansion_counts.append(associated)

        # Bridge discovery
        bridge_stage = stages.get("bridge_discovery")
        if bridge_stage:
            meta = bridge_stage.get("metadata", {})
            paths = meta.get("paths_found", 0)
            if paths > 0:
                bridge_paths_found += 1
                bridge_path_counts.append(paths)

        # Validity filtering
        validity_stage = stages.get("validity_filtering")
        if validity_stage:
            meta = validity_stage.get("metadata", {})
            expired = meta.get("expired_filtered", 0)
            if expired > 0:
                validity_filtered += 1

        # Reranking
        rerank_stage = stages.get("rerank")
        if rerank_stage:
            wall = rerank_stage.get("wall_ms", 0)
            if wall > 0:
                rerank_fired += 1

    result = {
        "total_questions": total,
        "questions_with_trace": with_trace,
        "graph_expansion": {
            "activated_count": graph_expansion_fired,
            "activation_rate": graph_expansion_fired / with_trace if with_trace else 0,
            "mean_associated_added": sum(graph_expansion_counts) / len(graph_expansion_counts) if graph_expansion_counts else 0,
        },
        "bridge_discovery": {
            "activated_count": bridge_paths_found,
            "activation_rate": bridge_paths_found / with_trace if with_trace else 0,
            "mean_paths_found": sum(bridge_path_counts) / len(bridge_path_counts) if bridge_path_counts else 0,
        },
        "validity_filtering": {
            "activated_count": validity_filtered,
            "activation_rate": validity_filtered / with_trace if with_trace else 0,
        },
        "reranking": {
            "activated_count": rerank_fired,
            "activation_rate": rerank_fired / with_trace if with_trace else 0,
        },
    }

    return result


def print_report(result: dict):
    print(f"\n## V6 Feature Utilization Probe")
    print(f"\nTotal questions: {result['total_questions']}")
    print(f"Questions with trace: {result['questions_with_trace']}")

    print(f"\n### Feature Activation Rates")
    print(f"| Feature | Activated | Rate | Details |")
    print(f"|---------|-----------|------|---------|")

    ge = result["graph_expansion"]
    print(f"| Graph expansion (1-hop) | {ge['activated_count']} | {ge['activation_rate']*100:.1f}% | "
          f"avg {ge['mean_associated_added']:.1f} memories added |")

    bd = result["bridge_discovery"]
    print(f"| Bridge discovery | {bd['activated_count']} | {bd['activation_rate']*100:.1f}% | "
          f"avg {bd['mean_paths_found']:.1f} paths found |")

    vf = result["validity_filtering"]
    print(f"| Validity filtering | {vf['activated_count']} | {vf['activation_rate']*100:.1f}% | "
          f"expired memories filtered |")

    rr = result["reranking"]
    print(f"| Reranking | {rr['activated_count']} | {rr['activation_rate']*100:.1f}% | "
          f"LLM rerank stage |")


def main():
    parser = argparse.ArgumentParser(description="V6 feature utilization probe")
    parser.add_argument("--results", required=True, help="Path to results JSON")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = analyze_utilization(args.results)
    print_report(result)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
