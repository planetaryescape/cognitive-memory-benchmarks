#!/usr/bin/env python3
"""
LongMemEval (ICLR 2025) harness for cognitive-memory.

500 questions, 6 types, 53 haystack sessions per question,
binary GPT-4o judge scoring. SOTA: ENGRAM 71.40%.

Usage:
    python run_longmemeval.py --data data/longmemeval_s_cleaned.json
    python run_longmemeval.py --data data/longmemeval_s_cleaned.json --deep-recall --rerank
"""

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

# Global lock for thread-safe memory store access
_ingest_lock = threading.Lock()


def _patch_adapter_for_threading(adapter):
    """Monkey-patch the InMemoryAdapter to be thread-safe during iteration.
    The issue: search_similar iterates self.hot.values() while create() modifies self.hot,
    causing RuntimeError: dictionary changed size during iteration."""
    if not hasattr(adapter, 'memory'):
        return
    async_mem = getattr(adapter.memory, '_async', None)
    if async_mem is None:
        return
    inner_adapter = getattr(async_mem, '_adapter', None)
    if inner_adapter is None:
        return

    # Patch search_similar to use a snapshot of values
    original_search = inner_adapter.search_similar.__func__

    async def safe_search_similar(
        self,
        query_embedding,
        top_k=10,
        include_superseded=False,
        include_cold=False,
        include_stubs=False,
        user_id=None,
    ):
        from cognitive_memory.embeddings import cosine_similarity
        results = []
        # Take snapshot to avoid dict-changed-size-during-iteration
        candidates = list(self.hot.values())
        if include_cold:
            candidates.extend(list(self.cold.values()))
        if include_stubs:
            candidates.extend(list(self.stubs.values()))
        for mem in candidates:
            if mem.embedding is None:
                continue
            if mem.is_superseded and not include_superseded:
                continue
            if mem.is_stub and not include_stubs:
                continue
            if user_id is not None and mem.user_id != user_id:
                continue
            sim = cosine_similarity(query_embedding, mem.embedding)
            results.append((mem, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    import types
    inner_adapter.search_similar = types.MethodType(safe_search_similar, inner_adapter)

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.memory_adapter import (
    CognitiveMemoryAdapter,
    NaiveRAGAdapter,
    FullContextAdapter,
    QueryResult,
)
from shared.adapter import _parse_timestamp


# ---------------------------------------------------------------------------
# Judge prompts (verbatim from xiaowu0162/LongMemEval)
# ---------------------------------------------------------------------------

JUDGE_MODEL = "gpt-4o-2024-08-06"

JUDGE_PROMPTS = {
    "single-session-user": (
        "I will give you a question, a correct answer, and a response from a model. "
        "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
        "If the response is equivalent to the correct answer or contains all the intermediate "
        "steps to get the correct answer, you should also answer yes. If the response only "
        "contains a subset of the information required by the answer, answer no. \n\n"
        "Question: {question}\n\nCorrect Answer: {answer}\n\n"
        "Model Response: {response}\n\n"
        "Is the model response correct? Answer yes or no only."
    ),
    "single-session-assistant": (
        "I will give you a question, a correct answer, and a response from a model. "
        "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
        "If the response is equivalent to the correct answer or contains all the intermediate "
        "steps to get the correct answer, you should also answer yes. If the response only "
        "contains a subset of the information required by the answer, answer no. \n\n"
        "Question: {question}\n\nCorrect Answer: {answer}\n\n"
        "Model Response: {response}\n\n"
        "Is the model response correct? Answer yes or no only."
    ),
    "multi-session": (
        "I will give you a question, a correct answer, and a response from a model. "
        "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
        "If the response is equivalent to the correct answer or contains all the intermediate "
        "steps to get the correct answer, you should also answer yes. If the response only "
        "contains a subset of the information required by the answer, answer no. \n\n"
        "Question: {question}\n\nCorrect Answer: {answer}\n\n"
        "Model Response: {response}\n\n"
        "Is the model response correct? Answer yes or no only."
    ),
    "temporal-reasoning": (
        "I will give you a question, a correct answer, and a response from a model. "
        "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
        "If the response is equivalent to the correct answer or contains all the intermediate "
        "steps to get the correct answer, you should also answer yes. If the response only "
        "contains a subset of the information required by the answer, answer no. "
        "In addition, do not penalize off-by-one errors for the number of days. "
        "If the question asks for the number of days/weeks/months, etc., and the model makes "
        "off-by-one errors (e.g., predicting 19 days when the answer is 18), the model's "
        "response is still correct. \n\n"
        "Question: {question}\n\nCorrect Answer: {answer}\n\n"
        "Model Response: {response}\n\n"
        "Is the model response correct? Answer yes or no only."
    ),
    "knowledge-update": (
        "I will give you a question, a correct answer, and a response from a model. "
        "Please answer yes if the response contains the correct answer. Otherwise, answer no. "
        "If the response contains some previous information along with an updated answer, "
        "the response should be considered as correct as long as the updated answer is the "
        "required answer.\n\n"
        "Question: {question}\n\nCorrect Answer: {answer}\n\n"
        "Model Response: {response}\n\n"
        "Is the model response correct? Answer yes or no only."
    ),
    "single-session-preference": (
        "I will give you a question, a rubric for desired personalized response, and a response "
        "from a model. Please answer yes if the response satisfies the desired response. "
        "Otherwise, answer no. The model does not need to reflect all the points in the rubric. "
        "The response is correct as long as it recalls and utilizes the user's personal "
        "information correctly.\n\n"
        "Question: {question}\n\nRubric: {answer}\n\n"
        "Model Response: {response}\n\n"
        "Is the model response correct? Answer yes or no only."
    ),
    "abstention": (
        "I will give you an unanswerable question, an explanation, and a response from a model. "
        "Please answer yes if the model correctly identifies the question as unanswerable. "
        "The model could say that the information is incomplete, or some other information is "
        "given but the asked information is not.\n\n"
        "Question: {question}\n\nExplanation: {answer}\n\n"
        "Model Response: {response}\n\n"
        "Does the model correctly identify the question as unanswerable? Answer yes or no only."
    ),
}

ANSWER_PROMPT = """You are a personal assistant with access to memories from past conversations.

Below are relevant memories from the user's conversation history:

{memories}

Based on the above memories, answer the following question. Be concise and specific.
If the memories don't contain enough information to answer, say "I don't have that information."
If the question asks about timing or dates, use the memory timestamps to calculate.

Question: {question}

Answer:"""

QUESTION_TYPES = [
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "multi-session",
    "temporal-reasoning",
    "knowledge-update",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_longmemeval(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)

    print(f"Loaded {len(data)} questions from {path}")

    from collections import Counter
    types = Counter(d["question_type"] for d in data)
    for qt in QUESTION_TYPES:
        print(f"  {qt}: {types.get(qt, 0)}")
    abs_count = sum(1 for d in data if "_abs" in d["question_id"])
    print(f"  abstention: {abs_count}")

    return data


# ---------------------------------------------------------------------------
# Session conversion
# ---------------------------------------------------------------------------

def convert_sessions(haystack_sessions, haystack_dates):
    """Convert LongMemEval sessions to adapter format."""
    converted = []
    for idx, (session, date_str) in enumerate(zip(haystack_sessions, haystack_dates)):
        turns = []
        for msg_idx, msg in enumerate(session):
            speaker = "User" if msg["role"] == "user" else "Assistant"
            # Truncate long messages to stay within embedding model token limits
            text = msg["content"]
            if len(text) > 6000:
                text = text[:6000]
            turns.append({
                "speaker": speaker,
                "text": text,
                "dia_id": f"s{idx}_m{msg_idx}",
            })
        converted.append({
            "session_id": f"session_{idx}",
            "timestamp": _parse_longmemeval_date(date_str),
            "turns": turns,
            "speaker_a": "User",
            "speaker_b": "Assistant",
        })
    return converted


def _parse_longmemeval_date(date_str: str) -> str:
    """Parse '2023/05/20 (Sat) 02:21' to ISO string."""
    try:
        cleaned = date_str.split("(")[0].strip() + " " + date_str.split(")")[-1].strip()
        dt = datetime.strptime(cleaned.strip(), "%Y/%m/%d %H:%M")
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, IndexError):
        return date_str


# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------

def generate_answer(question, query_result, client=None, model="gpt-4o-mini"):
    if client is None:
        from openai import OpenAI
        client = OpenAI()

    if not query_result.retrieved_memories:
        memories_text = "(No relevant memories found)"
    else:
        parts = []
        for i, mem in enumerate(query_result.retrieved_memories, 1):
            ts = f" [{mem.created_at}]" if mem.created_at else ""
            parts.append(f"{i}.{ts} {mem.content}")
        memories_text = "\n".join(parts)

    prompt = ANSWER_PROMPT.format(memories=memories_text, question=question)

    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e).lower()
            if attempt < 4 and any(k in err_str for k in ("500", "502", "503", "529", "rate_limit", "timeout")):
                time.sleep(min(60, 2 ** attempt * 2))
                continue
            raise


# ---------------------------------------------------------------------------
# GPT-4o Judge
# ---------------------------------------------------------------------------

def judge_answer(question, answer, response, question_type, question_id, client=None):
    if client is None:
        from openai import OpenAI
        client = OpenAI()

    is_abstention = "_abs" in question_id
    if is_abstention:
        prompt_template = JUDGE_PROMPTS["abstention"]
    else:
        prompt_template = JUDGE_PROMPTS.get(question_type, JUDGE_PROMPTS["single-session-user"])

    prompt = prompt_template.format(question=question, answer=answer, response=response)

    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10,
            )
            raw = resp.choices[0].message.content.strip()
            correct = "yes" in raw.lower()
            return {"correct": correct, "model": JUDGE_MODEL, "raw": raw}
        except Exception as e:
            err_str = str(e).lower()
            if attempt < 4 and any(k in err_str for k in ("500", "502", "503", "529", "rate_limit", "timeout")):
                time.sleep(min(60, 2 ** attempt * 2))
                continue
            raise


# ---------------------------------------------------------------------------
# Per-question evaluation
# ---------------------------------------------------------------------------

def _ingest_one_session(adapter, session):
    """Ingest a single session — used as ThreadPoolExecutor target.
    Retries on dict contention errors from concurrent access."""
    for attempt in range(5):
        try:
            adapter.ingest_session(
                turns=session["turns"],
                session_id=session["session_id"],
                timestamp=session["timestamp"],
                speaker_a=session["speaker_a"],
                speaker_b=session["speaker_b"],
            )
            return
        except RuntimeError as e:
            if "dictionary changed size" in str(e) and attempt < 4:
                time.sleep(0.1 * (2 ** attempt))  # 0.1, 0.2, 0.4, 0.8s
                continue
            raise


def evaluate_question(item, adapter, question_index, client=None, answer_model="gpt-4o-mini",
                       top_k=20, verbose=True, parallel_ingest=False, max_workers=53):
    question_id = item["question_id"]
    question_type = item["question_type"]
    question = item["question"]
    answer = item["answer"]
    question_date = item.get("question_date", "")

    adapter.reset()

    sessions = convert_sessions(item["haystack_sessions"], item["haystack_dates"])

    ingest_start = time.time()
    if parallel_ingest and len(sessions) > 1:
        _patch_adapter_for_threading(adapter)

        # Disable tick during parallel ingestion to avoid race conditions
        if hasattr(adapter, 'memory') and hasattr(adapter.memory, '_config'):
            old_tick = getattr(adapter.memory._config, 'run_maintenance_during_ingestion', True)
            adapter.memory._config.run_maintenance_during_ingestion = False

        # monkey-patched adapter handles dict contention via list snapshot
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_ingest_one_session, adapter, s): i for i, s in enumerate(sessions)}
            succeeded = 0
            failed = 0
            for future in as_completed(futures):
                try:
                    future.result()
                    succeeded += 1
                except Exception:
                    failed += 1
            if failed:
                print(f"  WARNING: {failed}/{len(sessions)} sessions failed ingestion (retries exhausted)")

        # Restore tick setting and run maintenance once
        if hasattr(adapter, 'memory') and hasattr(adapter.memory, '_config'):
            adapter.memory._config.run_maintenance_during_ingestion = old_tick
        if hasattr(adapter, 'memory') and hasattr(adapter.memory, 'tick'):
            adapter.memory.tick()
    else:
        for session in sessions:
            adapter.ingest_session(
                turns=session["turns"],
                session_id=session["session_id"],
                timestamp=session["timestamp"],
                speaker_a=session["speaker_a"],
                speaker_b=session["speaker_b"],
            )
    ingest_time = time.time() - ingest_start

    query_ts = _parse_longmemeval_date(question_date) if question_date else None
    query_result = adapter.query(question=question, timestamp=query_ts, top_k=top_k)

    prediction = generate_answer(question=question, query_result=query_result, client=client, model=answer_model)

    judge_result = judge_answer(
        question=question, answer=answer, response=prediction,
        question_type=question_type, question_id=question_id, client=client,
    )

    result = {
        "question_id": question_id,
        "question_type": question_type,
        "question": question,
        "ground_truth": answer,
        "prediction": prediction,
        "correct": judge_result["correct"],
        "judge_model": judge_result["model"],
        "judge_raw": judge_result["raw"],
        "is_abstention": "_abs" in question_id,
        "num_sessions": len(sessions),
        "num_retrieved": len(query_result.retrieved_memories),
        "retrieval_time_ms": query_result.retrieval_time_ms,
        "ingest_time_s": ingest_time,
    }

    if verbose:
        status = "CORRECT" if result["correct"] else "WRONG"
        print(f"  [{question_index}] {question_type} | {status} | "
              f"ingest={ingest_time:.1f}s | retrieved={result['num_retrieved']}")

    return result


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def run_evaluation(
    data_path, adapter_name="cognitive_memory", model="gpt-4o-mini",
    output_path=None, verbose=True, top_k=20, deep_recall=False,
    rerank=False, rerank_factor=2, start_from=0, max_questions=None,
    max_workers=53, trial_kwargs=None,
):
    adapter_kwargs = {"llm_model": model}
    if adapter_name == "cognitive_memory":
        if deep_recall:
            adapter_kwargs["deep_recall"] = True
        if rerank:
            adapter_kwargs["rerank"] = True
            adapter_kwargs["rerank_factor"] = rerank_factor
        # Trial config kwargs (Phase 0c) — merged after explicit flags
        # so config_overrides can flip arbitrary CognitiveMemoryConfig
        # fields without conflicting with the harness's own knobs.
        if trial_kwargs:
            adapter_kwargs.update(trial_kwargs)
        adapter = CognitiveMemoryAdapter(**adapter_kwargs)
    elif adapter_name == "naive_rag":
        adapter = NaiveRAGAdapter(llm_model=model)
    elif adapter_name == "full_context":
        adapter = FullContextAdapter(llm_model=model)
    else:
        print(f"Unknown adapter: {adapter_name}")
        sys.exit(1)

    print(f"Adapter: {adapter_name}")
    print(f"Answer model: {model}")
    print(f"Judge model: {JUDGE_MODEL}")
    print(f"Top-k: {top_k}, Deep recall: {deep_recall}, Rerank: {rerank}")

    data = load_longmemeval(data_path)
    if max_questions:
        data = data[:max_questions]

    from openai import OpenAI
    client = OpenAI()

    # Load existing results for resume
    existing_results = []
    if start_from > 0 and output_path and os.path.exists(output_path):
        with open(output_path) as f:
            saved = json.load(f)
            existing_results = saved.get("per_question", [])
        print(f"Loaded {len(existing_results)} existing results for resume")

    all_results = list(existing_results)
    total_start = time.time()

    for i, item in enumerate(data):
        if i < start_from:
            continue

        if verbose:
            print(f"\nQuestion {i}/{len(data)} [{item['question_type']}]")

        result = evaluate_question(
            item=item, adapter=adapter, question_index=i,
            client=client, answer_model=model, top_k=top_k, verbose=verbose,
            parallel_ingest=(adapter_name == "cognitive_memory"),
            max_workers=max_workers,
        )
        all_results.append(result)

        # Save incrementally every 10 questions
        if output_path and (i + 1) % 10 == 0:
            _save_results(all_results, output_path, adapter_name, model, top_k,
                          deep_recall, rerank, rerank_factor, time.time() - total_start)

    total_time = time.time() - total_start

    agg = aggregate_longmemeval(all_results)
    agg["meta"] = {
        "adapter": adapter_name, "model": model, "judge_model": JUDGE_MODEL,
        "top_k": top_k, "deep_recall": deep_recall, "rerank": rerank,
        "total_questions": len(all_results),
        "total_time_seconds": total_time, "timestamp": datetime.now().isoformat(),
    }

    print(f"\n{'='*60}")
    print("LONGMEMEVAL RESULTS")
    print(f"{'='*60}")
    print(f"Adapter: {adapter_name}")
    print(f"Questions: {len(all_results)}")
    print(f"Task-averaged accuracy: {agg['task_averaged_accuracy']*100:.1f}%")
    print(f"Overall accuracy:       {agg['overall_accuracy']*100:.1f}%")
    if agg.get("abstention_accuracy") is not None:
        print(f"Abstention accuracy:    {agg['abstention_accuracy']*100:.1f}%")

    print(f"\nPer-type:")
    for qt in QUESTION_TYPES:
        if qt in agg["by_type"]:
            td = agg["by_type"][qt]
            print(f"  {qt:30s}: {td['accuracy']*100:5.1f}% (n={td['count']})")

    print(f"\nBaselines: ENGRAM=71.40%, Full-context=56.20%")
    print(f"Total time: {total_time/60:.1f}min")

    if output_path:
        _save_results(all_results, output_path, adapter_name, model, top_k,
                      deep_recall, rerank, rerank_factor, total_time, agg)
        print(f"Results: {output_path}")

    return agg


def _save_results(results, path, adapter, model, top_k, deep_recall, rerank, rerank_factor, elapsed, agg=None):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    output = {
        "per_question": results,
        "meta": {
            "adapter": adapter, "model": model, "top_k": top_k,
            "deep_recall": deep_recall, "rerank": rerank,
            "total_questions": len(results), "elapsed_seconds": elapsed,
        },
    }
    if agg:
        output["aggregate"] = agg
    with open(path, "w") as f:
        json.dump(output, f, indent=2, default=str)


def aggregate_longmemeval(results):
    if not results:
        return {"task_averaged_accuracy": 0, "overall_accuracy": 0, "by_type": {}}

    by_type = {}
    for qt in QUESTION_TYPES:
        type_results = [r for r in results if r["question_type"] == qt]
        if type_results:
            acc = sum(1 for r in type_results if r["correct"]) / len(type_results)
            by_type[qt] = {"accuracy": acc, "count": len(type_results)}

    task_avg = sum(d["accuracy"] for d in by_type.values()) / len(by_type) if by_type else 0.0
    overall = sum(1 for r in results if r["correct"]) / len(results)
    abs_results = [r for r in results if r.get("is_abstention")]
    abs_acc = (sum(1 for r in abs_results if r["correct"]) / len(abs_results)) if abs_results else None

    return {
        "task_averaged_accuracy": task_avg,
        "overall_accuracy": overall,
        "abstention_accuracy": abs_acc,
        "by_type": by_type,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LongMemEval (ICLR 2025) benchmark")
    parser.add_argument("--data", required=True, help="Path to longmemeval_s_cleaned.json")
    parser.add_argument("--adapter", default="cognitive_memory",
                        choices=["cognitive_memory", "naive_rag", "full_context"])
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--output", default="results/longmemeval_results.json")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--deep-recall", action="store_true")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--rerank-factor", type=int, default=2)
    parser.add_argument("--start-from", type=int, default=0)
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=53)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--config", default=None,
        help="Path to a tuning trial JSON config (Phase 0c). "
        "Overrides CognitiveMemoryConfig fields per-trial.",
    )
    parser.add_argument(
        "--surface", choices=["sdk", "daemon"], default=None,
        help="Override the trial config's surface. CLI flag wins.",
    )

    args = parser.parse_args()

    from shared.trial_config import load_trial_config
    trial_kwargs = load_trial_config(args.config)
    if args.surface is not None:
        trial_kwargs["surface"] = args.surface

    run_evaluation(
        data_path=args.data, adapter_name=args.adapter, model=args.model,
        output_path=args.output, verbose=not args.quiet, top_k=args.top_k,
        deep_recall=args.deep_recall, rerank=args.rerank,
        rerank_factor=args.rerank_factor, start_from=args.start_from,
        max_questions=args.max_questions,
        max_workers=args.max_workers,
        trial_kwargs=trial_kwargs,
    )


if __name__ == "__main__":
    main()
