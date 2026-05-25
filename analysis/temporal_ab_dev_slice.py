"""Phase 14 temporal reconstruction dev-slice A/B.

Ingest one temporal-rich LoCoMo-test conversation ONCE, then answer its
temporal (category 2) questions twice: ``temporal_query_mode`` off vs auto on
the same ingested store.

Why this is cheap and still valid:
- The SDK reads ``temporal_query_mode`` live at search time, so a single
  ingested store serves both arms (ingest once, retrieve twice).
- The entire temporal retrieval path is gated on
  ``mode == "auto" AND _is_temporal_query(query_text)``. For non-temporal
  queries ``temporal_query`` is False in both arms, so they are byte-identical.
  Non-temporal regression therefore reduces to counting ``_is_temporal_query``
  false positives over the non-temporal questions, which we compute statically
  without any answer generation.

Answers run on a local OpenAI-compatible chat server (LM Studio) via
``OPENAI_CHAT_BASE_URL``; extraction + embeddings use OpenAI. This is a dev
slice: the relative off-vs-auto deltas are the signal, not absolute F1. Escalate
to the full held-out split (full feature config) only if this shows real signal.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Repo root on path so `shared` / `locomo` imports resolve when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from locomo.locomo_eval import extract_qa, extract_sessions, generate_answer, PROMPT_MEM0
from shared.adapter import CognitiveMemoryAdapter
from shared.metrics import token_f1
from shared.openai_clients import make_chat_client

from cognitive_memory.engine import _is_temporal_query


def load_conversation(data_path: str, conv_index: int) -> dict:
    data = json.loads(Path(data_path).read_text())
    if not isinstance(data, list):
        data = [data]
    return data[conv_index]


def count_temporal_metadata(adapter: CognitiveMemoryAdapter) -> dict:
    """How many ingested memories carry usable temporal metadata."""
    hot = adapter.memory.adapter.hot
    total = len(hot)
    with_event = 0
    with_valid = 0
    for mem in hot.values():
        temporal = getattr(mem, "temporal", {}) or {}
        if isinstance(temporal, dict):
            if temporal.get("event_time", {}).get("start"):
                with_event += 1
            if temporal.get("valid_time", {}).get("status"):
                with_valid += 1
    return {"total": total, "with_event_time": with_event, "with_valid_time": with_valid}


def query_arm(adapter, mode, qa, query_ts, top_k, answer_client, answer_model, speaker_a, speaker_b):
    """Run one temporal question under a given temporal_query_mode."""
    adapter.memory.config.temporal_query_mode = mode
    qr = adapter.query(question=qa["question"], timestamp=query_ts, top_k=top_k)
    answer = generate_answer(
        question=qa["question"],
        query_result=qr,
        client=answer_client,
        model=answer_model,
        prompt_mode=PROMPT_MEM0,
        speaker_a=speaker_a,
        speaker_b=speaker_b,
    )
    f1 = token_f1(answer, qa["answer"])
    return {
        "answer": answer,
        "f1": f1["f1"],
        "retrieved": [m.content for m in qr.retrieved_memories],
        "temporal_evidence": [e.get("content", "") for e in (qr.temporal_evidence or [])],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        default="tuning/splits/peer_review_20260511/locomo_test.json",
    )
    parser.add_argument("--conv-index", type=int, default=1, help="conv-42 = most temporal-rich (40 cat-2 Qs)")
    parser.add_argument("--config", default="tuning/spaces/peer_review/temporal_reconstruction_auto.json")
    parser.add_argument("--answer-model", default="openai/gpt-oss-120b")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--limit-temporal", type=int, default=0, help="cap temporal Qs (0 = all)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tuning/runs/phase14-temporal-reconstruction/dev_slice_ab.json"),
    )
    args = parser.parse_args()

    if not os.getenv("OPENAI_CHAT_BASE_URL"):
        print("WARN: OPENAI_CHAT_BASE_URL unset; answers will hit real OpenAI, not LM Studio.", file=sys.stderr)

    conv = load_conversation(args.data, args.conv_index)
    sample_id = conv.get("sample_id", f"index-{args.conv_index}")
    conv_meta = conv.get("conversation", {})
    speaker_a = conv_meta.get("speaker_a", "Speaker A")
    speaker_b = conv_meta.get("speaker_b", "Speaker B")

    sessions = extract_sessions(conv)
    qa_items = extract_qa(conv)
    temporal_qa = [q for q in qa_items if str(q.get("category")) == "2"]
    nontemporal_qa = [q for q in qa_items if str(q.get("category")) in {"1", "3", "4"}]
    if args.limit_temporal:
        temporal_qa = temporal_qa[: args.limit_temporal]

    config_overrides = json.loads(Path(args.config).read_text())["config_overrides"]

    print(f"Conversation {sample_id}: {len(sessions)} sessions, "
          f"{len(temporal_qa)} temporal (cat-2) Qs, {len(nontemporal_qa)} non-temporal (cat 1/3/4) Qs")

    adapter = CognitiveMemoryAdapter(config_overrides=config_overrides, surface="sdk")
    adapter.reset()

    print("Ingesting (once)...", flush=True)
    t0 = time.time()
    for s in sessions:
        adapter.ingest_session(
            turns=s["turns"], session_id=s["session_id"], timestamp=s["timestamp"],
            speaker_a=s["speaker_a"], speaker_b=s["speaker_b"],
        )
        print(f"  {s['session_id']} ({len(s['turns'])} turns) done", flush=True)
    ingest_secs = time.time() - t0
    meta = count_temporal_metadata(adapter)
    print(f"Ingested in {ingest_secs:.0f}s. Memories={meta['total']} "
          f"with_event_time={meta['with_event_time']} with_valid_time={meta['with_valid_time']}", flush=True)

    # Non-temporal regression: off and auto share an identical code path unless
    # the query classifier false-positives on a non-temporal question. So only
    # the false positives can regress; we measure F1 on exactly those.
    nontemporal_fp_qa = [q for q in nontemporal_qa if _is_temporal_query(q["question"])]
    temporal_detected = sum(1 for q in temporal_qa if _is_temporal_query(q["question"]))
    print(f"Classifier: {temporal_detected}/{len(temporal_qa)} temporal Qs detected as temporal; "
          f"{len(nontemporal_fp_qa)}/{len(nontemporal_qa)} non-temporal false positives", flush=True)

    answer_client = make_chat_client()
    query_ts = sessions[-1]["timestamp"] if sessions else None

    def run_pair(qa, label, i, total):
        off = query_arm(adapter, "off", qa, query_ts, args.top_k, answer_client, args.answer_model, speaker_a, speaker_b)
        # When the classifier doesn't fire, auto == off exactly: skip the call.
        if _is_temporal_query(qa["question"]):
            auto = query_arm(adapter, "auto", qa, query_ts, args.top_k, answer_client, args.answer_model, speaker_a, speaker_b)
        else:
            auto = dict(off)
        row = {
            "question": qa["question"],
            "gold": qa["answer"],
            "evidence": qa.get("evidence", []),
            "classified_temporal": _is_temporal_query(qa["question"]),
            "off": off,
            "auto": auto,
            "delta_f1": round(auto["f1"] - off["f1"], 4),
        }
        print(f"  {label}[{i}/{total}] off={off['f1']:.2f} auto={auto['f1']:.2f} "
              f"d={auto['f1'] - off['f1']:+.2f} | {qa['question'][:55]}", flush=True)
        return row

    per_q = [run_pair(qa, "TMP", i, len(temporal_qa)) for i, qa in enumerate(temporal_qa, 1)]
    fp_q = [run_pair(qa, "FP ", i, len(nontemporal_fp_qa)) for i, qa in enumerate(nontemporal_fp_qa, 1)]

    def agg(rows):
        n = len(rows) or 1
        off = sum(r["off"]["f1"] for r in rows) / n
        auto = sum(r["auto"]["f1"] for r in rows) / n
        return {
            "n": len(rows),
            "f1_off": round(off, 4),
            "f1_auto": round(auto, 4),
            "f1_delta": round(auto - off, 4),
            "improved": sum(1 for r in rows if r["delta_f1"] > 1e-9),
            "regressed": sum(1 for r in rows if r["delta_f1"] < -1e-9),
            "unchanged": sum(1 for r in rows if abs(r["delta_f1"]) <= 1e-9),
        }

    temporal_agg = agg(per_q)
    fp_agg = agg(fp_q)
    # Projected regression over ALL non-temporal Qs: only the FPs can change, the
    # rest are identical (delta 0), so the mean shift dilutes by the FP fraction.
    fp_total_delta = sum(r["delta_f1"] for r in fp_q)
    projected_nontemporal_delta = round(fp_total_delta / (len(nontemporal_qa) or 1), 4)

    summary = {
        "conversation": sample_id,
        "data": args.data,
        "config": args.config,
        "answer_model": args.answer_model,
        "top_k": args.top_k,
        "ingest_secs": round(ingest_secs, 1),
        "memory_meta": meta,
        "classifier_temporal_recall": round(temporal_detected / (len(temporal_qa) or 1), 4),
        "nontemporal_false_positive_rate": round(len(nontemporal_fp_qa) / (len(nontemporal_qa) or 1), 4),
        "temporal": temporal_agg,
        "nontemporal_false_positives": fp_agg,
        "projected_nontemporal_f1_delta": projected_nontemporal_delta,
        "adoption_gate": {
            "temporal_f1_improved": temporal_agg["f1_delta"] > 0,
            "nontemporal_regression_within_1pp": projected_nontemporal_delta >= -0.01,
            "note": "Manual ordering/date/status audit still required; see per_question evidence.",
        },
        "per_question_temporal": per_q,
        "per_question_nontemporal_fp": fp_q,
        "caveats": [
            "Dev slice: single conversation, single-perspective ingestion, no LLM rerank.",
            "Relative off-vs-auto delta is the signal, not absolute F1.",
            "Escalate to full held-out split with the production feature config only if signal is real.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print("\n=== SUMMARY ===")
    print(f"temporal (n={temporal_agg['n']}): off={temporal_agg['f1_off']:.4f} "
          f"auto={temporal_agg['f1_auto']:.4f} delta={temporal_agg['f1_delta']:+.4f} "
          f"(up {temporal_agg['improved']} / down {temporal_agg['regressed']} / same {temporal_agg['unchanged']})")
    print(f"non-temporal FPs (n={fp_agg['n']}): off={fp_agg['f1_off']:.4f} "
          f"auto={fp_agg['f1_auto']:.4f} delta={fp_agg['f1_delta']:+.4f}")
    print(f"projected non-temporal F1 delta over all {len(nontemporal_qa)}: {projected_nontemporal_delta:+.4f}")
    print(f"adoption gate: temporal_up={summary['adoption_gate']['temporal_f1_improved']} "
          f"nontemporal_within_1pp={summary['adoption_gate']['nontemporal_regression_within_1pp']}")
    print(f"written: {args.output}")


if __name__ == "__main__":
    main()
