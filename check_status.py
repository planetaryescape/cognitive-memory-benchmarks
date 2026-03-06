#!/usr/bin/env python3
"""Quick status check for all running benchmark jobs."""

import json
import os
import subprocess
from pathlib import Path

BASE = Path(__file__).parent

def check_locomo():
    print("=" * 60)
    print("LOCOMO RUNS")
    print("=" * 60)

    runs = {
        "Run H (legacy)": "locomo/results/run_h_hybrid/run_h_full.json",
        "Clean Run A (official+DR+RR)": "locomo/results/clean_run_a/results.json",
        "Clean Run B (FadeMem+DR+RR)": "locomo/results/clean_run_b/results.json",
        "Clean Run E (tuned+DR+RR)": "locomo/results/clean_run_e/results.json",
        "Clean Run F (mem0+DR+RR)": "locomo/results/clean_run_f/results.json",
        "Clean F-ablation (mem0, no DR/RR)": "locomo/results/clean_run_f_ablation/results.json",
    }

    for name, path in runs.items():
        full_path = BASE / path
        if full_path.exists():
            with open(full_path) as f:
                data = json.load(f)
            questions = len(data.get("per_question", []))
            agg = data.get("aggregate", {})
            overall = agg.get("overall", {})
            f1 = overall.get("mean_f1", 0)
            print(f"  {name}: DONE - {questions} questions, F1={f1*100:.1f}%")
        else:
            print(f"  {name}: IN PROGRESS (no results file yet)")


def check_longmemeval():
    print("\n" + "=" * 60)
    print("LONGMEMEVAL")
    print("=" * 60)

    results_dir = BASE / "longmemeval" / "results"
    if not results_dir.exists():
        print("  No results directory yet")
        return

    for f in sorted(results_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        questions = len(data.get("per_question", []))
        agg = data.get("aggregate", {})
        task_avg = agg.get("task_averaged_accuracy", 0)
        overall = agg.get("overall_accuracy", 0)
        print(f"  {f.name}: {questions} questions, task_avg={task_avg*100:.1f}%, overall={overall*100:.1f}%")
        by_type = agg.get("by_type", {})
        for qt, td in by_type.items():
            print(f"    {qt}: {td['accuracy']*100:.1f}% (n={td['count']})")


def check_processes():
    print("\n" + "=" * 60)
    print("RUNNING PROCESSES")
    print("=" * 60)

    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    count = 0
    for line in result.stdout.split("\n"):
        if "locomo_eval" in line or "longmemeval" in line or "memorybench" in line:
            if "grep" in line or "zsh" in line:
                continue
            parts = line.split()
            if len(parts) < 11:
                continue
            pid = parts[1]
            cpu = parts[2]
            mem_pct = parts[3]
            cmd_parts = " ".join(parts[10:])
            # Extract output path for identification
            if "--output" in cmd_parts:
                out_path = cmd_parts.split("--output")[1].strip().split()[0]
                print(f"  PID {pid} (CPU={cpu}%): {out_path}")
            else:
                print(f"  PID {pid} (CPU={cpu}%): {cmd_parts[-80:]}")
            count += 1
    if count == 0:
        print("  No benchmark processes running")


if __name__ == "__main__":
    check_locomo()
    check_longmemeval()
    check_processes()
