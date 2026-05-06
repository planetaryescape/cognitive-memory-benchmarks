#!/usr/bin/env python3
"""
Oracle Ceiling for LoCoMo.

Feeds ground-truth evidence text directly as context (no retrieval),
generates answer, scores. Measures the answer-generation ceiling
independent of retrieval quality.

Usage:
    python locomo/oracle_ceiling.py --data locomo/data/locomo10.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.metrics import token_f1, token_f1_mem0, bleu1, aggregate_results, LOCOMO_CATEGORIES
from shared.adapter import RetrievalResult, QueryResult


def load_locomo(path):
    with open(path) as f:
        return json.load(f)


def extract_evidence_text(conversation, qa_item):
    """Extract the actual text of evidence dialog turns."""
    conv_data = conversation.get("conversation", {})
    evidence_ids = qa_item.get("evidence", [])

    # Build dia_id -> text map
    dia_text = {}
    session_keys = sorted(
        [k for k in conv_data if k.startswith("session_") and not k.endswith(("_date_time", "_observation", "_summary"))],
        key=lambda x: int(x.split("_")[1])
    )
    for session_key in session_keys:
        session_ts = conv_data.get(f"{session_key}_date_time", "")
        for turn in conv_data.get(session_key, []):
            dia_id = turn.get("dia_id", "")
            speaker = turn.get("speaker", "")
            text = turn.get("text", "")
            if dia_id:
                dia_text[dia_id] = f"[{session_ts}] {speaker}: {text}"

    # Resolve evidence
    texts = []
    for eid in evidence_ids:
        eid = str(eid).strip()
        if eid in dia_text:
            texts.append(dia_text[eid])
        else:
            for did, dtxt in dia_text.items():
                if eid in did or did in eid:
                    texts.append(dtxt)
                    break

    return texts


MEM0_ORACLE_PROMPT = """You are an intelligent memory assistant tasked with retrieving accurate information from conversation memories.

# CONTEXT:
You have access to memories from a conversation. These memories contain
timestamped information that may be relevant to answering the question.

# INSTRUCTIONS:
1. Carefully analyze all provided memories
2. Pay special attention to the timestamps to determine the answer
3. If the question asks about a specific event or fact, look for direct evidence in the memories
4. If the memories contain contradictory information, prioritize the most recent memory
5. If there is a question about time references (like "last year", "two months ago", etc.),
   calculate the actual date based on the memory timestamp.
6. Always convert relative time references to specific dates, months, or years.
7. Focus only on the content of the memories. Do not confuse character
   names mentioned in memories with the actual users who created those memories.
8. The answer should be less than 5-6 words.

# APPROACH (Think step by step):
1. First, examine all memories that contain information related to the question
2. Examine the timestamps and content of these memories carefully
3. Look for explicit mentions of dates, times, locations, or events that answer the question
4. If the answer requires calculation (e.g., converting relative time references), show your work
5. Formulate a precise, concise answer based solely on the evidence in the memories
6. Double-check that your answer directly addresses the question asked
7. Ensure your final answer is specific and avoids vague time references

Memories:
{memories}

Question: {question}

Answer:"""


def generate_oracle_answer(question, evidence_texts, client, model="gpt-4o-mini", category=0, prompt_mode="official"):
    """Generate answer using oracle evidence as context."""
    if not evidence_texts:
        memories_text = "(No evidence available)"
    else:
        memories_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(evidence_texts))

    if prompt_mode == "mem0":
        prompt = MEM0_ORACLE_PROMPT.format(memories=memories_text, question=question)
        max_tokens = None  # Mem0 doesn't limit
    else:
        prompt = f"""Below are the exact relevant conversation excerpts that contain the answer.

{memories_text}

Based on the above, write an answer in the form of a short phrase for the following question. Answer with exact words from the excerpts whenever possible.

Question: {question} Short answer:"""

        if category == 2:
            prompt += " Use DATE of CONVERSATION to answer with an approximate date."
        max_tokens = 100

    api_kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    if max_tokens is not None:
        api_kwargs["max_tokens"] = max_tokens

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(**api_kwargs)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise


def main():
    parser = argparse.ArgumentParser(description="Oracle Ceiling for LoCoMo")
    parser.add_argument("--data", required=True, help="Path to locomo10.json")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--output", default="locomo/results/v6/oracle_ceiling.json")
    parser.add_argument("--max-conversations", type=int, default=None)
    parser.add_argument("--prompt-mode", default="official", choices=["official", "mem0"],
                        help="Prompt mode: official (original) or mem0 (match Run A prompt)")
    args = parser.parse_args()

    from openai import OpenAI
    client = OpenAI()

    data = load_locomo(args.data)
    if args.max_conversations:
        data = data[:args.max_conversations]

    print(f"Oracle Ceiling: {len(data)} conversations, model={args.model}, prompt={args.prompt_mode}")

    all_results = []
    total_start = time.time()

    for conv_idx, conversation in enumerate(data):
        qa_items = conversation.get("qa", [])
        print(f"\nConv {conv_idx}: {len(qa_items)} questions")

        for qi, qa in enumerate(qa_items):
            category = int(qa.get("category", 0))

            # Skip adversarial (category 5) — no standard answer
            ground_truth = qa.get("answer", qa.get("adversarial_answer", ""))
            if not ground_truth or category == 5:
                continue

            evidence_texts = extract_evidence_text(conversation, qa)

            answer = generate_oracle_answer(
                question=qa["question"],
                evidence_texts=evidence_texts,
                client=client,
                model=args.model,
                category=category,
                prompt_mode=args.prompt_mode,
            )

            f1_result = token_f1(answer, str(ground_truth))
            f1_mem0_result = token_f1_mem0(answer, str(ground_truth))
            bleu1_score = bleu1(answer, str(ground_truth))

            result = {
                "conv_index": conv_idx,
                "question_index": qi,
                "question": qa["question"],
                "ground_truth": str(ground_truth),
                "prediction": answer,
                "category": category,
                "category_name": LOCOMO_CATEGORIES.get(category, "unknown"),
                "f1": f1_result["f1"],
                "f1_mem0": f1_mem0_result["f1"],
                "bleu1": bleu1_score,
                "num_evidence": len(evidence_texts),
                "has_evidence": len(evidence_texts) > 0,
            }
            all_results.append(result)

            if qi % 20 == 0:
                print(f"  {qi}/{len(qa_items)}...")

    total_time = time.time() - total_start

    # Aggregate
    agg = aggregate_results(all_results)
    valid = [r for r in all_results if r.get("category", 5) <= 4]
    overall_f1_mem0 = sum(r["f1_mem0"] for r in valid) / len(valid) if valid else 0

    print(f"\n{'='*60}")
    print("ORACLE CEILING RESULTS")
    print(f"{'='*60}")
    print(f"Overall F1 (LoCoMo): {agg['overall']['mean_f1']*100:.1f}%")
    print(f"Overall F1 (Mem0):   {overall_f1_mem0*100:.1f}%")
    for cat_name, cat_data in agg.get("by_category", {}).items():
        print(f"  {cat_name:15s}: F1={cat_data['mean_f1']*100:.1f}% (n={cat_data['count']})")

    with_evidence = [r for r in valid if r["has_evidence"]]
    if with_evidence:
        print(f"\nWith evidence only: F1={sum(r['f1'] for r in with_evidence)/len(with_evidence)*100:.1f}% (n={len(with_evidence)})")

    print(f"\nTime: {total_time:.0f}s")

    # Save
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({
            "aggregate": agg,
            "overall_f1_mem0": overall_f1_mem0,
            "per_question": all_results,
            "meta": {
                "model": args.model,
                "total_time_seconds": total_time,
                "timestamp": datetime.now().isoformat(),
                "type": "oracle_ceiling",
            },
        }, f, indent=2, default=str)
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
