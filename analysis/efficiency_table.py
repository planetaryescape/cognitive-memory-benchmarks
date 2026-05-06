#!/usr/bin/env python3
"""
Efficiency Table: aggregate per-stage timing and token usage from trace data.

Reads the primary LoCoMo results (with trace data embedded in adapter)
and produces a markdown efficiency table.

Usage:
    python analysis/efficiency_table.py --results locomo/results/v6/primary.json
"""

import argparse
import json
import statistics
from pathlib import Path


def analyze_traces(results_path: str) -> dict:
    """Analyze trace data from results file."""
    with open(results_path) as f:
        data = json.load(f)

    per_question = data.get("per_question", [])

    # Collect per-stage metrics
    stage_wall_ms = {}
    stage_prompt_tokens = {}
    stage_completion_tokens = {}
    total_wall_ms = []

    for r in per_question:
        trace = r.get("trace")
        if not trace:
            continue

        if "total_wall_ms" in trace:
            total_wall_ms.append(trace["total_wall_ms"])

        stages = trace.get("stages", {})
        for stage_name, stage_data in stages.items():
            if stage_name not in stage_wall_ms:
                stage_wall_ms[stage_name] = []
                stage_prompt_tokens[stage_name] = []
                stage_completion_tokens[stage_name] = []

            stage_wall_ms[stage_name].append(stage_data.get("wall_ms", 0))
            meta = stage_data.get("metadata", {})
            stage_prompt_tokens[stage_name].append(meta.get("prompt_tokens", 0))
            stage_completion_tokens[stage_name].append(meta.get("completion_tokens", 0))

    if not stage_wall_ms:
        print("No trace data found in results. Make sure trace=True was enabled.")
        return {}

    # Build summary table
    table = {}
    for stage in stage_wall_ms:
        wall = stage_wall_ms[stage]
        pt = stage_prompt_tokens[stage]
        ct = stage_completion_tokens[stage]

        table[stage] = {
            "count": len(wall),
            "wall_ms_mean": statistics.mean(wall),
            "wall_ms_p50": statistics.median(wall),
            "wall_ms_p95": sorted(wall)[int(len(wall) * 0.95)] if len(wall) > 1 else wall[0],
            "prompt_tokens_mean": statistics.mean(pt),
            "completion_tokens_mean": statistics.mean(ct),
            "total_tokens_mean": statistics.mean(pt) + statistics.mean(ct),
        }

    summary = {
        "stages": table,
        "total_queries": len(per_question),
        "queries_with_trace": len(total_wall_ms),
    }

    if total_wall_ms:
        summary["total_wall_ms_mean"] = statistics.mean(total_wall_ms)
        summary["total_wall_ms_p50"] = statistics.median(total_wall_ms)
        summary["total_wall_ms_p95"] = sorted(total_wall_ms)[int(len(total_wall_ms) * 0.95)]

    return summary


def print_markdown_table(summary: dict):
    """Print efficiency table in markdown format."""
    stages = summary.get("stages", {})
    if not stages:
        print("No data to display.")
        return

    print("\n## Efficiency Table (Per-Query Averages)")
    print()
    print("| Stage | Wall (ms) | P50 (ms) | P95 (ms) | Prompt Tokens | Completion Tokens | Total Tokens |")
    print("|-------|-----------|----------|----------|---------------|-------------------|--------------|")

    for stage, data in sorted(stages.items()):
        print(f"| {stage} | {data['wall_ms_mean']:.1f} | {data['wall_ms_p50']:.1f} | "
              f"{data['wall_ms_p95']:.1f} | {data['prompt_tokens_mean']:.0f} | "
              f"{data['completion_tokens_mean']:.0f} | {data['total_tokens_mean']:.0f} |")

    if "total_wall_ms_mean" in summary:
        print(f"| **Total** | **{summary['total_wall_ms_mean']:.1f}** | "
              f"**{summary['total_wall_ms_p50']:.1f}** | "
              f"**{summary['total_wall_ms_p95']:.1f}** | — | — | — |")

    print(f"\n_Based on {summary['queries_with_trace']} queries with trace data "
          f"out of {summary['total_queries']} total._")


def main():
    parser = argparse.ArgumentParser(description="Efficiency table from trace data")
    parser.add_argument("--results", required=True, help="Path to results JSON with trace data")
    parser.add_argument("--output", default=None, help="Optional output JSON path")
    args = parser.parse_args()

    summary = analyze_traces(args.results)
    print_markdown_table(summary)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
