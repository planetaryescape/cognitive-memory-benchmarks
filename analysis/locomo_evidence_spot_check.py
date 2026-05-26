"""Human spot-check protocol for the Phase 13 retrieval evidence judge.

Two modes:

  sample  -- write a blind fill-in JSON for the human to annotate, plus a
             paired truth file with the LLM judge's decisions held aside.
  score   -- after the human fills in the blind file, compute raw and Cohen's
             kappa agreement between the human and the LLM judge.

Stratifies the sample across categories and balances judge-covering vs
judge-not-covering memories so kappa is not artificially inflated by the
non-covering majority. This complements the LLM-vs-LLM reliability already
recorded in `judge_reliability.json` with a human anchor on the per-memory
'covers any evidence' decision plus exact-set agreement.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def collect_decisions(packet):
    """Flatten the packet into per-memory decisions usable for stratification."""
    decisions = []
    for item in packet["items"]:
        for row in item["rows"]:
            for mem in row["retrieved"]:
                judge = list(mem.get("covers_evidence_ids", []) or [])
                decisions.append({
                    "subset_index": item["subset_index"],
                    "question": item["question"],
                    "answer": item["answer"],
                    "category": item["category_name"],
                    "condition": row["label"],
                    "evidence": [
                        {"id": eid, "text": txt}
                        for eid, txt in zip(item["evidence_ids"], item["evidence_texts"])
                    ],
                    "memory_rank": mem.get("rank"),
                    "memory_text": mem.get("text", ""),
                    "judge_decision": judge,
                    "judge_covers_any": bool(judge),
                })
    return decisions


def stratified_sample(decisions, n_total, seed):
    """Half judge-covering, half not; spread across categories."""
    rng = random.Random(seed)
    by_class = {True: [], False: []}
    for d in decisions:
        by_class[d["judge_covers_any"]].append(d)
    n_each = n_total // 2
    picks = []
    for cls in (True, False):
        pool = list(by_class[cls])
        rng.shuffle(pool)
        # spread across categories: round-robin
        by_cat = defaultdict(list)
        for d in pool:
            by_cat[d["category"]].append(d)
        cats = list(by_cat)
        rng.shuffle(cats)
        taken = []
        while len(taken) < n_each and any(by_cat[c] for c in cats):
            for c in cats:
                if by_cat[c] and len(taken) < n_each:
                    taken.append(by_cat[c].pop())
        picks.extend(taken)
    rng.shuffle(picks)
    for i, p in enumerate(picks):
        p["spot_check_id"] = i
    return picks


def write_sample(packet_path, blind_path, truth_path, n, seed):
    packet = json.loads(Path(packet_path).read_text())
    decisions = collect_decisions(packet)
    sample = stratified_sample(decisions, n, seed)
    blind = {
        "instructions": (
            "For each item, decide which gold evidence IDs the memory_text actually "
            "supports — i.e. a reader could derive that evidence's fact from the memory "
            "alone (shared topic/names alone do NOT count). Put the IDs in `user_decision` "
            "as a list (empty list [] if none). Use only IDs from the item's `evidence`. "
            "Do NOT look at the truth file; the judge's call is held aside for scoring."
        ),
        "items": [
            {
                "spot_check_id": d["spot_check_id"],
                "category": d["category"],
                "condition": d["condition"],
                "question": d["question"],
                "answer": d["answer"],
                "evidence": d["evidence"],
                "memory_rank": d["memory_rank"],
                "memory_text": d["memory_text"],
                "user_decision": None,  # <-- you fill this in
            }
            for d in sample
        ],
    }
    truth = {
        "items": [
            {"spot_check_id": d["spot_check_id"], "judge_decision": d["judge_decision"]}
            for d in sample
        ],
        "stratification": dict(Counter(d["judge_covers_any"] for d in sample)),
    }
    Path(blind_path).parent.mkdir(parents=True, exist_ok=True)
    Path(blind_path).write_text(json.dumps(blind, indent=2) + "\n")
    Path(truth_path).write_text(json.dumps(truth, indent=2) + "\n")
    print(f"wrote {blind_path} ({len(sample)} items) and {truth_path}")
    print(f"stratification (judge_covers_any): {truth['stratification']}")


def cohens_kappa(pairs):
    n = len(pairs) or 1
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    pa_yes = sum(1 for a, _ in pairs if a) / n
    pb_yes = sum(1 for _, b in pairs if b) / n
    pe = pa_yes * pb_yes + (1 - pa_yes) * (1 - pb_yes)
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 1e-12 else 1.0
    return kappa, po, len(pairs)


def score(blind_path, truth_path, output_path):
    blind = json.loads(Path(blind_path).read_text())
    truth = json.loads(Path(truth_path).read_text())
    truth_by_id = {it["spot_check_id"]: it["judge_decision"] for it in truth["items"]}

    binary_pairs = []
    exact_set_matches = 0
    unfilled = []
    disagreements = []
    for it in blind["items"]:
        user = it.get("user_decision")
        if user is None:
            unfilled.append(it["spot_check_id"])
            continue
        judge = truth_by_id[it["spot_check_id"]]
        u_set = set(user)
        j_set = set(judge)
        binary_pairs.append((bool(u_set), bool(j_set)))
        if u_set == j_set:
            exact_set_matches += 1
        else:
            disagreements.append({
                "spot_check_id": it["spot_check_id"],
                "question": it["question"],
                "memory_text": it["memory_text"],
                "evidence_ids": [e["id"] for e in it["evidence"]],
                "user": sorted(u_set),
                "judge": sorted(j_set),
            })
    if unfilled:
        raise SystemExit(f"{len(unfilled)} items unfilled (ids: {unfilled[:10]}...); "
                         f"set user_decision on every item.")

    kappa, raw, n = cohens_kappa(binary_pairs)
    summary = {
        "n_decisions": n,
        "binary_covers_any": {
            "cohens_kappa": round(kappa, 4),
            "raw_agreement": round(raw, 4),
        },
        "exact_set_agreement": round(exact_set_matches / (n or 1), 4),
        "disagreements": disagreements,
        "interpretation": (
            "Human-vs-judge agreement on the per-memory 'covers >=1 evidence' decision. "
            ">0.8 = strong; 0.6-0.8 = substantial. Exact-set is the stricter ID-equality metric. "
            "Compare to judge_reliability.json (LLM-vs-LLM, kappa=0.754)."
        ),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\nspot-check (n={n}): kappa={kappa:.4f} raw={raw:.4f} "
          f"exact-set={summary['exact_set_agreement']:.4f} disagreements={len(disagreements)}")
    print(f"written: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("sample", help="write blind + truth files")
    s.add_argument(
        "--packet",
        default="tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet_judged.json",
    )
    s.add_argument(
        "--blind",
        default="tuning/runs/phase13-retrieval-evidence/spot_check_blind.json",
    )
    s.add_argument(
        "--truth",
        default="tuning/runs/phase13-retrieval-evidence/spot_check_truth.json",
    )
    s.add_argument("--n", type=int, default=20)
    s.add_argument("--seed", type=int, default=20260526)

    c = sub.add_parser("score", help="compute human-vs-judge agreement")
    c.add_argument(
        "--blind",
        default="tuning/runs/phase13-retrieval-evidence/spot_check_blind.json",
    )
    c.add_argument(
        "--truth",
        default="tuning/runs/phase13-retrieval-evidence/spot_check_truth.json",
    )
    c.add_argument(
        "--output",
        default="tuning/runs/phase13-retrieval-evidence/spot_check_score.json",
    )

    args = parser.parse_args()
    if args.mode == "sample":
        write_sample(args.packet, args.blind, args.truth, args.n, args.seed)
    else:
        score(args.blind, args.truth, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
