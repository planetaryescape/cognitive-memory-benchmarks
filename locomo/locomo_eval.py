#!/usr/bin/env python3
"""
LoCoMo Benchmark Evaluation for Cognitive Memory Systems.

Evaluates a memory system on the LoCoMo long-term conversational memory
benchmark. Direct comparison with FadeMem, Mem0, and MemGPT.

Usage:
    python locomo_eval.py --data data/locomo/data/locomo10.json
    python locomo_eval.py --data data/locomo/data/locomo10.json --adapter naive_rag
    python locomo_eval.py --data data/locomo/data/locomo10.json --use-judge

Pipeline:
    1. Load LoCoMo conversations
    2. For each conversation:
       a. Reset memory system
       b. Ingest sessions chronologically (memory extraction)
       c. Query with each QA question (memory retrieval + answer generation)
       d. Score against ground truth
    3. Aggregate and report metrics by category
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from shared.memory_adapter import (
    CognitiveMemoryAdapter,
    CognitiveMemoryRawTurnAdapter,
    NaiveRAGAdapter,
    FullContextAdapter,
    QueryResult,
)
from shared.metrics import (
    token_f1,
    token_f1_mem0,
    bleu1,
    llm_judge,
    retrieval_precision_at_k,
    aggregate_results,
    LOCOMO_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_locomo(path: str) -> list[dict]:
    """Load LoCoMo dataset from JSON file."""
    with open(path) as f:
        data = json.load(f)

    print(f"Loaded {len(data)} conversations from {path}")
    for i, conv in enumerate(data):
        sessions = [k for k in conv.get("conversation", {}) if k.startswith("session_") and not k.endswith("_date_time")]
        qa_count = len(conv.get("qa", []))
        print(f"  Conv {i}: {len(sessions)} sessions, {qa_count} QA questions")

    return data


def extract_sessions(conversation: dict) -> list[dict]:
    """
    Extract sessions in chronological order from a LoCoMo conversation.
    
    Returns list of:
    {
        "session_id": "session_1",
        "timestamp": "2023-01-15T10:00:00",
        "turns": [{"speaker": str, "text": str, "dia_id": str}, ...]
    }
    """
    conv_data = conversation.get("conversation", {})
    speaker_a = conv_data.get("speaker_a", "Speaker A")
    speaker_b = conv_data.get("speaker_b", "Speaker B")

    sessions = []
    # Find all session keys
    session_keys = sorted(
        [k for k in conv_data if k.startswith("session_") and not k.endswith(("_date_time", "_observation", "_summary"))],
        key=lambda x: int(x.split("_")[1])
    )

    for session_key in session_keys:
        timestamp_key = f"{session_key}_date_time"
        timestamp = conv_data.get(timestamp_key, "")

        turns = []
        for turn in conv_data.get(session_key, []):
            turns.append({
                "speaker": turn.get("speaker", ""),
                "text": turn.get("text", ""),
                "dia_id": turn.get("dia_id", ""),
            })

        sessions.append({
            "session_id": session_key,
            "timestamp": timestamp,
            "turns": turns,
            "speaker_a": speaker_a,
            "speaker_b": speaker_b,
        })

    return sessions


def extract_qa(conversation: dict) -> list[dict]:
    """
    Extract QA pairs from a LoCoMo conversation.
    
    Returns list of:
    {
        "question": str,
        "answer": str,
        "category": int (1-5),
        "evidence": list[str] (dialog IDs containing the answer),
    }
    """
    qa_items = conversation.get("qa", [])
    result = []
    for item in qa_items:
        raw_answer = item.get("answer", "")
        result.append({
            "question": item.get("question", ""),
            "answer": str(raw_answer) if raw_answer is not None else "",
            "category": item.get("category", 0),
            "evidence": item.get("evidence", []),
        })
    return result


# ---------------------------------------------------------------------------
# Answer generation using retrieved memories
# ---------------------------------------------------------------------------

# Matches the official LoCoMo evaluation prompt from snap-research/locomo
# with per-category date hint (category 2) exactly as the benchmark authors do.
# Mem0's prompt is far more aggressive (7-step CoT with worked examples).
ANSWER_PROMPT = """Below are memories from previous conversations.

{memories}

Based on the above memories, write an answer in the form of a short phrase for the following question. Answer with exact words from the memories whenever possible. Say "unknown" only if the memories contain absolutely nothing relevant.

Question: {question} Short answer:"""

# Appended to category 2 (temporal) questions only, matching official LoCoMo protocol
TEMPORAL_DATE_HINT = " Use DATE of CONVERSATION to answer with an approximate date."

# Our tuned prompt — optimized for our system's strengths.
# No category-specific hints — all guidance is in the prompt itself.
TUNED_ANSWER_PROMPT = """Below are memories from previous conversations.

{memories}

Based on the above memories, write an answer in the form of a short phrase for the following question. Say "unknown" only if the memories contain absolutely nothing relevant. If you can make a reasonable inference from the memories, DO answer — even approximately.

Guidelines:
- For dates, use the memory timestamps to calculate absolute dates (e.g., "May 2023", not "last year"). If you can narrow it to a month or year, give your best estimate rather than saying unknown.
- If the question asks what someone would likely do, reason from the evidence in the memories.
- Answer with ONLY the specific fact asked for — no context, no explanation, no full sentences.

Question: {question} Short answer:"""

# Mem0's EXACT prompt from mem0ai/mem0/evaluation/prompts.py (ANSWER_PROMPT)
# Replicated VERBATIM — including two-speaker memory split.
# Key differences from official LoCoMo: 7-step CoT, worked date examples,
# separate speaker memories, system message role, no max_tokens limit,
# top_k=30 per speaker (60 total).
MEM0_ANSWER_PROMPT = """You are an intelligent memory assistant tasked with retrieving accurate information from conversation memories.

# CONTEXT:
You have access to memories from two speakers in a conversation. These memories contain
timestamped information that may be relevant to answering the question.

# INSTRUCTIONS:
1. Carefully analyze all provided memories from both speakers
2. Pay special attention to the timestamps to determine the answer
3. If the question asks about a specific event or fact, look for direct evidence in the memories
4. If the memories contain contradictory information, prioritize the most recent memory
5. If there is a question about time references (like "last year", "two months ago", etc.),
   calculate the actual date based on the memory timestamp. For example, if a memory from
   4 May 2022 mentions "went to India last year," then the trip occurred in 2021.
6. Always convert relative time references to specific dates, months, or years. For example,
   convert "last year" to "2022" or "two months ago" to "March 2023" based on the memory
   timestamp. Ignore the reference while answering the question.
7. Focus only on the content of the memories from both speakers. Do not confuse character
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

Memories for user {speaker_a}:
{speaker_a_memories}

Memories for user {speaker_b}:
{speaker_b_memories}

Question: {question}

Answer:"""

# Prompt mode constants
PROMPT_OFFICIAL = "official"
PROMPT_TUNED = "tuned"
PROMPT_MEM0 = "mem0"


def generate_answer(
    question: str,
    query_result: QueryResult,
    client=None,
    model: str = "gpt-4o-mini",
    temperature: float = 0,
    max_tokens: int = None,
    prompt_mode: str = PROMPT_OFFICIAL,
    speaker_a: str = "",
    speaker_b: str = "",
) -> str:
    """Generate an answer using retrieved memories as context."""
    if client is None:
        from openai import OpenAI
        client = OpenAI()

    # Deduplicate retrieved memories (exact content matches)
    if query_result.retrieved_memories:
        seen = set()
        deduped = []
        for mem in query_result.retrieved_memories:
            key = mem.content.strip().lower()
            if key not in seen:
                seen.add(key)
                deduped.append(mem)
        query_result = QueryResult(
            retrieved_memories=deduped,
            retrieval_time_ms=query_result.retrieval_time_ms,
            answer=query_result.answer,
            memories_considered=query_result.memories_considered,
        )

    # Format retrieved memories
    if not query_result.retrieved_memories:
        if prompt_mode == PROMPT_MEM0:
            # Two-speaker format even when empty
            memories_text = None  # handled below
        else:
            memories_text = "(No relevant memories found)"
    else:
        memories_text = None  # will be set below

    if prompt_mode == PROMPT_MEM0:
        import json as _json
        # Split memories by speaker (heuristic: check if memory mentions speaker name)
        speaker_a_mems = []
        speaker_b_mems = []
        for mem in (query_result.retrieved_memories or []):
            content_lower = mem.content.lower()
            ts = mem.created_at or ""
            formatted = f"{ts}: {mem.content}" if ts else mem.content
            # Assign to speaker based on whose name appears in the memory
            a_match = speaker_a.lower() in content_lower if speaker_a else False
            b_match = speaker_b.lower() in content_lower if speaker_b else False
            if a_match and not b_match:
                speaker_a_mems.append(formatted)
            elif b_match and not a_match:
                speaker_b_mems.append(formatted)
            else:
                # Mentions both or neither — add to both (Mem0 stores per-user so overlap is natural)
                speaker_a_mems.append(formatted)
                speaker_b_mems.append(formatted)

        speaker_a_text = _json.dumps(speaker_a_mems, indent=4)
        speaker_b_text = _json.dumps(speaker_b_mems, indent=4)
    elif memories_text is None:
        memories_parts = []
        for i, mem in enumerate(query_result.retrieved_memories, 1):
            memories_parts.append(f"{i}. {mem.content}")
        memories_text = "\n".join(memories_parts)

    # Select prompt template and format
    if prompt_mode == PROMPT_MEM0:
        template = MEM0_ANSWER_PROMPT
        prompt = template.format(
            speaker_a=speaker_a or "Speaker A",
            speaker_b=speaker_b or "Speaker B",
            speaker_a_memories=speaker_a_text,
            speaker_b_memories=speaker_b_text,
            question=question,
        )
    elif prompt_mode == PROMPT_TUNED:
        prompt = TUNED_ANSWER_PROMPT.format(memories=memories_text, question=question)
    else:
        prompt = ANSWER_PROMPT.format(memories=memories_text, question=question)

    # Mem0 uses system message role; others use user message
    if prompt_mode == PROMPT_MEM0:
        messages = [{"role": "system", "content": prompt}]
    else:
        messages = [{"role": "user", "content": prompt}]

    # Build API kwargs — Mem0 doesn't set max_tokens (uses API default)
    api_kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    if max_tokens is not None:
        api_kwargs["max_tokens"] = max_tokens

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(**api_kwargs)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt < 2 and ("500" in str(e) or "server_error" in str(e)):
                import time as _time
                _time.sleep(2 ** attempt)
                continue
            raise


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def evaluate_conversation(
    conversation: dict,
    adapter,
    conv_index: int,
    client=None,
    model: str = "gpt-4o-mini",
    use_judge: bool = False,
    verbose: bool = True,
    answer_temperature: float = 0,
    answer_max_tokens: int = 32,
    prompt_mode: str = PROMPT_OFFICIAL,
    top_k_override: int = None,
) -> list[dict]:
    """
    Evaluate a single conversation: ingest sessions, query QA, score.
    """
    # Reset memory system
    adapter.reset()

    # Extract sessions and QA
    sessions = extract_sessions(conversation)
    qa_items = extract_qa(conversation)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Conversation {conv_index}: {len(sessions)} sessions, {len(qa_items)} questions")
        print(f"{'='*60}")

    # Phase 1: Ingest all sessions chronologically
    ingest_start = time.time()
    for session in sessions:
        if verbose:
            print(f"  Ingesting {session['session_id']} ({len(session['turns'])} turns)...", end=" ", flush=True)
        
        adapter.ingest_session(
            turns=session["turns"],
            session_id=session["session_id"],
            timestamp=session["timestamp"],
            speaker_a=session["speaker_a"],
            speaker_b=session["speaker_b"],
        )
        
        if verbose:
            print("done")

    ingest_time = time.time() - ingest_start
    if verbose:
        print(f"  Ingestion complete in {ingest_time:.1f}s")

    # Phase 2: Query with each QA question
    results = []
    for qi, qa in enumerate(qa_items):
        # Skip adversarial (category 5) during eval, but still run for completeness
        category = qa.get("category", 0)
        
        if verbose and qi % 10 == 0:
            print(f"  Querying {qi+1}/{len(qa_items)}...")

        # Query memory system
        # Mem0 uses top_k=30 per speaker (60 total); our default is 20
        effective_top_k = top_k_override if top_k_override else (60 if prompt_mode == PROMPT_MEM0 else 20)
        query_result = adapter.query(
            question=qa["question"],
            timestamp=sessions[-1]["timestamp"] if sessions else None,  # query at "now"
            top_k=effective_top_k,
        )

        # Get speaker names for Mem0 two-speaker format
        conv_speaker_a = sessions[0]["speaker_a"] if sessions else ""
        conv_speaker_b = sessions[0]["speaker_b"] if sessions else ""

        # Generate answer from retrieved memories
        question_text = qa["question"]
        if prompt_mode == PROMPT_TUNED:
            # Tuned prompt has all guidance built in — no category-specific hints
            pass
        elif prompt_mode == PROMPT_MEM0:
            # Mem0 prompt has built-in date resolution — no extra hint needed
            pass
        else:
            # Official mode: date hint only for category 2, matching LoCoMo protocol
            if category == 2:
                question_text = question_text + TEMPORAL_DATE_HINT

        answer = generate_answer(
            question=question_text,
            query_result=query_result,
            client=client,
            model=model,
            temperature=answer_temperature,
            max_tokens=answer_max_tokens,
            prompt_mode=prompt_mode,
            speaker_a=conv_speaker_a,
            speaker_b=conv_speaker_b,
        )

        # Score: token F1 (LoCoMo standard: Counter-based with Porter stemming)
        f1_result = token_f1(answer, qa["answer"])

        # Also compute Mem0's F1 (set-based, no stemming) for apples-to-apples comparison
        f1_mem0_result = token_f1_mem0(answer, qa["answer"])

        # BLEU-1 (Mem0 reports this as their third metric alongside F1 and LLM Judge)
        bleu1_score = bleu1(answer, qa["answer"])

        result = {
            "conv_index": conv_index,
            "question_index": qi,
            "question": qa["question"],
            "ground_truth": qa["answer"],
            "prediction": answer,
            "category": category,
            "category_name": LOCOMO_CATEGORIES.get(category, "unknown"),
            "f1": f1_result["f1"],
            "precision": f1_result["precision"],
            "recall": f1_result["recall"],
            "f1_mem0": f1_mem0_result["f1"],
            "precision_mem0": f1_mem0_result["precision"],
            "recall_mem0": f1_mem0_result["recall"],
            "bleu1": bleu1_score,
            "num_retrieved": len(query_result.retrieved_memories),
            "retrieval_time_ms": query_result.retrieval_time_ms,
        }

        # Optional: LLM-as-judge
        if use_judge and category <= 4:
            judge_result = llm_judge(
                question=qa["question"],
                prediction=answer,
                ground_truth=qa["answer"],
                client=client,
                model=model,
            )
            result["llm_correct"] = judge_result["correct"]

        results.append(result)

    # Phase 3: Collect stats
    stats = adapter.get_stats()
    if verbose:
        print(f"  Memory stats: {stats.total_memories} total, "
              f"{stats.core_memories} core, {stats.faint_memories} faint, "
              f"avg retention={stats.avg_retention:.2f}")

    return results


def run_evaluation(
    data_path: str,
    adapter_name: str = "cognitive_memory",
    model: str = "gpt-4o-mini",
    use_judge: bool = False,
    output_path: str = None,
    max_conversations: int = None,
    verbose: bool = True,
    answer_temperature: float = 0,
    answer_max_tokens: int = 32,
    prompt_mode: str = PROMPT_OFFICIAL,
    dual_perspective: bool = False,
    top_k: int = None,
    deep_recall: bool = False,
    custom_extraction_instructions: str = None,
    rerank: bool = False,
    rerank_factor: int = 2,
    start_from: int = 0,
    extraction_mode: str = "semantic",
):
    """
    Run full LoCoMo evaluation.
    """
    # Select adapter
    adapters = {
        "cognitive_memory": CognitiveMemoryAdapter,
        "cognitive_memory_raw": CognitiveMemoryRawTurnAdapter,
        "naive_rag": NaiveRAGAdapter,
        "full_context": FullContextAdapter,
    }

    if adapter_name not in adapters:
        print(f"Unknown adapter: {adapter_name}. Choose from: {list(adapters.keys())}")
        sys.exit(1)

    adapter_kwargs = {"llm_model": model}
    if adapter_name == "cognitive_memory":
        if dual_perspective:
            adapter_kwargs["dual_perspective"] = True
        if deep_recall:
            adapter_kwargs["deep_recall"] = True
        if custom_extraction_instructions:
            adapter_kwargs["custom_extraction_instructions"] = custom_extraction_instructions
        if rerank:
            adapter_kwargs["rerank"] = True
            adapter_kwargs["rerank_factor"] = rerank_factor
        if extraction_mode != "semantic":
            adapter_kwargs["extraction_mode"] = extraction_mode
    adapter = adapters[adapter_name](**adapter_kwargs)
    print(f"Using adapter: {adapter_name}")
    print(f"LLM model: {model}")
    print(f"Answer settings: temperature={answer_temperature}, max_tokens={answer_max_tokens}")
    print(f"Answer prompt: {prompt_mode}")
    print(f"Dual perspective: {'enabled' if dual_perspective else 'disabled'}")
    print(f"Deep recall: {'enabled' if deep_recall else 'disabled'}")
    print(f"Rerank: {'enabled (factor=' + str(rerank_factor) + ')' if rerank else 'disabled'}")
    print(f"Custom extraction instructions: {'loaded' if custom_extraction_instructions else 'none'}")
    print(f"Top-k override: {top_k if top_k else 'default (20 standard, 60 mem0)'}")
    print(f"LLM judge: {'enabled' if use_judge else 'disabled'}")

    # Load data
    data = load_locomo(data_path)
    if max_conversations:
        data = data[:max_conversations]

    # Initialize OpenAI client
    from openai import OpenAI
    client = OpenAI()

    # Run evaluation
    all_results = []
    total_start = time.time()

    for i, conversation in enumerate(data):
        if i < start_from:
            print(f"\n--- Skipping conversation {i} (resuming from {start_from}) ---")
            continue
        conv_results = evaluate_conversation(
            conversation=conversation,
            adapter=adapter,
            conv_index=i,
            client=client,
            model=model,
            use_judge=use_judge,
            verbose=verbose,
            answer_temperature=answer_temperature,
            answer_max_tokens=answer_max_tokens,
            prompt_mode=prompt_mode,
            top_k_override=top_k,
        )
        all_results.extend(conv_results)

    total_time = time.time() - total_start

    # Aggregate (LoCoMo standard F1)
    agg = aggregate_results(all_results)

    # Also aggregate Mem0-method F1 and BLEU-1 for apples-to-apples comparison
    mem0_valid = [r for r in all_results if r.get("category", 5) <= 4]
    if mem0_valid:
        overall_f1_mem0 = sum(r["f1_mem0"] for r in mem0_valid) / len(mem0_valid)
        overall_bleu1 = sum(r["bleu1"] for r in mem0_valid) / len(mem0_valid)
        by_cat_mem0 = {}
        _cats = LOCOMO_CATEGORIES
        for cat_id, cat_name in _cats.items():
            if cat_id == 5:
                continue
            cat_results = [r for r in mem0_valid if r.get("category") == cat_id]
            if cat_results:
                by_cat_mem0[cat_name] = {
                    "count": len(cat_results),
                    "mean_f1": sum(r["f1_mem0"] for r in cat_results) / len(cat_results),
                    "mean_bleu1": sum(r["bleu1"] for r in cat_results) / len(cat_results),
                }
        agg["mem0_f1_method"] = {
            "overall_f1": overall_f1_mem0,
            "overall_bleu1": overall_bleu1,
            "by_category": by_cat_mem0,
            "note": "Mem0's exact metrics: set-based F1 (no stemming) + BLEU-1 (nltk)",
        }

    agg["meta"] = {
        "adapter": adapter_name,
        "model": model,
        "answer_temperature": answer_temperature,
        "answer_max_tokens": answer_max_tokens,
        "prompt_mode": prompt_mode,
        "dual_perspective": dual_perspective,
        "deep_recall": deep_recall,
        "custom_extraction_instructions": bool(custom_extraction_instructions),
        "rerank": rerank,
        "rerank_factor": rerank_factor if rerank else None,
        "top_k_override": top_k,
        "use_judge": use_judge,
        "num_conversations": len(data),
        "total_questions": len(all_results),
        "total_time_seconds": total_time,
        "timestamp": datetime.now().isoformat(),
    }

    # Print results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Adapter: {adapter_name}")
    print(f"Questions evaluated: {agg['overall']['num_questions']} (categories 1-4)")
    print(f"Overall F1 (LoCoMo):  {agg['overall']['mean_f1']:.4f} ({agg['overall']['mean_f1']*100:.1f}%)")
    if "mem0_f1_method" in agg:
        m0f1 = agg["mem0_f1_method"]["overall_f1"]
        m0b1 = agg["mem0_f1_method"]["overall_bleu1"]
        print(f"Overall F1 (Mem0):    {m0f1:.4f} ({m0f1*100:.1f}%)")
        print(f"Overall BLEU-1:       {m0b1:.4f} ({m0b1*100:.1f}%)")
    if agg["overall"]["llm_accuracy"] is not None:
        print(f"LLM Judge Accuracy: {agg['overall']['llm_accuracy']:.4f} ({agg['overall']['llm_accuracy']*100:.1f}%)")

    print(f"\nPer-category breakdown (LoCoMo F1 / Mem0 F1 / BLEU-1):")
    for cat_name, cat_data in agg.get("by_category", {}).items():
        f1_pct = cat_data["mean_f1"] * 100
        m0_pct = ""
        if "mem0_f1_method" in agg and cat_name in agg["mem0_f1_method"]["by_category"]:
            m0_cat = agg["mem0_f1_method"]["by_category"][cat_name]
            m0_pct = f" / {m0_cat['mean_f1']*100:5.1f}% / B1={m0_cat['mean_bleu1']*100:4.1f}%"
        acc_str = f", accuracy={cat_data['llm_accuracy']*100:.1f}%" if cat_data.get("llm_accuracy") else ""
        print(f"  {cat_name:15s}: F1={f1_pct:5.1f}%{m0_pct} (n={cat_data['count']}){acc_str}")

    print(f"\nComparison with baselines:")
    print(f"  FadeMem multi-hop F1: {agg['comparison']['vs_fademem']['fademem_multihop_f1']}")
    print(f"  Mem0 multi-hop F1:    {agg['comparison']['vs_mem0']['mem0_multihop_f1']}")
    print(f"  Ours overall F1:      {agg['overall']['mean_f1']*100:.2f}")

    print(f"\nTotal evaluation time: {total_time:.1f}s")

    # Save results
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump({
                "aggregate": agg,
                "per_question": all_results,
            }, f, indent=2, default=str)
        print(f"\nDetailed results saved to {output_path}")

    return agg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate memory systems on LoCoMo benchmark"
    )
    parser.add_argument(
        "--data", required=True,
        help="Path to locomo10.json"
    )
    parser.add_argument(
        "--adapter", default="cognitive_memory",
        choices=["cognitive_memory", "cognitive_memory_raw", "naive_rag", "full_context"],
        help="Which memory adapter to use"
    )
    parser.add_argument(
        "--model", default="gpt-4o-mini",
        help="LLM model for answer generation and judging"
    )
    parser.add_argument(
        "--use-judge", action="store_true",
        help="Enable LLM-as-a-judge evaluation (slower, costs more)"
    )
    parser.add_argument(
        "--output", default="results/locomo_results.json",
        help="Output path for detailed results JSON"
    )
    parser.add_argument(
        "--max-conversations", type=int, default=None,
        help="Limit number of conversations to evaluate (for testing)"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-conversation output"
    )
    parser.add_argument(
        "--answer-temperature", type=float, default=0,
        help="Temperature for answer generation (official LoCoMo=0, FadeMem=0.7)"
    )
    parser.add_argument(
        "--answer-max-tokens", type=int, default=32,
        help="Max tokens for answer generation (official LoCoMo=32, FadeMem=500)"
    )
    parser.add_argument(
        "--prompt-mode", default="official",
        choices=["official", "tuned", "mem0"],
        help="Answer prompt mode: official (LoCoMo standard), tuned (our optimized), mem0 (Mem0's 7-step CoT)"
    )
    parser.add_argument(
        "--dual-perspective", action="store_true",
        help="Ingest each session twice (once per speaker as 'user'). Matches Mem0's dual-perspective ingestion."
    )
    parser.add_argument(
        "--top-k", type=int, default=None,
        help="Override retrieval top_k (default: 20 for standard, 60 for mem0 mode)"
    )
    parser.add_argument(
        "--deep-recall", action="store_true",
        help="Enable deep recall: include superseded/consolidated originals in retrieval (Section 3.8)"
    )
    parser.add_argument(
        "--custom-extraction-instructions", type=str, default=None,
        help="Path to a text file with custom extraction instructions (prepended to extraction prompt)"
    )
    parser.add_argument(
        "--rerank", action="store_true",
        help="Enable LLM re-ranking: retrieve top_k*factor candidates, re-rank by relevance, keep top_k"
    )
    parser.add_argument(
        "--rerank-factor", type=int, default=2,
        help="Re-rank oversampling factor (default: 2, so retrieve 2x top_k then re-rank to top_k)"
    )
    parser.add_argument(
        "--start-from", type=int, default=0,
        help="Skip conversations before this index (for resuming interrupted runs)"
    )
    parser.add_argument(
        "--extraction-mode", default="semantic",
        choices=["raw", "semantic", "hybrid"],
        help="SDK extraction mode: raw (verbatim turns), semantic (LLM facts), hybrid (both)"
    )

    args = parser.parse_args()

    # Handle max_tokens: Mem0 doesn't set it (API default), others use specified value
    max_tokens = args.answer_max_tokens
    if args.prompt_mode == "mem0" and args.answer_max_tokens == 32:
        max_tokens = None  # Mem0 doesn't limit tokens

    # Load custom extraction instructions from file if provided
    custom_extraction_instructions = None
    if args.custom_extraction_instructions:
        with open(args.custom_extraction_instructions) as f:
            custom_extraction_instructions = f.read().strip()
        print(f"Loaded custom extraction instructions from {args.custom_extraction_instructions}")

    run_evaluation(
        data_path=args.data,
        adapter_name=args.adapter,
        model=args.model,
        use_judge=args.use_judge,
        output_path=args.output,
        max_conversations=args.max_conversations,
        verbose=not args.quiet,
        answer_temperature=args.answer_temperature,
        answer_max_tokens=max_tokens,
        prompt_mode=args.prompt_mode,
        dual_perspective=args.dual_perspective,
        top_k=args.top_k,
        deep_recall=args.deep_recall,
        custom_extraction_instructions=custom_extraction_instructions,
        rerank=args.rerank,
        rerank_factor=args.rerank_factor,
        start_from=args.start_from,
        extraction_mode=args.extraction_mode,
    )


if __name__ == "__main__":
    main()
