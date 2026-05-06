#!/usr/bin/env python3
"""
Evidence Recall@k diagnostic for LoCoMo.

Computes what fraction of ground-truth evidence dialog turns appear
in the top-k retrieved memories, at k=5, 10, 20, 60.

Usage:
    python locomo/evidence_recall.py \
        --data locomo/data/locomo10.json \
        --results locomo/results/v6/primary.json
"""

import argparse
import json
import sys
from pathlib import Path


def load_evidence_map(data_path: str) -> dict:
    """Build a map from (conv_index, question_index) -> list of evidence texts."""
    with open(data_path) as f:
        data = json.load(f)

    evidence_map = {}
    for conv_idx, conv in enumerate(data):
        conv_data = conv.get("conversation", {})
        # Build dialog ID -> text map
        dia_text = {}
        session_keys = sorted(
            [k for k in conv_data if k.startswith("session_") and not k.endswith(("_date_time", "_observation", "_summary"))],
            key=lambda x: int(x.split("_")[1])
        )
        for session_key in session_keys:
            for turn in conv_data.get(session_key, []):
                dia_id = turn.get("dia_id", "")
                if dia_id:
                    dia_text[dia_id] = turn.get("text", "")

        qa_items = conv.get("qa", [])
        for qi, qa in enumerate(qa_items):
            evidence_ids = qa.get("evidence", [])
            if not evidence_ids:
                continue
            # Resolve evidence IDs to text
            texts = []
            for eid in evidence_ids:
                # Evidence format: "D1:3" means dialog session 1, turn 3
                # Or sometimes just the dia_id
                eid = str(eid).strip()
                if eid in dia_text:
                    texts.append(dia_text[eid])
                else:
                    # Try partial match
                    for did, dtxt in dia_text.items():
                        if eid in did or did in eid:
                            texts.append(dtxt)
                            break
            if texts:
                evidence_map[(conv_idx, qi)] = texts

    return evidence_map


def compute_recall_at_k(results_path: str, evidence_map: dict, k_values: list[int]) -> dict:
    """Compute evidence recall@k from results."""
    with open(results_path) as f:
        data = json.load(f)

    per_question = data.get("per_question", [])

    recall_at_k = {k: [] for k in k_values}
    recall_by_cat = {k: {} for k in k_values}  # k -> cat -> list of recalls

    matched = 0
    total = 0

    for r in per_question:
        conv_idx = r.get("conv_index", 0)
        qi = r.get("question_index", 0)
        cat = r.get("category", 0)
        key = (conv_idx, qi)

        if key not in evidence_map:
            continue
        if cat == 5:
            continue

        evidence_texts = evidence_map[key]
        total += 1

        # Check if we have retrieved memories stored
        # The results file stores prediction/answer but not retrieved memories
        # We need to check if the results contain retrieved content
        retrieved = r.get("retrieved_contents", [])
        if not retrieved:
            # If no retrieved contents stored, skip
            continue

        matched += 1

        for k in k_values:
            top_k_texts = retrieved[:k]
            found = 0
            for ev_text in evidence_texts:
                # Token overlap: evidence is raw dialog, retrieved are extracted facts
                # Check if key content words from evidence appear in any retrieved memory
                ev_tokens = set(ev_text.lower().split())
                stopwords = {"i", "a", "the", "to", "and", "is", "was", "it", "in",
                             "of", "for", "on", "that", "my", "me", "we", "so", "but",
                             "with", "had", "have", "has", "do", "did", "an", "or",
                             "be", "at", "by", "as", "this", "from", "are", "were",
                             "been", "not", "just", "also", "very", "really", "too",
                             "about", "up", "out", "if", "what", "when", "how", "all",
                             "would", "there", "their", "which", "will", "can", "could",
                             "should", "you", "your", "he", "she", "her", "his", "they",
                             "them", "its", "our", "us", "no", "yes", "than", "then"}
                ev_content = ev_tokens - stopwords
                if len(ev_content) < 2:
                    found += 1  # trivial evidence, count as found
                    continue
                for ret_text in top_k_texts:
                    ret_tokens = set(ret_text.lower().split())
                    overlap = len(ev_content & ret_tokens) / len(ev_content)
                    if overlap >= 0.25:  # 25% content word overlap
                        found += 1
                        break
            recall = found / len(evidence_texts) if evidence_texts else 0
            recall_at_k[k].append(recall)
            recall_by_cat[k].setdefault(cat, []).append(recall)

    results = {}
    for k in k_values:
        scores = recall_at_k[k]
        results[f"recall@{k}"] = sum(scores) / len(scores) if scores else 0.0
        results[f"recall@{k}_count"] = len(scores)

    results["total_with_evidence"] = total
    results["total_with_retrieved"] = matched

    cat_names = {1: "single-hop", 2: "multi-hop", 3: "temporal", 4: "open-domain"}
    results["by_category"] = {}
    for k in k_values:
        for cat, scores in recall_by_cat[k].items():
            cat_label = cat_names.get(cat, str(cat))
            results["by_category"].setdefault(cat_label, {})[f"recall@{k}"] = sum(scores) / len(scores) if scores else 0
            results["by_category"].setdefault(cat_label, {})[f"recall@{k}_n"] = len(scores)

    return results


def main():
    parser = argparse.ArgumentParser(description="Evidence Recall@k for LoCoMo")
    parser.add_argument("--data", required=True, help="Path to locomo10.json")
    parser.add_argument("--results", required=True, help="Path to results JSON or directory of conv*.json files")
    parser.add_argument("--k-values", nargs="+", type=int, default=[5, 10, 20, 60])
    args = parser.parse_args()

    evidence_map = load_evidence_map(args.data)
    print(f"Found {len(evidence_map)} questions with evidence annotations")

    results_path = Path(args.results)
    if results_path.is_dir():
        # Merge parallel results into a single structure
        merged = {"per_question": []}
        for p in sorted(results_path.glob("conv*.json")):
            with open(p) as f:
                data = json.load(f)
            merged["per_question"].extend(data.get("per_question", []))
        # Write temp merged file
        tmp = results_path / "_merged_for_recall.json"
        with open(tmp, "w") as f:
            json.dump(merged, f)
        results = compute_recall_at_k(str(tmp), evidence_map, args.k_values)
        tmp.unlink()
    else:
        results = compute_recall_at_k(args.results, evidence_map, args.k_values)

    print(f"\nEvidence Recall@k:")
    for k in args.k_values:
        r = results.get(f"recall@{k}", 0)
        n = results.get(f"recall@{k}_count", 0)
        print(f"  Recall@{k:2d}: {r*100:.1f}% (n={n})")

    print(f"\nTotal questions with evidence: {results['total_with_evidence']}")
    print(f"Questions with retrieved data: {results['total_with_retrieved']}")

    # Save
    out_dir = results_path if results_path.is_dir() else results_path.parent
    out_path = out_dir / "evidence_recall.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
