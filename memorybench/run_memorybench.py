#!/usr/bin/env python3
"""
MemoryBench harness for cognitive-memory.

Two modes:
1. Standalone: Downloads from HuggingFace, evaluates Locomo subsets directly
2. Framework: Plugs into the MemoryBench-code repo for full 27-dataset evaluation

Standalone mode (macOS-compatible, uses OpenAI):
    python run_memorybench.py --standalone --datasets Locomo-0 --output results/

Framework mode (requires Linux + vLLM):
    See memorybench/SETUP.md for vLLM setup instructions.
    cd memorybench/repo
    python -m src.predict --memory_system cognitive_memory --domain Open-Domain

Note: MemoryBench's official protocol requires vLLM + Qwen3-8B which needs
Linux + NVIDIA GPU. Standalone mode uses OpenAI API as a practical alternative.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.memory_adapter import (
    CognitiveMemoryAdapter,
    HybridMemoryAdapter,
    NaiveRAGAdapter,
    QueryResult,
)
from shared.metrics import token_f1, normalize_answer

REPO_DIR = Path(__file__).parent / "repo"


# ---------------------------------------------------------------------------
# LoCoMo F1 scoring (matches MemoryBench's Locomo evaluation)
# ---------------------------------------------------------------------------

def memorybench_locomo_f1(prediction: str, info: dict) -> dict:
    """
    Score a LoCoMo prediction using MemoryBench's F1 method.
    Handles category-specific logic (adversarial = category 5).
    """
    answer = info.get("golden_answer", "")
    category = info.get("category", 0)

    if category == 5:
        # Adversarial: correct if model says "not mentioned" or similar
        pred_lower = prediction.lower()
        correct = any(phrase in pred_lower for phrase in [
            "not mentioned", "no information", "unknown", "not available",
            "cannot determine", "don't have", "isn't mentioned",
        ])
        return {"f1": 1.0 if correct else 0.0, "category": category}

    # Standard F1
    result = token_f1(prediction, str(answer))
    result["category"] = category
    return result


# ---------------------------------------------------------------------------
# Standalone evaluation (HuggingFace data)
# ---------------------------------------------------------------------------

def load_from_huggingface(dataset_name: str) -> dict:
    """Load a MemoryBench dataset from HuggingFace."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("Install datasets: pip install datasets")
        sys.exit(1)

    print(f"Loading {dataset_name} from THUIR/MemoryBench...")
    ds = load_dataset("THUIR/MemoryBench", dataset_name)
    return ds


def run_standalone_locomo(
    dataset_name: str,
    adapter,
    output_dir: str,
    answer_model: str = "gpt-4o-mini",
    top_k: int = 20,
    verbose: bool = True,
) -> dict:
    """
    Run standalone evaluation on a MemoryBench Locomo dataset.
    Downloads from HuggingFace, ingests conversations, answers questions.
    """
    ds = load_from_huggingface(dataset_name)

    # MemoryBench has train (dialogs) and test splits
    test_data = ds["test"]
    train_data = ds.get("train", [])

    print(f"  Test questions: {len(test_data)}")
    print(f"  Train dialogs: {len(train_data) if train_data else 0}")

    from openai import OpenAI
    client = OpenAI()

    results = []
    total_start = time.time()

    for idx, item in enumerate(test_data):
        test_idx = item.get("test_idx", idx)
        info = item.get("info", {})
        if isinstance(info, str):
            info = json.loads(info)

        # Get input prompt
        question = item.get("input_prompt", "")
        if not question and "input_chat_messages" in item:
            msgs = item["input_chat_messages"]
            if isinstance(msgs, str):
                msgs = json.loads(msgs)
            question = msgs[-1]["content"] if msgs else ""

        if not question:
            continue

        # Ingest conversation dialogs for this question's context
        # In MemoryBench, the dialog field contains the conversation history
        dialog = item.get("dialog", [])
        if isinstance(dialog, str):
            dialog = json.loads(dialog)

        if dialog:
            adapter.reset()
            # Convert dialog messages to session format
            turns = []
            for msg in dialog:
                if isinstance(msg, dict):
                    speaker = "User" if msg.get("role") == "user" else "Assistant"
                    turns.append({
                        "speaker": speaker,
                        "text": msg.get("content", ""),
                        "dia_id": f"d{test_idx}",
                    })

            if turns:
                adapter.ingest_session(
                    turns=turns,
                    session_id=f"dialog_{test_idx}",
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    speaker_a="User",
                    speaker_b="Assistant",
                )

        # Query
        query_result = adapter.query(question=question, top_k=top_k)

        # Generate answer
        memories_text = "\n".join(
            f"{i+1}. {mem.content}" for i, mem in enumerate(query_result.retrieved_memories)
        ) if query_result.retrieved_memories else "(No memories)"

        prompt = (
            f"Context:\n{memories_text}\n\n"
            f"Question: {question}\n\n"
            f"Answer concisely:"
        )

        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=answer_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=200,
                )
                prediction = resp.choices[0].message.content.strip()
                break
            except Exception:
                time.sleep(2 ** attempt)
                prediction = "Error"

        # Score
        score = memorybench_locomo_f1(prediction, info)

        result = {
            "test_idx": test_idx,
            "question": question[:200],
            "ground_truth": str(info.get("golden_answer", "")),
            "prediction": prediction,
            "f1": score["f1"],
            "category": score.get("category", 0),
            "num_retrieved": len(query_result.retrieved_memories),
        }
        results.append(result)

        if verbose and (idx + 1) % 5 == 0:
            avg_f1 = sum(r["f1"] for r in results) / len(results)
            print(f"  [{idx+1}/{len(test_data)}] Running F1: {avg_f1*100:.1f}%")

    total_time = time.time() - total_start

    # Aggregate
    if results:
        avg_f1 = sum(r["f1"] for r in results) / len(results)
        by_cat = {}
        for r in results:
            cat = r["category"]
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(r["f1"])

        agg = {
            "dataset": dataset_name,
            "overall_f1": avg_f1,
            "num_questions": len(results),
            "by_category": {
                cat: {"mean_f1": sum(scores)/len(scores), "count": len(scores)}
                for cat, scores in by_cat.items()
            },
            "total_time_s": total_time,
        }
    else:
        agg = {"dataset": dataset_name, "overall_f1": 0, "num_questions": 0}

    # Save
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{dataset_name}_results.json")
    with open(output_path, "w") as f:
        json.dump({"aggregate": agg, "per_question": results}, f, indent=2, default=str)

    print(f"\n  {dataset_name}: F1={agg['overall_f1']*100:.1f}% ({len(results)} questions, {total_time:.0f}s)")
    print(f"  Saved: {output_path}")

    return agg


# ---------------------------------------------------------------------------
# DialSim evaluation (TV show dialog Q&A)
# ---------------------------------------------------------------------------

def parse_dialsim_transcript(corpus_path: str) -> list:
    """Parse a DialSim transcript file into sessions."""
    sessions = []
    current_session = None
    current_turns = []
    current_date = ""

    with open(corpus_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[Date:"):
                # Save previous session
                if current_turns:
                    sessions.append({
                        "session_id": f"session_{len(sessions)+1}",
                        "date": current_date,
                        "turns": current_turns,
                    })
                # Parse new session header: [Date: September 22, 1994, Session #1]
                parts = line.strip("[]").split(", Session #")
                current_date = parts[0].replace("Date: ", "") if parts else ""
                current_turns = []
            elif ": " in line:
                # Speaker: text
                speaker, _, text = line.partition(": ")
                current_turns.append({
                    "speaker": speaker.strip(),
                    "text": text.strip(),
                })

    # Save last session
    if current_turns:
        sessions.append({
            "session_id": f"session_{len(sessions)+1}",
            "date": current_date,
            "turns": current_turns,
        })

    return sessions


def run_standalone_dialsim(
    dataset_name: str,
    adapter,
    output_dir: str,
    answer_model: str = "gpt-4o-mini",
    top_k: int = 20,
    verbose: bool = True,
) -> dict:
    """Run evaluation on a DialSim dataset (Friends, Big Bang, The Office)."""
    # Map dataset name to corpus file
    show_map = {
        "DialSim-friends": "dialsim_corpus_friends.txt",
        "DialSim-bigbang": "dialsim_corpus_bigbang.txt",
        "DialSim-theoffice": "dialsim_corpus_theoffice.txt",
    }
    corpus_file = show_map.get(dataset_name)
    if not corpus_file:
        raise ValueError(f"Unknown DialSim dataset: {dataset_name}")

    corpus_path = REPO_DIR / "raw" / "DialSim" / corpus_file
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    # Parse and ingest transcript
    print(f"  Parsing transcript: {corpus_file}")
    sessions = parse_dialsim_transcript(str(corpus_path))
    print(f"  Found {len(sessions)} sessions")

    adapter.reset()
    for i, session in enumerate(sessions):
        turns = [{"speaker": t["speaker"], "text": t["text"], "dia_id": f"ds{i}"} for t in session["turns"]]
        adapter.ingest_session(
            turns=turns,
            session_id=session["session_id"],
            timestamp=session["date"],
            speaker_a=session["turns"][0]["speaker"] if session["turns"] else "Speaker",
            speaker_b="Other",
        )
        if verbose and (i + 1) % 50 == 0:
            print(f"  Ingested {i+1}/{len(sessions)} sessions")
    print(f"  Ingestion complete ({len(sessions)} sessions)")

    # Load test questions from HuggingFace
    ds = load_from_huggingface(dataset_name)
    test_data = ds["test"]
    print(f"  Test questions: {len(test_data)}")

    from openai import OpenAI
    client = OpenAI()

    results = []
    total_start = time.time()

    for idx, item in enumerate(test_data):
        test_idx = item.get("test_idx", idx)
        info = item.get("info", {})
        if isinstance(info, str):
            info = json.loads(info)

        # Extract question from input_prompt
        input_prompt = item.get("input_prompt", "")
        # The question is embedded in the prompt after [Question]
        question_text = input_prompt
        if "[Question]" in input_prompt:
            question_text = input_prompt.split("[Question]")[-1].strip()

        golden_answer = info.get("golden_answer", "")

        # Query memory
        query_result = adapter.query(question=question_text, top_k=top_k)

        memories_text = "\n".join(
            f"{i+1}. {mem.content}" for i, mem in enumerate(query_result.retrieved_memories)
        ) if query_result.retrieved_memories else "(No memories)"

        prompt = (
            f"Based on the dialog history below, answer the question concisely "
            f"with just the answer (a name, place, or short phrase).\n\n"
            f"Dialog history:\n{memories_text}\n\n"
            f"Question: {question_text}\n\n"
            f"Answer (just the answer, nothing else):"
        )

        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=answer_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=50,
                )
                prediction = resp.choices[0].message.content.strip()
                break
            except Exception:
                time.sleep(2 ** attempt)
                prediction = "Error"

        # Score: flexible match (case-insensitive, normalized, token-set overlap)
        pred_norm = normalize_answer(prediction)
        gold_norm = normalize_answer(str(golden_answer))
        # Substring containment
        correct = gold_norm in pred_norm or pred_norm in gold_norm
        # Token-set match: all gold tokens present in prediction (handles word order)
        if not correct:
            gold_tokens = set(gold_norm.split())
            pred_tokens = set(pred_norm.split())
            if gold_tokens and gold_tokens.issubset(pred_tokens):
                correct = True
        # Number normalization: "phase 1" vs "phase one" etc.
        if not correct:
            num_words = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                         "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
            def normalize_numbers(s):
                for word, digit in num_words.items():
                    s = s.replace(word, digit)
                return s
            if normalize_numbers(gold_norm) in normalize_numbers(pred_norm) or \
               normalize_numbers(pred_norm) in normalize_numbers(gold_norm):
                correct = True

        result = {
            "test_idx": test_idx,
            "question": question_text[:200],
            "ground_truth": str(golden_answer),
            "prediction": prediction,
            "correct": correct,
            "num_retrieved": len(query_result.retrieved_memories),
        }
        results.append(result)

        if verbose and (idx + 1) % 5 == 0:
            acc = sum(1 for r in results if r["correct"]) / len(results)
            print(f"  [{idx+1}/{len(test_data)}] Running accuracy: {acc*100:.1f}%")

    total_time = time.time() - total_start

    # Aggregate
    if results:
        accuracy = sum(1 for r in results if r["correct"]) / len(results)
        agg = {
            "dataset": dataset_name,
            "overall_accuracy": accuracy,
            "overall_f1": accuracy,  # For unified summary
            "num_questions": len(results),
            "metric": "accuracy",
            "total_time_s": total_time,
        }
    else:
        agg = {"dataset": dataset_name, "overall_accuracy": 0, "overall_f1": 0, "num_questions": 0}

    # Save
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{dataset_name}_results.json")
    with open(output_path, "w") as f:
        json.dump({"aggregate": agg, "per_question": results}, f, indent=2, default=str)

    metric_val = agg.get("overall_accuracy", 0)
    print(f"\n  {dataset_name}: Accuracy={metric_val*100:.1f}% ({len(results)} questions, {total_time:.0f}s)")
    print(f"  Saved: {output_path}")

    return agg


# ---------------------------------------------------------------------------
# NFCats evaluation (short text categorization)
# ---------------------------------------------------------------------------

def run_standalone_nfcats(
    adapter,
    output_dir: str,
    answer_model: str = "gpt-4o-mini",
    top_k: int = 20,
    verbose: bool = True,
) -> dict:
    """Run evaluation on NFCats dataset."""
    ds = load_from_huggingface("NFCats")
    test_data = ds["test"]

    print(f"  Test questions: {len(test_data)}")

    from openai import OpenAI
    client = OpenAI()

    results = []
    total_start = time.time()

    for idx, item in enumerate(test_data):
        test_idx = item.get("test_idx", idx)
        info = item.get("info", {})
        if isinstance(info, str):
            info = json.loads(info)

        input_prompt = item.get("input_prompt", "")
        golden_answer = info.get("golden_answer", "")

        # NFCats is short-short: no dialog to ingest
        # Just answer using the prompt directly
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=answer_model,
                    messages=[{"role": "user", "content": input_prompt}],
                    temperature=0,
                    max_tokens=200,
                )
                prediction = resp.choices[0].message.content.strip()
                break
            except Exception:
                time.sleep(2 ** attempt)
                prediction = "Error"

        # Score: flexible match
        pred_norm = normalize_answer(prediction)
        gold_norm = normalize_answer(str(golden_answer))
        correct = gold_norm in pred_norm or pred_norm in gold_norm
        if not correct:
            gold_tokens = set(gold_norm.split())
            pred_tokens = set(pred_norm.split())
            if gold_tokens and gold_tokens.issubset(pred_tokens):
                correct = True
        if not correct:
            num_words = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                         "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
            def normalize_numbers(s):
                for word, digit in num_words.items():
                    s = s.replace(word, digit)
                return s
            if normalize_numbers(gold_norm) in normalize_numbers(pred_norm) or \
               normalize_numbers(pred_norm) in normalize_numbers(gold_norm):
                correct = True

        results.append({
            "test_idx": test_idx,
            "question": input_prompt[:200],
            "ground_truth": str(golden_answer),
            "prediction": prediction,
            "correct": correct,
        })

        if verbose and (idx + 1) % 10 == 0:
            acc = sum(1 for r in results if r["correct"]) / len(results)
            print(f"  [{idx+1}/{len(test_data)}] Running accuracy: {acc*100:.1f}%")

    total_time = time.time() - total_start
    accuracy = sum(1 for r in results if r["correct"]) / len(results) if results else 0

    agg = {
        "dataset": "NFCats",
        "overall_accuracy": accuracy,
        "overall_f1": accuracy,
        "num_questions": len(results),
        "metric": "accuracy",
        "total_time_s": total_time,
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "NFCats_results.json")
    with open(output_path, "w") as f:
        json.dump({"aggregate": agg, "per_question": results}, f, indent=2, default=str)

    print(f"\n  NFCats: Accuracy={accuracy*100:.1f}% ({len(results)} questions, {total_time:.0f}s)")
    print(f"  Saved: {output_path}")

    return agg


DIALSIM_DATASETS = {"DialSim-friends", "DialSim-bigbang", "DialSim-theoffice"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MemoryBench evaluation for cognitive-memory")
    parser.add_argument("--standalone", action="store_true",
                        help="Run standalone mode (downloads from HuggingFace, uses OpenAI)")
    parser.add_argument("--datasets", nargs="+",
                        default=["Locomo-0"],
                        help="Dataset names to evaluate (e.g., Locomo-0 Locomo-1)")
    parser.add_argument("--adapter", default="cognitive_memory",
                        choices=["cognitive_memory", "hybrid", "naive_rag"])
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--deep-recall", action="store_true")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--no-extract", action="store_true",
                        help="Hybrid adapter only: skip LLM extraction, use raw turns + BM25 only")
    parser.add_argument("--extraction-mode", default="semantic",
                        choices=["raw", "semantic", "hybrid"],
                        help="SDK extraction mode: raw (verbatim turns), semantic (LLM facts), hybrid (both)")
    parser.add_argument("--output", default="results/memorybench/")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    if not args.standalone:
        print("For framework mode, use the MemoryBench repo directly.")
        print("See memorybench/SETUP.md for instructions.")
        print("Use --standalone for HuggingFace-based evaluation.")
        sys.exit(0)

    # Build adapter
    if args.adapter == "cognitive_memory":
        adapter = CognitiveMemoryAdapter(
            llm_model=args.model,
            deep_recall=args.deep_recall,
            rerank=args.rerank,
            extraction_mode=args.extraction_mode,
        )
    elif args.adapter == "hybrid":
        adapter = HybridMemoryAdapter(
            llm_model=args.model,
            deep_recall=args.deep_recall,
            rerank=args.rerank,
            extract=not args.no_extract,
        )
    else:
        adapter = NaiveRAGAdapter(llm_model=args.model)

    print(f"MemoryBench Standalone Evaluation")
    print(f"Adapter: {args.adapter}, Model: {args.model}")
    print(f"Top-k: {args.top_k}, Deep recall: {args.deep_recall}, Rerank: {args.rerank}")
    print(f"Datasets: {args.datasets}")

    all_results = {}
    for dataset_name in args.datasets:
        print(f"\n{'='*60}")
        print(f"Evaluating {dataset_name}")
        print(f"{'='*60}")

        try:
            if dataset_name in DIALSIM_DATASETS:
                agg = run_standalone_dialsim(
                    dataset_name=dataset_name,
                    adapter=adapter,
                    output_dir=args.output,
                    answer_model=args.model,
                    top_k=args.top_k,
                    verbose=not args.quiet,
                )
            elif dataset_name == "NFCats":
                agg = run_standalone_nfcats(
                    adapter=adapter,
                    output_dir=args.output,
                    answer_model=args.model,
                    top_k=args.top_k,
                    verbose=not args.quiet,
                )
            else:
                agg = run_standalone_locomo(
                    dataset_name=dataset_name,
                    adapter=adapter,
                    output_dir=args.output,
                    answer_model=args.model,
                    top_k=args.top_k,
                    verbose=not args.quiet,
                )
            all_results[dataset_name] = agg
        except Exception as e:
            print(f"  Error on {dataset_name}: {e}")
            import traceback; traceback.print_exc()
            all_results[dataset_name] = {"error": str(e)}

    # Summary
    print(f"\n{'='*60}")
    print("MEMORYBENCH SUMMARY")
    print(f"{'='*60}")
    for name, agg in all_results.items():
        if "error" in agg:
            print(f"  {name}: ERROR - {agg['error']}")
        else:
            metric = agg.get("metric", "f1")
            val = agg.get("overall_accuracy", agg.get("overall_f1", 0))
            label = "Acc" if metric == "accuracy" else "F1"
            print(f"  {name}: {label}={val*100:.1f}% (n={agg['num_questions']})")


if __name__ == "__main__":
    main()
