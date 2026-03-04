"""
Evaluation metrics for memory benchmarks.

Implements:
- Partial-match F1 (standard LoCoMo metric)
- LLM-as-a-judge accuracy (binary CORRECT/WRONG)
- Storage efficiency metrics
- Retrieval quality metrics
"""

import re
import string
from collections import Counter
from typing import Optional

from nltk.stem import PorterStemmer

_stemmer = PorterStemmer()


# ---------------------------------------------------------------------------
# Token-level F1 (LoCoMo standard)
# ---------------------------------------------------------------------------

def normalize_answer(text: str) -> str:
    """Lowercase, strip articles/punctuation/whitespace. Matches official LoCoMo."""
    text = str(text) if text is not None else ""
    text = text.lower()
    # Remove commas (official LoCoMo step)
    text = text.replace(",", "")
    # Remove articles (including "and" per official LoCoMo)
    text = re.sub(r"\b(a|an|the|and)\b", " ", text)
    # Remove punctuation
    text = text.translate(str.maketrans("", "", string.punctuation))
    # Collapse whitespace
    text = " ".join(text.split())
    return text


def token_f1(prediction: str, ground_truth: str) -> dict:
    """
    Compute token-level precision, recall, and F1 with Porter stemming.
    Matches the official LoCoMo QA metric exactly.
    """
    pred_tokens = [_stemmer.stem(w) for w in normalize_answer(prediction).split()]
    gold_tokens = [_stemmer.stem(w) for w in normalize_answer(ground_truth).split()]

    if not gold_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0} if not pred_tokens else {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not pred_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_common = sum(common.values())

    if num_common == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    precision = num_common / len(pred_tokens)
    recall = num_common / len(gold_tokens)
    f1 = 2 * precision * recall / (precision + recall)

    return {"precision": precision, "recall": recall, "f1": f1}


def token_f1_mem0(prediction: str, ground_truth: str) -> dict:
    """
    Compute F1 using Mem0's exact method: set-based, no stemming, no article removal.
    Matches mem0ai/mem0/evaluation/utils.py simple_tokenize + set intersection.
    """
    def simple_tokenize(text):
        text = str(text) if text is not None else ""
        return text.lower().replace(".", " ").replace(",", " ").replace("!", " ").replace("?", " ").split()

    pred_tokens = set(simple_tokenize(prediction))
    ref_tokens = set(simple_tokenize(ground_truth))

    if not ref_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0} if not pred_tokens else {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not pred_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    common_tokens = pred_tokens & ref_tokens
    if not common_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    precision = len(common_tokens) / len(pred_tokens)
    recall = len(common_tokens) / len(ref_tokens)
    f1 = 2 * precision * recall / (precision + recall)

    return {"precision": precision, "recall": recall, "f1": f1}


def bleu1(prediction: str, ground_truth: str) -> float:
    """
    BLEU-1 (unigram) score matching Mem0's evaluation.
    Uses nltk word_tokenize + smoothing function 1.
    Mem0 uses: sentence_bleu([ref_tokens], pred_tokens, weights=(1,0,0,0), smoothing)
    """
    from nltk.tokenize import word_tokenize
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

    pred_text = str(prediction) if prediction is not None else ""
    ref_text = str(ground_truth) if ground_truth is not None else ""

    pred_tokens = word_tokenize(pred_text.lower())
    ref_tokens = word_tokenize(ref_text.lower())

    if not ref_tokens:
        return 1.0 if not pred_tokens else 0.0
    if not pred_tokens:
        return 0.0

    smoothing = SmoothingFunction().method1
    return sentence_bleu(
        [ref_tokens], pred_tokens,
        weights=(1, 0, 0, 0),
        smoothing_function=smoothing,
    )


def exact_match(prediction: str, ground_truth: str) -> bool:
    """Exact match after normalization."""
    return normalize_answer(prediction) == normalize_answer(ground_truth)


# ---------------------------------------------------------------------------
# LLM-as-a-Judge (used by Mem0, Hindsight, FadeMem)
# ---------------------------------------------------------------------------

LLM_JUDGE_PROMPT = """You are evaluating a question-answering system's response against a ground truth answer.

Question: {question}
Ground Truth Answer: {ground_truth}
System Answer: {prediction}

Does the system's answer correctly capture the key information from the ground truth?
Consider partial credit: if the system answer contains the essential facts from the ground truth,
even if worded differently, it should be marked CORRECT.

Respond with exactly one word: CORRECT or WRONG"""


def llm_judge(
    question: str,
    prediction: str,
    ground_truth: str,
    client=None,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    Use an LLM to judge if the prediction matches the ground truth.
    Returns {"correct": bool, "raw_response": str}
    """
    if client is None:
        from openai import OpenAI
        client = OpenAI()

    prompt = LLM_JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        prediction=prediction,
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=10,
    )

    raw = resp.choices[0].message.content.strip().upper()
    correct = "CORRECT" in raw

    return {"correct": correct, "raw_response": raw}


# ---------------------------------------------------------------------------
# Retrieval Quality
# ---------------------------------------------------------------------------

def retrieval_precision_at_k(
    retrieved_contents: list[str],
    evidence_texts: list[str],
    k: int = 5,
) -> float:
    """
    What fraction of top-k retrieved memories contain evidence?
    Uses substring matching (evidence text appears in retrieved content).
    """
    if not evidence_texts or not retrieved_contents:
        return 0.0

    top_k = retrieved_contents[:k]
    hits = 0
    for retrieved in top_k:
        retrieved_lower = retrieved.lower()
        for evidence in evidence_texts:
            if evidence.lower() in retrieved_lower:
                hits += 1
                break

    return hits / min(k, len(top_k))


# ---------------------------------------------------------------------------
# Storage Efficiency
# ---------------------------------------------------------------------------

def storage_reduction_rate(retained: int, total_ingested: int) -> float:
    """
    SRR = 1 - (retained / total_ingested)
    Higher is better (more compression).
    FadeMem reports 45% storage reduction (SRR = 0.45).
    """
    if total_ingested == 0:
        return 0.0
    return 1.0 - (retained / total_ingested)


def memory_efficiency_score(
    f1_score: float,
    storage_fraction: float,
) -> float:
    """
    Combined score: quality per unit storage.
    Higher is better. A system that gets F1=0.30 with 55% storage
    scores better than one that gets F1=0.28 with 100% storage.
    
    score = f1 / storage_fraction
    """
    if storage_fraction <= 0:
        return float("inf")
    return f1_score / storage_fraction


# ---------------------------------------------------------------------------
# Aggregate Reporting
# ---------------------------------------------------------------------------

LOCOMO_CATEGORIES = {
    1: "single-hop",
    2: "multi-hop",
    3: "temporal",
    4: "open-domain",
    5: "adversarial",  # excluded from standard eval
}

# FadeMem reported numbers for direct comparison
FADEMEM_BASELINES = {
    "multi-hop_f1": 29.43,
    "factual_consistency": 85.9,
    "storage_fraction": 55.0,
    "critical_retention": 82.1,
}

MEM0_BASELINES = {
    "multi-hop_f1": 28.37,
    "storage_fraction": 100.0,
    "critical_retention": 78.4,
}

MEMGPT_BASELINES = {
    "multi-hop_f1": 9.46,
}


def aggregate_results(per_question_results: list[dict]) -> dict:
    """
    Aggregate per-question results into category-level and overall metrics.
    
    Each result dict should have:
    - category: int (1-5)
    - f1: float
    - llm_correct: bool (optional)
    - retrieval_precision: float (optional)
    """
    # Filter to categories 1-4 (standard protocol)
    valid = [r for r in per_question_results if r.get("category", 5) <= 4]

    if not valid:
        return {"error": "No valid results"}

    # Overall metrics
    overall_f1 = sum(r["f1"] for r in valid) / len(valid)
    
    # LLM judge accuracy (if available)
    judged = [r for r in valid if "llm_correct" in r]
    overall_accuracy = (
        sum(1 for r in judged if r["llm_correct"]) / len(judged)
        if judged else None
    )

    # Per-category breakdown
    by_category = {}
    for cat_id, cat_name in LOCOMO_CATEGORIES.items():
        if cat_id == 5:
            continue
        cat_results = [r for r in valid if r.get("category") == cat_id]
        if cat_results:
            by_category[cat_name] = {
                "count": len(cat_results),
                "mean_f1": sum(r["f1"] for r in cat_results) / len(cat_results),
                "llm_accuracy": (
                    sum(1 for r in cat_results if r.get("llm_correct", False)) / len(cat_results)
                    if any("llm_correct" in r for r in cat_results) else None
                ),
            }

    return {
        "overall": {
            "num_questions": len(valid),
            "mean_f1": overall_f1,
            "llm_accuracy": overall_accuracy,
        },
        "by_category": by_category,
        "comparison": {
            "vs_fademem": {
                "our_f1": overall_f1,
                "fademem_multihop_f1": FADEMEM_BASELINES["multi-hop_f1"],
            },
            "vs_mem0": {
                "our_f1": overall_f1,
                "mem0_multihop_f1": MEM0_BASELINES["multi-hop_f1"],
            },
        },
    }
