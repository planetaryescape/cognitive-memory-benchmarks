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
from shared.metrics import token_f1, normalize_answer, llm_judge

JUDGE_MODEL = "gpt-4o-2024-08-06"


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
        # Critical / Core facts (should persist strongly) — fact_idx 0..7
        SyntheticFact("My name is Alex Chen", "critical", day_introduced=1, expected_core=True, access_days=[5, 10, 15, 20, 25]),
        SyntheticFact("I'm allergic to shellfish", "critical", day_introduced=1, expected_core=True, access_days=[8, 22]),
        SyntheticFact("I work at Meridian Labs as a senior engineer", "critical", day_introduced=1, expected_core=True, access_days=[3, 7, 14]),
        SyntheticFact("My partner's name is Jordan", "critical", day_introduced=2, expected_core=True, access_days=[6, 12, 18]),
        SyntheticFact("I have a dog named Pixel", "critical", day_introduced=2, expected_core=True, access_days=[4, 9, 16, 23]),
        SyntheticFact("I have type 1 diabetes and use a continuous glucose monitor", "critical", day_introduced=1, expected_core=True, access_days=[8, 19, 27]),
        SyntheticFact("My mother's name is Eileen and she lives in Vancouver", "critical", day_introduced=2, expected_core=True, access_days=[11, 21]),
        SyntheticFact("I live in Brooklyn, in the Park Slope neighborhood", "critical", day_introduced=2, expected_core=True, access_days=[7, 16, 26]),

        # Contextual facts (medium importance, should decay but be retrievable) — fact_idx 8..15
        SyntheticFact("I'm working on a project called Helios that's due in March", "contextual", day_introduced=3, access_days=[5, 8, 12]),
        SyntheticFact("I prefer dark mode in all my applications", "contextual", day_introduced=4, access_days=[10]),
        SyntheticFact("I've been learning Rust on weekends", "contextual", day_introduced=5, access_days=[11, 17]),
        SyntheticFact("My team has a standup at 9:30am every day", "contextual", day_introduced=3, access_days=[6]),
        SyntheticFact("I'm training for a half marathon in April", "contextual", day_introduced=6, access_days=[12, 20]),
        SyntheticFact("I drive a 2019 Subaru Outback", "contextual", day_introduced=4, access_days=[15]),
        SyntheticFact("My therapist's name is Dr. Patel and I see her on Tuesdays", "contextual", day_introduced=5, access_days=[12, 19]),
        SyntheticFact("I take a guitar lesson every other Thursday", "contextual", day_introduced=6, access_days=[14]),

        # Trivial facts (low importance, should fade quickly) — fact_idx 16..23
        SyntheticFact("I had pasta for lunch today", "trivial", day_introduced=3, access_days=[]),
        SyntheticFact("The weather was really nice this morning", "trivial", day_introduced=5, access_days=[]),
        SyntheticFact("I watched a documentary about octopuses last night", "trivial", day_introduced=7, access_days=[]),
        SyntheticFact("There was traffic on my commute today", "trivial", day_introduced=10, access_days=[]),
        SyntheticFact("I tried a new coffee shop called Bean Counter", "trivial", day_introduced=12, access_days=[]),
        SyntheticFact("My neighbor's cat got stuck in a tree this morning", "trivial", day_introduced=8, access_days=[]),
        SyntheticFact("I forgot my umbrella and got rained on", "trivial", day_introduced=13, access_days=[]),
        SyntheticFact("The elevator in my building was broken today", "trivial", day_introduced=18, access_days=[]),

        # Facts that get contradicted/updated — fact_idx 24..27
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
        SyntheticFact(
            "I'm planning to go to Tokyo for vacation in May", "contextual",
            day_introduced=5, access_days=[9],
            superseded_by="Actually we changed plans, we're going to Lisbon instead of Tokyo",
            superseded_on_day=18,
        ),
        SyntheticFact(
            "I prefer working from the office on Mondays", "contextual",
            day_introduced=4, access_days=[8],
            superseded_by="I switched to fully remote, I don't go into the office anymore",
            superseded_on_day=20,
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

    # Generate probes (questions to test at specific times).
    # Probes are evaluated using time-stepped ingestion: sessions through day D
    # are ingested before any probe at day D fires. This makes temporal_before
    # probes meaningful (the superseded fact is still current at probe time).
    probes = []

    # --- CORE PERSISTENCE (8) ---
    # Core facts at day 30 — all should be retrievable with strong scoring.
    probes.extend([
        {"day": 30, "question": "What is my name?", "expected": "Alex Chen", "fact_idx": 0, "type": "core_persistence"},
        {"day": 30, "question": "What am I allergic to?", "expected": "shellfish", "fact_idx": 1, "type": "core_persistence"},
        {"day": 30, "question": "Where do I work?", "expected": "Meridian Labs", "fact_idx": 2, "type": "core_persistence"},
        {"day": 30, "question": "What's my partner's name?", "expected": "Jordan", "fact_idx": 3, "type": "core_persistence"},
        {"day": 30, "question": "What's my dog's name?", "expected": "Pixel", "fact_idx": 4, "type": "core_persistence"},
        {"day": 30, "question": "Do I have any chronic medical conditions?", "expected": "type 1 diabetes", "fact_idx": 5, "type": "core_persistence"},
        {"day": 30, "question": "What's my mother's name and where does she live?", "expected": "Eileen, Vancouver", "fact_idx": 6, "type": "core_persistence"},
        {"day": 30, "question": "What neighborhood do I live in?", "expected": "Park Slope, Brooklyn", "fact_idx": 7, "type": "core_persistence"},
    ])

    # --- DECAY TRIVIAL (6) ---
    # Trivial unaccessed facts at day 30. With decay floors they should still
    # be retrievable when probed directly, just lower-ranked.
    probes.extend([
        {"day": 30, "question": "What did I have for lunch on day 3?", "expected": "pasta", "fact_idx": 16, "type": "decay_trivial"},
        {"day": 30, "question": "What documentary did I watch?", "expected": "octopuses", "fact_idx": 18, "type": "decay_trivial"},
        {"day": 30, "question": "What coffee shop did I try?", "expected": "Bean Counter", "fact_idx": 20, "type": "decay_trivial"},
        {"day": 30, "question": "What happened with my neighbor's cat?", "expected": "stuck in a tree", "fact_idx": 21, "type": "decay_trivial"},
        {"day": 30, "question": "Did I get caught in the rain at some point?", "expected": "forgot umbrella, got rained on", "fact_idx": 22, "type": "decay_trivial"},
        {"day": 30, "question": "Was there a problem with the elevator at any point?", "expected": "broken", "fact_idx": 23, "type": "decay_trivial"},
    ])

    # --- REVIVAL (5) ---
    # Memories that were mentioned once, never re-accessed, queried with
    # vague/oblique cues. Decay floors should keep them recoverable.
    probes.extend([
        {"day": 30, "question": "Was there anything about the weather I mentioned once?", "expected": "nice this morning", "fact_idx": 17, "type": "revival"},
        {"day": 30, "question": "Did I ever mention traffic?", "expected": "traffic on my commute", "fact_idx": 19, "type": "revival"},
        {"day": 30, "question": "Was there an incident with an animal at some point?", "expected": "neighbor's cat in a tree", "fact_idx": 21, "type": "revival"},
        {"day": 30, "question": "Have I had any minor weather mishaps recently?", "expected": "got rained on, forgot umbrella", "fact_idx": 22, "type": "revival"},
        {"day": 30, "question": "Has anything in my building been broken lately?", "expected": "elevator", "fact_idx": 23, "type": "revival"},
    ])

    # --- CONFLICT RESOLUTION (4) ---
    # Updated facts. Probe at day 30 — should return the *updated* version.
    probes.extend([
        {"day": 30, "question": "When is the Helios project deadline?", "expected": "April 1st", "fact_idx": 24, "type": "conflict"},
        {"day": 30, "question": "What language is the Helios backend in?", "expected": "Go", "fact_idx": 25, "type": "conflict"},
        {"day": 30, "question": "Where am I going for vacation in May?", "expected": "Lisbon", "fact_idx": 26, "type": "conflict"},
        {"day": 30, "question": "What's my work-from-home situation?", "expected": "fully remote", "fact_idx": 27, "type": "conflict"},
    ])

    # --- CONTEXTUAL RETENTION (6) ---
    # Medium-importance facts with light access pattern. Should be retrievable
    # at day 30, possibly paraphrased.
    probes.extend([
        {"day": 30, "question": "What project am I working on?", "expected": "Helios", "fact_idx": 8, "type": "contextual_retention"},
        {"day": 30, "question": "What language am I learning on weekends?", "expected": "Rust", "fact_idx": 10, "type": "contextual_retention"},
        {"day": 30, "question": "What am I training for?", "expected": "half marathon", "fact_idx": 12, "type": "contextual_retention"},
        {"day": 30, "question": "What car do I drive?", "expected": "2019 Subaru Outback", "fact_idx": 13, "type": "contextual_retention"},
        {"day": 30, "question": "Who is my therapist?", "expected": "Dr. Patel", "fact_idx": 14, "type": "contextual_retention"},
        {"day": 30, "question": "What musical instrument am I taking lessons in?", "expected": "guitar", "fact_idx": 15, "type": "contextual_retention"},
    ])

    # --- TEMPORAL: BEFORE UPDATE (4) ---
    # Probe a fact at a day before its supersession. Time-stepped ingestion
    # means the superseding fact has not yet been ingested.
    probes.extend([
        {"day": 10, "question": "When is the Helios deadline?", "expected": "March 15th", "fact_idx": 24, "type": "temporal_before_update"},
        {"day": 10, "question": "What language is the Helios backend in?", "expected": "Python", "fact_idx": 25, "type": "temporal_before_update"},
        {"day": 12, "question": "Where am I going for vacation in May?", "expected": "Tokyo", "fact_idx": 26, "type": "temporal_before_update"},
        {"day": 15, "question": "When do I prefer to be in the office?", "expected": "Mondays", "fact_idx": 27, "type": "temporal_before_update"},
    ])

    # --- TEMPORAL: AFTER UPDATE (4) ---
    # Same fact, probed after supersession.
    probes.extend([
        {"day": 22, "question": "When is the Helios deadline?", "expected": "April 1st", "fact_idx": 24, "type": "temporal_after_update"},
        {"day": 22, "question": "What language is the Helios backend in?", "expected": "Go", "fact_idx": 25, "type": "temporal_after_update"},
        {"day": 22, "question": "Where am I going for vacation in May?", "expected": "Lisbon", "fact_idx": 26, "type": "temporal_after_update"},
        {"day": 25, "question": "What's my work-from-home situation?", "expected": "fully remote", "fact_idx": 27, "type": "temporal_after_update"},
    ])

    # --- ASSOCIATIVE RETRIEVAL (5) ---
    # Cross-fact queries that should surface multiple related memories together.
    # Tests whether bidirectional associations form via co-retrieval.
    probes.extend([
        {"day": 30, "question": "What do you know about my family?", "expected": "Jordan (partner), Eileen (mother), Pixel (dog)", "fact_idx": -1, "type": "associative"},
        {"day": 30, "question": "What's my health situation?", "expected": "type 1 diabetes, shellfish allergy", "fact_idx": -1, "type": "associative"},
        {"day": 30, "question": "Tell me about the Helios project.", "expected": "Helios, deadline April 1st, Go backend", "fact_idx": -1, "type": "associative"},
        {"day": 30, "question": "What recurring appointments or activities do I have?", "expected": "therapy Tuesdays Dr. Patel, guitar lessons Thursdays, half marathon training", "fact_idx": -1, "type": "associative"},
        {"day": 30, "question": "What do you know about my home and commute?", "expected": "Park Slope Brooklyn, Subaru Outback", "fact_idx": -1, "type": "associative"},
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
    judge_model: str = JUDGE_MODEL,
    verbose: bool = True,
) -> dict:
    """Run the 30-day LTI benchmark with time-stepped ingestion + LLM judge."""
    from openai import OpenAI
    client = OpenAI()

    scenario = generate_30_day_scenario()
    facts = scenario["facts"]
    daily_sessions = scenario["daily_sessions"]
    probes = scenario["probes"]

    if verbose:
        print(f"LTI-Bench: {len(facts)} facts, {len(daily_sessions)} session days, {len(probes)} probes")

    adapter.reset()

    sessions_by_day = {s["day"]: s for s in daily_sessions}
    probes_by_day = {}
    for p in probes:
        probes_by_day.setdefault(p["day"], []).append(p)

    results_by_type = {}
    base_date = datetime(2024, 1, 1)

    for day in range(1, 31):
        # Ingest the day's session BEFORE running any probe at this day so
        # day-D probes see day-D state (and not later supersessions).
        if day in sessions_by_day:
            session = sessions_by_day[day]
            if verbose and day % 5 == 0:
                print(f"  Ingesting day {day}...")
            adapter.ingest_session(
                turns=session["turns"],
                session_id=f"day_{day}",
                timestamp=session["timestamp"],
                speaker_a="Alex",
                speaker_b="Assistant",
            )

        for probe in probes_by_day.get(day, []):
            query_result = adapter.query(
                question=probe["question"],
                timestamp=(base_date + timedelta(days=day - 1)).isoformat(),
            )

            from locomo.locomo_eval import generate_answer
            answer = generate_answer(
                question=probe["question"],
                query_result=query_result,
                client=client,
                model=model,
            )

            f1 = token_f1(answer, probe["expected"])["f1"]
            judgement = llm_judge(
                question=probe["question"],
                prediction=answer,
                ground_truth=probe["expected"],
                client=client,
                model=judge_model,
            )

            probe_type = probe["type"]
            results_by_type.setdefault(probe_type, []).append({
                "question": probe["question"],
                "expected": probe["expected"],
                "answer": answer,
                "f1": f1,
                "correct": judgement["correct"],
                "judge_raw": judgement["raw_response"],
                "day": day,
                "num_retrieved": len(query_result.retrieved_memories),
            })

    stats = adapter.get_stats()

    summary = {}
    for probe_type, results in results_by_type.items():
        n = len(results)
        mean_f1 = sum(r["f1"] for r in results) / n if n else 0
        accuracy = sum(1 for r in results if r["correct"]) / n if n else 0
        summary[probe_type] = {
            "count": n,
            "mean_f1": mean_f1,
            "accuracy": accuracy,
        }

    critical_results = results_by_type.get("core_persistence", [])
    critical_retention = (
        sum(1 for r in critical_results if r["correct"]) / len(critical_results)
        if critical_results else 0
    )

    all_results = [r for results in results_by_type.values() for r in results]
    overall_accuracy = sum(1 for r in all_results if r["correct"]) / len(all_results) if all_results else 0
    overall_f1 = sum(r["f1"] for r in all_results) / len(all_results) if all_results else 0

    output = {
        "config": {
            "answer_model": model,
            "judge_model": judge_model,
            "n_facts": len(facts),
            "n_sessions": len(daily_sessions),
            "n_probes": len(probes),
            "scoring": "llm_judge (CORRECT/WRONG) + token_f1",
            "ingestion_mode": "time_stepped",
        },
        "overall": {
            "accuracy": overall_accuracy,
            "mean_f1": overall_f1,
            "n": len(all_results),
        },
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

    if verbose:
        print(f"\n{'='*60}")
        print("LTI-BENCH RESULTS (judge: " + judge_model + ")")
        print(f"{'='*60}")
        for probe_type, data in summary.items():
            print(f"  {probe_type:25s}: accuracy={data['accuracy']*100:5.1f}%  F1={data['mean_f1']*100:5.1f}%  (n={data['count']})")
        print(f"\n  Overall accuracy:        {overall_accuracy*100:.1f}% (n={len(all_results)})")
        print(f"  Overall F1:              {overall_f1*100:.1f}%")
        print(f"  Critical fact retention: {critical_retention*100:.1f}% (FadeMem: 82.1%)")
        print(f"  Total memories stored:   {stats.total_memories}")
        print(f"  Core memories detected:  {stats.core_memories}")

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run LTI-Bench evaluation")
    parser.add_argument("--adapter", default="cognitive_memory", choices=["cognitive_memory", "naive_rag"])
    parser.add_argument("--model", default="gpt-4o-mini", help="Answer model")
    parser.add_argument("--judge-model", default=JUDGE_MODEL, help="LLM-as-judge model")
    parser.add_argument("--output", default="results/lti_bench_results.json")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a tuning trial JSON config (Phase 0c). Overrides "
        "CognitiveMemoryConfig fields and adapter kwargs per-trial.",
    )
    parser.add_argument(
        "--surface",
        choices=["sdk", "daemon"],
        default=None,
        help="Override the trial config's surface (sdk = in-process; "
        "daemon = via Unix socket). Used by Phase 3 SDK↔daemon parity "
        "checks. CLI flag wins over the JSON file's surface field.",
    )
    args = parser.parse_args()

    from shared.memory_adapter import CognitiveMemoryAdapter, NaiveRAGAdapter
    from shared.trial_config import load_trial_config

    trial_kwargs = load_trial_config(args.config)
    if args.surface is not None:
        trial_kwargs["surface"] = args.surface

    adapters = {
        "cognitive_memory": CognitiveMemoryAdapter,
        "naive_rag": NaiveRAGAdapter,
    }
    if args.adapter == "cognitive_memory":
        adapter = CognitiveMemoryAdapter(llm_model=args.model, **trial_kwargs)
    else:
        # NaiveRAGAdapter doesn't accept the trial kwargs — only the
        # cognitive_memory adapter is tunable. Warn if a trial was
        # passed alongside --adapter naive_rag so a misconfigured
        # study is loud rather than silently ignored.
        if trial_kwargs:
            print(
                f"warning: --config / --surface ignored for adapter={args.adapter}",
                flush=True,
            )
        adapter = NaiveRAGAdapter(llm_model=args.model)

    results = run_lti_bench(
        adapter,
        model=args.model,
        judge_model=args.judge_model,
        verbose=not args.quiet,
    )

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
