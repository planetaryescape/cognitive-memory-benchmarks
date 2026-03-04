#!/usr/bin/env python3
"""
LTI-Bench: Long-Term Interaction Benchmark for Forgetting Systems.

This is our own controlled benchmark that directly tests the properties
that differentiate cognitive-memory from other systems:

1. DECAY BEHAVIOR: Do old, unaccessed memories actually lose retrieval priority?
2. REVIVAL: Can a faint memory be revived when queried directly?
3. CORE PERSISTENCE: Do core memories (name, allergies) maintain high retrieval?
4. ASSOCIATIVE RETRIEVAL: Do related memories surface together?
5. CONFLICT RESOLUTION: When facts contradict, does the system handle it?
6. STORAGE EFFICIENCY: How does memory count scale over time?

Unlike LoCoMo (which tests recall quality), this tests the *dynamics* of memory.
FadeMem reports: 82.1% critical fact retention at 55% storage after 30 days.

Usage:
    python lti_bench.py --adapter cognitive_memory
"""

import argparse
import json
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from shared.memory_adapter import (
    CognitiveMemoryAdapter,
    NaiveRAGAdapter,
    MemoryAdapter,
    MemoryStats,
)
from shared.metrics import token_f1, normalize_answer


# ---------------------------------------------------------------------------
# Synthetic interaction generation
# ---------------------------------------------------------------------------

@dataclass
class SyntheticFact:
    """A fact injected into conversation at a known time."""
    content: str
    category: str  # "critical", "contextual", "trivial"
    day_introduced: int
    expected_core: bool = False
    access_days: list[int] = field(default_factory=list)  # days when re-accessed
    superseded_by: str = None  # if contradicted later
    superseded_on_day: int = None


def generate_30_day_scenario() -> dict:
    """
    Generate a controlled 30-day interaction scenario with known facts,
    access patterns, and contradictions.
    
    Returns:
        {
            "facts": list of SyntheticFact,
            "daily_sessions": list of {day, turns},
            "probes": list of {day, question, expected_answer, fact_index, probe_type},
        }
    """
    facts = [
        # Critical / Core facts (should persist strongly)
        SyntheticFact("My name is Alex Chen", "critical", day_introduced=1, expected_core=True, access_days=[5, 10, 15, 20, 25]),
        SyntheticFact("I'm allergic to shellfish", "critical", day_introduced=1, expected_core=True, access_days=[8, 22]),
        SyntheticFact("I work at Meridian Labs as a senior engineer", "critical", day_introduced=1, expected_core=True, access_days=[3, 7, 14]),
        SyntheticFact("My partner's name is Jordan", "critical", day_introduced=2, expected_core=True, access_days=[6, 12, 18]),
        SyntheticFact("I have a dog named Pixel", "critical", day_introduced=2, expected_core=True, access_days=[4, 9, 16, 23]),

        # Contextual facts (medium importance, should decay but be retrievable)
        SyntheticFact("I'm working on a project called Helios that's due in March", "contextual", day_introduced=3, access_days=[5, 8, 12]),
        SyntheticFact("I prefer dark mode in all my applications", "contextual", day_introduced=4, access_days=[10]),
        SyntheticFact("I've been learning Rust on weekends", "contextual", day_introduced=5, access_days=[11, 17]),
        SyntheticFact("My team has a standup at 9:30am every day", "contextual", day_introduced=3, access_days=[6]),
        SyntheticFact("I'm training for a half marathon in April", "contextual", day_introduced=6, access_days=[12, 20]),

        # Trivial facts (low importance, should fade quickly)
        SyntheticFact("I had pasta for lunch today", "trivial", day_introduced=3, access_days=[]),
        SyntheticFact("The weather was really nice this morning", "trivial", day_introduced=5, access_days=[]),
        SyntheticFact("I watched a documentary about octopuses last night", "trivial", day_introduced=7, access_days=[]),
        SyntheticFact("There was traffic on my commute today", "trivial", day_introduced=10, access_days=[]),
        SyntheticFact("I tried a new coffee shop called Bean Counter", "trivial", day_introduced=12, access_days=[]),

        # Facts that get contradicted/updated
        SyntheticFact(
            "The Helios project deadline is March 15th", "contextual",
            day_introduced=3, access_days=[5],
            superseded_by="The Helios deadline got pushed to April 1st",
            superseded_on_day=14,
        ),
        SyntheticFact(
            "I'm using Python for the Helios backend", "contextual",
            day_introduced=4, access_days=[7],
            superseded_by="We switched the Helios backend to Go for performance",
            superseded_on_day=16,
        ),
    ]

    # Generate daily sessions (simple conversations that naturally mention facts)
    base_date = datetime(2024, 1, 1)
    daily_sessions = []

    for day in range(1, 31):
        turns = []
        date = base_date + timedelta(days=day - 1)

        # Introduce new facts for this day
        for fi, fact in enumerate(facts):
            if fact.day_introduced == day:
                turns.append({
                    "speaker": "Alex",
                    "text": fact.content,
                    "dia_id": f"d{day}_{fi}",
                })
                turns.append({
                    "speaker": "Assistant",
                    "text": f"Got it, I'll remember that.",
                    "dia_id": f"d{day}_{fi}_ack",
                })

            # Re-access facts on scheduled days
            if day in fact.access_days:
                turns.append({
                    "speaker": "Alex",
                    "text": f"You know how I mentioned that {fact.content.lower()}? Still relevant.",
                    "dia_id": f"d{day}_{fi}_reaccess",
                })

            # Handle contradictions
            if fact.superseded_on_day == day and fact.superseded_by:
                turns.append({
                    "speaker": "Alex",
                    "text": f"Actually, update on something: {fact.superseded_by}",
                    "dia_id": f"d{day}_{fi}_update",
                })

        # Add some filler conversation so sessions aren't just fact-dumps
        if day % 3 == 0:
            turns.append({"speaker": "Alex", "text": "How's it going today?", "dia_id": f"d{day}_filler"})

        if turns:
            daily_sessions.append({
                "day": day,
                "timestamp": date.isoformat(),
                "turns": turns,
            })

    # Generate probes (questions to test at specific times)
    probes = []

    # --- Probe Type 1: CORE PERSISTENCE ---
    # Ask about core facts at day 30. Should all be retrievable.
    probes.extend([
        {"day": 30, "question": "What is my name?", "expected": "Alex Chen", "fact_idx": 0, "type": "core_persistence"},
        {"day": 30, "question": "What am I allergic to?", "expected": "shellfish", "fact_idx": 1, "type": "core_persistence"},
        {"day": 30, "question": "Where do I work?", "expected": "Meridian Labs", "fact_idx": 2, "type": "core_persistence"},
        {"day": 30, "question": "What's my partner's name?", "expected": "Jordan", "fact_idx": 3, "type": "core_persistence"},
        {"day": 30, "question": "What's my dog's name?", "expected": "Pixel", "fact_idx": 4, "type": "core_persistence"},
    ])

    # --- Probe Type 2: DECAY VERIFICATION ---
    # Ask about trivial facts at day 30. Naive RAG returns them at full strength.
    # A decay system should rank them lower than critical facts.
    probes.extend([
        {"day": 30, "question": "What did I have for lunch on day 3?", "expected": "pasta", "fact_idx": 10, "type": "decay_trivial"},
        {"day": 30, "question": "What documentary did I watch?", "expected": "octopuses", "fact_idx": 12, "type": "decay_trivial"},
        {"day": 30, "question": "What coffee shop did I try?", "expected": "Bean Counter", "fact_idx": 14, "type": "decay_trivial"},
    ])

    # --- Probe Type 3: REVIVAL ---
    # Ask about a trivial fact that hasn't been accessed. If the system has
    # decay floors (never-delete), it should still be retrievable, just faint.
    probes.extend([
        {"day": 30, "question": "Was there anything about the weather I mentioned once?", "expected": "nice this morning", "fact_idx": 11, "type": "revival"},
        {"day": 30, "question": "Did I ever mention traffic?", "expected": "traffic on my commute", "fact_idx": 13, "type": "revival"},
    ])

    # --- Probe Type 4: CONFLICT RESOLUTION ---
    # Ask about facts that were updated. Should return the updated version.
    probes.extend([
        {"day": 30, "question": "When is the Helios project deadline?", "expected": "April 1st", "fact_idx": 15, "type": "conflict"},
        {"day": 30, "question": "What language is the Helios backend in?", "expected": "Go", "fact_idx": 16, "type": "conflict"},
    ])

    # --- Probe Type 5: CONTEXTUAL RETENTION ---
    # Ask about medium-importance facts that were accessed a few times.
    probes.extend([
        {"day": 30, "question": "What project am I working on?", "expected": "Helios", "fact_idx": 5, "type": "contextual_retention"},
        {"day": 30, "question": "What language am I learning on weekends?", "expected": "Rust", "fact_idx": 7, "type": "contextual_retention"},
        {"day": 30, "question": "What am I training for?", "expected": "half marathon", "fact_idx": 9, "type": "contextual_retention"},
    ])

    # --- Probe Type 6: TEMPORAL QUERIES ---
    # Ask about things at different time points
    probes.extend([
        {"day": 10, "question": "When is the Helios deadline?", "expected": "March 15th", "fact_idx": 15, "type": "temporal_before_update"},
        {"day": 20, "question": "When is the Helios deadline?", "expected": "April 1st", "fact_idx": 15, "type": "temporal_after_update"},
    ])

    return {
        "facts": facts,
        "daily_sessions": daily_sessions,
        "probes": probes,
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def run_lti_bench(
    adapter: MemoryAdapter,
    model: str = "gpt-4o-mini",
    verbose: bool = True,
) -> dict:
    """Run the 30-day LTI benchmark."""
    from openai import OpenAI
    client = OpenAI()

    scenario = generate_30_day_scenario()
    facts = scenario["facts"]
    daily_sessions = scenario["daily_sessions"]
    probes = scenario["probes"]

    if verbose:
        print(f"LTI-Bench: {len(facts)} facts, {len(daily_sessions)} session days, {len(probes)} probes")

    # Reset and ingest
    adapter.reset()

    for session in daily_sessions:
        if verbose and session["day"] % 5 == 0:
            print(f"  Ingesting day {session['day']}...")

        adapter.ingest_session(
            turns=session["turns"],
            session_id=f"day_{session['day']}",
            timestamp=session["timestamp"],
            speaker_a="Alex",
            speaker_b="Assistant",
        )

    # Run probes grouped by day (some probes are at day 10, 20, 30)
    probe_days = sorted(set(p["day"] for p in probes))
    results_by_type = {}

    for probe_day in probe_days:
        day_probes = [p for p in probes if p["day"] == probe_day]

        for probe in day_probes:
            # Query
            query_result = adapter.query(
                question=probe["question"],
                timestamp=(datetime(2024, 1, 1) + timedelta(days=probe_day - 1)).isoformat(),
            )

            # Generate answer
            from locomo.locomo_eval import generate_answer
            answer = generate_answer(
                question=probe["question"],
                query_result=query_result,
                client=client,
                model=model,
            )

            # Score
            f1 = token_f1(answer, probe["expected"])["f1"]
            expected_lower = normalize_answer(probe["expected"])
            answer_lower = normalize_answer(answer)
            contains_expected = expected_lower in answer_lower

            probe_type = probe["type"]
            if probe_type not in results_by_type:
                results_by_type[probe_type] = []

            results_by_type[probe_type].append({
                "question": probe["question"],
                "expected": probe["expected"],
                "answer": answer,
                "f1": f1,
                "contains_expected": contains_expected,
                "day": probe_day,
                "num_retrieved": len(query_result.retrieved_memories),
            })

    # Get final stats
    stats = adapter.get_stats()

    # Compute summary metrics
    summary = {}
    for probe_type, results in results_by_type.items():
        n = len(results)
        mean_f1 = sum(r["f1"] for r in results) / n if n else 0
        accuracy = sum(1 for r in results if r["contains_expected"]) / n if n else 0
        summary[probe_type] = {
            "count": n,
            "mean_f1": mean_f1,
            "accuracy": accuracy,
        }

    # Overall
    all_results = [r for results in results_by_type.values() for r in results]
    critical_results = results_by_type.get("core_persistence", [])
    critical_retention = (
        sum(1 for r in critical_results if r["contains_expected"]) / len(critical_results)
        if critical_results else 0
    )

    output = {
        "summary": summary,
        "critical_fact_retention": critical_retention,
        "storage": {
            "total_memories": stats.total_memories,
            "hot_memories": stats.hot_memories,
            "cold_memories": stats.cold_memories,
            "core_memories": stats.core_memories,
        },
        "comparison": {
            "fademem_critical_retention": 0.821,
            "fademem_storage_fraction": 0.55,
            "ours_critical_retention": critical_retention,
            "ours_total_memories": stats.total_memories,
        },
        "detailed": results_by_type,
    }

    # Print
    if verbose:
        print(f"\n{'='*60}")
        print("LTI-BENCH RESULTS")
        print(f"{'='*60}")
        for probe_type, data in summary.items():
            print(f"  {probe_type:25s}: accuracy={data['accuracy']*100:5.1f}%  F1={data['mean_f1']*100:5.1f}%  (n={data['count']})")
        print(f"\n  Critical fact retention: {critical_retention*100:.1f}% (FadeMem: 82.1%)")
        print(f"  Total memories stored:   {stats.total_memories}")
        print(f"  Core memories detected:  {stats.core_memories}")

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run LTI-Bench evaluation")
    parser.add_argument("--adapter", default="cognitive_memory", choices=["cognitive_memory", "naive_rag"])
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--output", default="results/lti_bench_results.json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    from memory_adapter import CognitiveMemoryAdapter, NaiveRAGAdapter
    adapters = {
        "cognitive_memory": CognitiveMemoryAdapter,
        "naive_rag": NaiveRAGAdapter,
    }
    adapter = adapters[args.adapter](llm_model=args.model)

    results = run_lti_bench(adapter, model=args.model, verbose=not args.quiet)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
