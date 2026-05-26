"""Phase 14 full held-out-split temporal A/B with paired bootstrap CI.

Scales the dev-slice pattern across all LoCoMo held-out test conversations:
ingest each once, run ``temporal_query_mode`` off vs auto on its cat-2 (temporal)
questions and on classifier-FP non-temporal questions, aggregate paired deltas
with a 95% percentile bootstrap CI, decide adopt-or-not.

Same lean config as the dev slice (single-perspective ingestion, no LLM rerank).
The relative off-vs-auto delta is what determines adoption; absolute F1 is not
directly comparable to the full-feature Phase 12 numbers. Run after the SDK
classifier precision fix (commit `ee3015a`) is live in the editable install.

Writes incrementally after each conversation so a long run leaves a usable
artifact.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from locomo.locomo_eval import extract_qa, extract_sessions
from shared.adapter import CognitiveMemoryAdapter
from shared.openai_clients import make_chat_client

from cognitive_memory.engine import _is_temporal_query
from analysis.temporal_ab_dev_slice import count_temporal_metadata, query_arm, load_conversation


def paired_bootstrap_ci(deltas, n_resamples=2000, ci=0.95, seed=20260526):
    """Percentile-bootstrap CI on the mean of paired per-question deltas."""
    if not deltas:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0, "p_gt_zero": None}
    rng = random.Random(seed)
    n = len(deltas)
    means = []
    for _ in range(n_resamples):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo_idx = int((1 - ci) / 2 * n_resamples)
    hi_idx = int((1 - (1 - ci) / 2) * n_resamples) - 1
    obs = sum(deltas) / n
    # Fraction of bootstrap means above zero — proxy for one-sided p>0.
    p_gt_zero = sum(1 for m in means if m > 0) / n_resamples
    return {
        "mean": round(obs, 4),
        "ci_low": round(means[lo_idx], 4),
        "ci_high": round(means[hi_idx], 4),
        "n": n,
        "p_gt_zero": round(p_gt_zero, 4),
    }


def run_one_conversation(conv, args, answer_client, config_overrides):
    sample_id = conv.get("sample_id", "?")
    conv_meta = conv.get("conversation", {})
    speaker_a = conv_meta.get("speaker_a", "Speaker A")
    speaker_b = conv_meta.get("speaker_b", "Speaker B")
    sessions = extract_sessions(conv)
    qa_items = extract_qa(conv)
    temporal_qa = [q for q in qa_items if str(q.get("category")) == "2"]
    nontemporal_qa = [q for q in qa_items if str(q.get("category")) in {"1", "3", "4"}]

    print(f"\n========== {sample_id}: {len(sessions)} sessions, "
          f"{len(temporal_qa)} temporal, {len(nontemporal_qa)} non-temporal ==========", flush=True)

    adapter = CognitiveMemoryAdapter(config_overrides=config_overrides, surface="sdk")
    adapter.reset()

    t0 = time.time()
    for s in sessions:
        adapter.ingest_session(
            turns=s["turns"], session_id=s["session_id"], timestamp=s["timestamp"],
            speaker_a=s["speaker_a"], speaker_b=s["speaker_b"],
        )
    ingest_secs = time.time() - t0
    meta = count_temporal_metadata(adapter)
    print(f"  ingested in {ingest_secs:.0f}s | mem={meta['total']} "
          f"event_time={meta['with_event_time']}", flush=True)

    nontemporal_fp_qa = [q for q in nontemporal_qa if _is_temporal_query(q["question"])]
    temporal_detected = sum(1 for q in temporal_qa if _is_temporal_query(q["question"]))
    print(f"  classifier: {temporal_detected}/{len(temporal_qa)} detected; "
          f"{len(nontemporal_fp_qa)}/{len(nontemporal_qa)} non-temporal FPs", flush=True)

    query_ts = sessions[-1]["timestamp"] if sessions else None

    def run_pair(qa):
        off = query_arm(adapter, "off", qa, query_ts, args.top_k, answer_client,
                        args.answer_model, speaker_a, speaker_b)
        if _is_temporal_query(qa["question"]):
            auto = query_arm(adapter, "auto", qa, query_ts, args.top_k, answer_client,
                             args.answer_model, speaker_a, speaker_b)
        else:
            auto = dict(off)
        return {
            "question": qa["question"], "gold": qa["answer"],
            "evidence": qa.get("evidence", []),
            "classified_temporal": _is_temporal_query(qa["question"]),
            "off": off, "auto": auto,
            "delta_f1": round(auto["f1"] - off["f1"], 4),
        }

    t0 = time.time()
    temporal_rows = []
    for i, qa in enumerate(temporal_qa, 1):
        r = run_pair(qa)
        temporal_rows.append(r)
        if i % 10 == 0 or i == len(temporal_qa):
            print(f"  TMP {i}/{len(temporal_qa)} ({(time.time() - t0) / i:.1f}s/Q avg)", flush=True)
    fp_rows = []
    for i, qa in enumerate(nontemporal_fp_qa, 1):
        fp_rows.append(run_pair(qa))
        if i % 5 == 0 or i == len(nontemporal_fp_qa):
            print(f"  FP  {i}/{len(nontemporal_fp_qa)}", flush=True)

    return {
        "sample_id": sample_id,
        "n_sessions": len(sessions),
        "n_temporal": len(temporal_qa),
        "n_nontemporal": len(nontemporal_qa),
        "ingest_secs": round(ingest_secs, 1),
        "memory_meta": meta,
        "classifier": {
            "temporal_recall": round(temporal_detected / (len(temporal_qa) or 1), 4),
            "nontemporal_fp_rate": round(len(nontemporal_fp_qa) / (len(nontemporal_qa) or 1), 4),
            "nontemporal_fp_count": len(nontemporal_fp_qa),
        },
        "per_question_temporal": temporal_rows,
        "per_question_nontemporal_fp": fp_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        default="tuning/splits/peer_review_20260511/locomo_test.json",
    )
    parser.add_argument("--conv-indexes", nargs="*", type=int, default=None,
                        help="conv indexes (default: all)")
    parser.add_argument("--config", default="tuning/spaces/peer_review/temporal_reconstruction_auto.json")
    parser.add_argument("--answer-model", default="openai/gpt-oss-120b")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tuning/runs/phase14-temporal-reconstruction/full_split_ab.json"),
    )
    args = parser.parse_args()

    if not os.getenv("OPENAI_CHAT_BASE_URL"):
        print("WARN: OPENAI_CHAT_BASE_URL unset; answers will hit real OpenAI.", file=sys.stderr)

    data = json.loads(Path(args.data).read_text())
    indexes = args.conv_indexes if args.conv_indexes is not None else list(range(len(data)))
    config_overrides = json.loads(Path(args.config).read_text())["config_overrides"]
    answer_client = make_chat_client()

    per_conv = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    for idx in indexes:
        conv = data[idx]
        result = run_one_conversation(conv, args, answer_client, config_overrides)
        per_conv.append(result)
        # incremental flush so a long run is observable / resumable artifact-wise
        args.output.write_text(json.dumps({"per_conv": per_conv}, indent=2) + "\n")
        elapsed = time.time() - t_start
        print(f"  >> wrote partial after {result['sample_id']} (cumulative {elapsed/60:.1f} min)", flush=True)

    # Aggregate.
    all_temporal = [r for c in per_conv for r in c["per_question_temporal"]]
    all_fp = [r for c in per_conv for r in c["per_question_nontemporal_fp"]]
    n_temporal_total = len(all_temporal)
    n_nontemporal_total = sum(c["n_nontemporal"] for c in per_conv)

    def agg(rows):
        n = len(rows) or 1
        return {
            "n": len(rows),
            "f1_off": round(sum(r["off"]["f1"] for r in rows) / n, 4),
            "f1_auto": round(sum(r["auto"]["f1"] for r in rows) / n, 4),
            "f1_delta_mean": round(sum(r["delta_f1"] for r in rows) / n, 4),
            "improved": sum(1 for r in rows if r["delta_f1"] > 1e-9),
            "regressed": sum(1 for r in rows if r["delta_f1"] < -1e-9),
            "unchanged": sum(1 for r in rows if abs(r["delta_f1"]) <= 1e-9),
        }

    temporal_agg = agg(all_temporal)
    fp_agg = agg(all_fp)
    temporal_ci = paired_bootstrap_ci([r["delta_f1"] for r in all_temporal])
    fp_ci = paired_bootstrap_ci([r["delta_f1"] for r in all_fp])
    # FP regression projected to all non-temporal (non-FPs are identical between arms).
    fp_total_delta = sum(r["delta_f1"] for r in all_fp)
    projected_nontemporal_delta = round(fp_total_delta / (n_nontemporal_total or 1), 4)

    summary = {
        "data": args.data,
        "config": args.config,
        "answer_model": args.answer_model,
        "top_k": args.top_k,
        "conv_indexes": indexes,
        "n_conversations": len(per_conv),
        "n_temporal_total": n_temporal_total,
        "n_nontemporal_total": n_nontemporal_total,
        "temporal": {**temporal_agg, "ci_95": temporal_ci},
        "nontemporal_false_positives": {**fp_agg, "ci_95": fp_ci},
        "projected_nontemporal_f1_delta": projected_nontemporal_delta,
        "adoption_gate": {
            "temporal_ci_excludes_zero": temporal_ci["ci_low"] > 0,
            "temporal_mean_positive": temporal_agg["f1_delta_mean"] > 0,
            "nontemporal_regression_within_1pp": projected_nontemporal_delta >= -0.01,
            "verdict": (
                "adopt" if (temporal_ci["ci_low"] > 0 and projected_nontemporal_delta >= -0.01)
                else "do_not_adopt"
            ),
        },
        "per_conv": per_conv,
        "caveats": [
            "Lean config (single-perspective, no LLM rerank). Relative delta is the signal.",
            "LoCoMo evidence-labeled cat-2 only; the residual classifier FPs are mostly LoCoMo-mislabeled temporal Qs.",
        ],
    }

    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print("\n=== FULL-SPLIT SUMMARY ===")
    print(f"temporal n={temporal_agg['n']}: off={temporal_agg['f1_off']} auto={temporal_agg['f1_auto']} "
          f"delta={temporal_agg['f1_delta_mean']:+} CI95=[{temporal_ci['ci_low']:+}, {temporal_ci['ci_high']:+}] "
          f"P(d>0)={temporal_ci['p_gt_zero']}")
    print(f"non-temporal FPs n={fp_agg['n']}: delta={fp_agg['f1_delta_mean']:+} "
          f"CI95=[{fp_ci['ci_low']:+}, {fp_ci['ci_high']:+}]")
    print(f"projected non-temporal delta over {n_nontemporal_total}: {projected_nontemporal_delta:+}")
    print(f"adoption verdict: {summary['adoption_gate']['verdict']}")
    print(f"written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
