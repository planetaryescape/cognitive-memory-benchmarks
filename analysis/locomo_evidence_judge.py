"""LLM-judge for the Phase 13 retrieval evidence packet.

Fills ``covers_evidence_ids`` on every retrieved memory by asking an LLM which
gold evidence IDs each memory supports (fully or partially), then writes a
judged copy of the packet. Score it with ``locomo_manual_retrieval_score.py``.

Retrieved memories are extracted facts with no dialog-ID provenance, so the
match is semantic, not an ID lookup. This mirrors the repo's established
LLM-as-judge methodology (Run M, kappa=0.919). Point chat at a local server via
OPENAI_CHAT_BASE_URL to run free; one batched call judges all memories of one
(question, condition) pair.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.openai_clients import make_chat_client

SYSTEM = (
    "You judge whether retrieved memory statements support gold evidence facts "
    "from a conversation. A memory SUPPORTS an evidence item if it conveys the "
    "same fact or event (full or partial overlap counts). Be strict: surface "
    "similarity or shared entities is not enough; the memory must actually carry "
    "the evidence's information. Only use the provided evidence IDs. Respond with "
    "a single JSON object and nothing else."
)

PROMPT = """Question: {question}
Gold answer: {answer}

Gold evidence (id: text):
{evidence}

Retrieved memories (rank: text):
{memories}

For each memory rank, list which gold evidence IDs it supports. Use [] when it
supports none. Return JSON exactly like:
{{"matches": {{"1": ["{example_id}"], "2": [], ...}}}}
Include every rank from 1 to {n}. Only use IDs from the gold evidence list."""


def parse_matches(text: str, valid_ids: set[str], n: int) -> dict[str, list[str]]:
    """Extract {rank: [evidence_ids]} from a model response, defensively."""
    blob = text.strip()
    if "```" in blob:
        blob = re.sub(r"```(?:json)?", "", blob).strip()
    # Grab the outermost JSON object.
    start, end = blob.find("{"), blob.rfind("}")
    obj = {}
    if start != -1 and end != -1:
        try:
            obj = json.loads(blob[start : end + 1])
        except json.JSONDecodeError:
            obj = {}
    matches = obj.get("matches", obj) if isinstance(obj, dict) else {}
    out: dict[str, list[str]] = {}
    for rank in range(1, n + 1):
        raw = matches.get(str(rank), []) if isinstance(matches, dict) else []
        if not isinstance(raw, list):
            raw = []
        out[str(rank)] = [str(x) for x in raw if str(x) in valid_ids]
    return out


def judge_row(client, model, item, row, max_retries=4):
    evidence_ids = [str(e) for e in item.get("evidence_ids", [])]
    valid = set(evidence_ids)
    if not valid:
        return {"skipped": "no evidence_ids"}
    ev_lines = "\n".join(f"- {eid}: {txt}" for eid, txt in zip(evidence_ids, item.get("evidence_texts", [])))
    retrieved = row.get("retrieved", [])
    mem_lines = "\n".join(f"{m.get('rank', i + 1)}: {m.get('text', '')}" for i, m in enumerate(retrieved))
    prompt = PROMPT.format(
        question=item["question"], answer=item.get("answer", ""), evidence=ev_lines,
        memories=mem_lines, example_id=evidence_ids[0], n=len(retrieved),
    )
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                temperature=0,
            )
            content = resp.choices[0].message.content
            matches = parse_matches(content, valid, len(retrieved))
            # Write annotations back onto the row.
            stray = 0
            for i, m in enumerate(retrieved):
                m["covers_evidence_ids"] = matches.get(str(m.get("rank", i + 1)), [])
            return {"ok": True, "stray_ids_dropped": stray}
        except Exception as e:  # noqa: BLE001 — retry transient server errors
            last_err = str(e)
            if attempt < max_retries - 1:
                time.sleep(min(30, 2 ** attempt * 2))
    return {"error": last_err}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet",
        default="tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet.json",
    )
    parser.add_argument(
        "--output",
        default="tuning/runs/phase13-retrieval-evidence/retrieval_annotation_packet_judged.json",
    )
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--limit", type=int, default=0, help="cap questions (0 = all)")
    args = parser.parse_args()

    packet = json.loads(Path(args.packet).read_text())
    items = packet["items"]
    if args.limit:
        items = items[: args.limit]
        packet["items"] = items

    client = make_chat_client()
    total_rows = sum(len(it["rows"]) for it in items)
    print(f"Judging {len(items)} questions x {total_rows // max(len(items), 1)} conditions = {total_rows} rows", flush=True)

    done = 0
    errors = 0
    t0 = time.time()
    for qi, item in enumerate(items, 1):
        for row in item["rows"]:
            res = judge_row(client, args.model, item, row)
            done += 1
            if res.get("error"):
                errors += 1
                print(f"  ERR q{qi} {row['label']}: {res['error'][:80]}", flush=True)
        if qi % 5 == 0 or qi == len(items):
            # Periodic flush so a long run leaves a usable artifact.
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(json.dumps(packet, indent=2) + "\n")
            rate = done / (time.time() - t0)
            print(f"  [{qi}/{len(items)}] rows={done}/{total_rows} errors={errors} "
                  f"({rate:.1f} rows/s)", flush=True)

    Path(args.output).write_text(json.dumps(packet, indent=2) + "\n")
    print(f"Done in {time.time() - t0:.0f}s. errors={errors}. Wrote {args.output}", flush=True)
    print("Score with: .venv/bin/python analysis/locomo_manual_retrieval_score.py "
          f"{args.output} --output tuning/runs/phase13-retrieval-evidence/retrieval_evidence_scored.json "
          "--markdown tuning/runs/phase13-retrieval-evidence/retrieval_evidence_scored.md")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
