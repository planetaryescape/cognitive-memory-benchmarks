"""Aggregate efficiency metrics from LoCoMo trace data and logs."""

import argparse
import json
import re
import statistics
from pathlib import Path

EXTRACT_RE = re.compile(r"Extracted (\d+) memories in ([\d.]+)s")
EMBED_RE = re.compile(r"Embedded (\d+) memories in ([\d.]+)s")


def percentile(data, pct):
    """Return the value at the given percentile (0-100)."""
    s = sorted(data)
    idx = int(len(s) * pct / 100)
    return s[min(idx, len(s) - 1)]


def parse_logs(results_dir, conv_idx):
    """Parse extraction and embedding timings from log file."""
    log_path = results_dir / f"conv{conv_idx}.log"
    extract_times = []
    embed_times = []
    try:
        text = log_path.read_text()
    except FileNotFoundError:
        return extract_times, embed_times

    for m in EXTRACT_RE.finditer(text):
        extract_times.append(float(m.group(2)) * 1000)  # convert to ms
    for m in EMBED_RE.finditer(text):
        embed_times.append(float(m.group(2)) * 1000)
    return extract_times, embed_times


def stats_block(values):
    if not values:
        return {"mean": None, "p50": None, "p95": None, "count": 0}
    return {
        "mean": round(statistics.mean(values), 2),
        "p50": round(statistics.median(values), 2),
        "p95": round(percentile(values, 95), 2),
        "count": len(values),
    }


def main():
    parser = argparse.ArgumentParser(description="Aggregate LoCoMo efficiency metrics")
    parser.add_argument(
        "--results-dir",
        default=str(Path(__file__).parent / "results" / "v6" / "parallel"),
        help="Directory containing conv*.json and conv*.log files",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "results" / "v6" / "efficiency_table.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    out_path = Path(args.output)

    all_vector_ms = []
    all_scoring_ms = []
    all_extract_ms = []
    all_embed_ms = []

    for i in range(10):
        # Trace data
        path = results_dir / f"conv{i}.json"
        with open(path) as f:
            data = json.load(f)

        for q in data["per_question"]:
            stages = q["trace"]["stages"]
            all_vector_ms.append(stages["vector_search"]["wall_ms"])
            all_scoring_ms.append(stages["scoring"]["wall_ms"])

        # Log data
        ext, emb = parse_logs(results_dir, i)
        all_extract_ms.extend(ext)
        all_embed_ms.extend(emb)

    results = {
        "extraction_ms": stats_block(all_extract_ms),
        "embedding_ms": stats_block(all_embed_ms),
        "vector_search_ms": stats_block(all_vector_ms),
        "scoring_ms": stats_block(all_scoring_ms),
    }

    # Print table
    print(f"{'Stage':<18} {'Count':>6} {'Mean (ms)':>10} {'P50 (ms)':>10} {'P95 (ms)':>10}")
    print("-" * 58)
    for label, key in [
        ("Extraction", "extraction_ms"),
        ("Embedding", "embedding_ms"),
        ("Vector Search", "vector_search_ms"),
        ("Scoring", "scoring_ms"),
    ]:
        s = results[key]
        if s["count"] == 0:
            print(f"{label:<18} {'N/A':>6}")
        else:
            print(f"{label:<18} {s['count']:>6} {s['mean']:>10.2f} {s['p50']:>10.2f} {s['p95']:>10.2f}")

    # Save
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
