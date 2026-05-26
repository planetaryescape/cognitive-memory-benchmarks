"""Inter-judge reliability for the Phase 13 retrieval evidence judge.

Re-judges a stratified sample of the primary judged packet with a second,
reworded prompt (same model), then reports Cohen's kappa and raw agreement on
the per-memory "covers any evidence" decision, plus exact-set agreement. This
mirrors the repo's Run M reliability methodology (alternative prompt, kappa=0.919
for answer judging) and quantifies the "single judge, not validated" caveat.

Run after the primary judge, pointing chat at the same local server:
    OPENAI_CHAT_BASE_URL=... python analysis/locomo_evidence_judge_reliability.py
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.openai_clients import make_chat_client
from analysis.locomo_evidence_judge import parse_matches

# Reworded second-judge prompt — same task and I/O contract, different framing.
SYSTEM_ALT = (
    "You are checking retrieval quality. For a question with its gold supporting "
    "evidence and a list of candidate memory statements, decide for each candidate "
    "which evidence items it actually conveys. A candidate conveys an evidence item "
    "only if a reader could derive that evidence's fact from the candidate alone; "
    "shared topic or names are not enough. Use only the listed evidence IDs and "
    "reply with one JSON object only."
)
PROMPT_ALT = """QUESTION: {question}
EXPECTED ANSWER: {answer}

GOLD EVIDENCE:
{evidence}

CANDIDATE MEMORIES:
{memories}

Return JSON mapping each candidate number to the list of gold evidence IDs it
conveys (empty list if none):
{{"matches": {{"1": [], "2": ["{example_id}"], ...}}}}
Cover every candidate from 1 to {n}; IDs must come from the gold evidence."""


def judge_row_alt(client, model, item, row):
    evidence_ids = [str(e) for e in item.get("evidence_ids", [])]
    valid = set(evidence_ids)
    ev_lines = "\n".join(f"- {eid}: {txt}" for eid, txt in zip(evidence_ids, item.get("evidence_texts", [])))
    retrieved = row.get("retrieved", [])
    mem_lines = "\n".join(f"{m.get('rank', i + 1)}: {m.get('text', '')}" for i, m in enumerate(retrieved))
    prompt = PROMPT_ALT.format(
        question=item["question"], answer=item.get("answer", ""), evidence=ev_lines,
        memories=mem_lines, example_id=evidence_ids[0], n=len(retrieved),
    )
    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_ALT}, {"role": "user", "content": prompt}],
                temperature=0,
            )
            return parse_matches(resp.choices[0].message.content, valid, len(retrieved))
        except Exception:  # noqa: BLE001
            if attempt < 3:
                time.sleep(min(30, 2 ** attempt * 2))
    return {}


def stratified_sample(items, per_category):
    by_cat = defaultdict(list)
    for it in items:
        by_cat[it["category_name"]].append(it)
    sample = []
    for cat in sorted(by_cat):
        sample.extend(by_cat[cat][:per_category])
    return sample


def cohens_kappa(pairs):
    """pairs: list of (a_bool, b_bool). Returns (kappa, raw_agreement, n)."""
    n = len(pairs) or 1
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    pa_yes = sum(1 for a, _ in pairs if a) / n
    pb_yes = sum(1 for _, b in pairs if b) / n
    pe = pa_yes * pb_yes + (1 - pa_yes) * (1 - pb_yes)
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 1e-12 else 1.0
    return kappa, po, len(pairs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--judged",
        default="tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet_judged.json",
    )
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--per-category", type=int, default=5, help="questions sampled per category")
    parser.add_argument(
        "--output",
        default="tuning/runs/phase13-retrieval-evidence/judge_reliability.json",
    )
    args = parser.parse_args()

    packet = json.loads(Path(args.judged).read_text())
    sample = stratified_sample(packet["items"], args.per_category)
    client = make_chat_client()
    total_rows = sum(len(it["rows"]) for it in sample)
    print(f"Reliability sample: {len(sample)} questions x ~5 conditions = {total_rows} rows", flush=True)

    binary_pairs = []          # (primary_covers_any, second_covers_any) per memory
    exact_set_matches = 0      # per-memory exact covers_evidence_ids set equality
    memory_count = 0
    done = 0
    t0 = time.time()
    for it in sample:
        for row in it["rows"]:
            primary = [set(m.get("covers_evidence_ids", []) or []) for m in row["retrieved"]]
            second_matches = judge_row_alt(client, args.model, it, copy.deepcopy(row))
            for i, m in enumerate(row["retrieved"]):
                p = primary[i]
                s = set(second_matches.get(str(m.get("rank", i + 1)), []))
                binary_pairs.append((bool(p), bool(s)))
                exact_set_matches += int(p == s)
                memory_count += 1
            done += 1
        if done % 10 == 0 or done == total_rows:
            print(f"  rows {done}/{total_rows} ({done / (time.time() - t0):.2f}/s)", flush=True)

    kappa, raw, n = cohens_kappa(binary_pairs)
    summary = {
        "judged_packet": args.judged,
        "second_judge": f"{args.model} (alternative prompt)",
        "sample_questions": len(sample),
        "sample_rows": total_rows,
        "memory_decisions": memory_count,
        "binary_covers_any": {
            "cohens_kappa": round(kappa, 4),
            "raw_agreement": round(raw, 4),
            "n": n,
        },
        "exact_set_agreement": round(exact_set_matches / (memory_count or 1), 4),
        "interpretation": (
            "kappa on the per-memory 'covers >=1 evidence' decision between the "
            "primary judge and a reworded second prompt (same model). >0.8 = strong; "
            "0.6-0.8 = substantial. Exact-set agreement is stricter (identical ID sets)."
        ),
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(summary, indent=2) + "\n")
    print("\n=== RELIABILITY ===")
    print(f"Cohen's kappa (covers-any): {kappa:.4f} | raw agreement: {raw:.4f} | "
          f"exact-set: {summary['exact_set_agreement']:.4f} | decisions: {memory_count}")
    print(f"written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
