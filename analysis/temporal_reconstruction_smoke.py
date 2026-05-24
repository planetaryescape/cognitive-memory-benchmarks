"""Cheap temporal reconstruction smoke benchmark.

This is intentionally synthetic and API-free. It validates that the SDK
experiment flag changes retrieval context shape before we spend on LoCoMo A/B.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from cognitive_memory import CognitiveMemoryConfig, Memory, MemoryCategory, SyncCognitiveMemory
from cognitive_memory.embeddings import EmbeddingProvider


AFTER_QUERY = "What happened after Alex injured her ankle?"
CURRENT_QUERY = "Where does Jamie live now?"

EXPECTED_AFTER_EVIDENCE = [
    "Alex injured her ankle.",
    "Alex started physiotherapy.",
    "Alex resumed light running.",
]
EXPECTED_CURRENT = "Jamie lives in London."
EXPECTED_STALE_STATE = "Jamie lives in Manchester."


class ControlledEmbeddings(EmbeddingProvider):
    """Deterministic vectors that isolate temporal behavior from embedding noise."""

    _vectors: dict[str, list[float]] = {
        AFTER_QUERY: [1.0, 0.0, 0.0],
        "Alex injured her ankle.": [1.0, 0.0, 0.0],
        "Alex started physiotherapy.": [0.99, 0.01, 0.0],
        "Alex resumed light running.": [0.98, 0.02, 0.0],
        "Alex trained for the marathon.": [0.2, 0.0, 1.0],
        CURRENT_QUERY: [0.0, 1.0, 0.0],
        "Jamie lives in Manchester.": [0.0, 1.0, 0.0],
        "Jamie lives in London.": [0.0, 0.7, 0.714],
    }

    @property
    def dimensions(self) -> int:
        return 3

    def embed(self, text: str) -> list[float]:
        return self._vectors.get(text, [0.0, 0.0, 1.0])

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


@dataclass
class ScenarioResult:
    mode: str
    after_results: list[str]
    after_temporal_evidence: list[str]
    current_results: list[str]
    current_temporal_evidence: list[str]


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _temporal(date: str, status: str, *, valid_to: str | None = None) -> dict:
    valid_time = {"status": status, "valid_from": f"{date}T00:00:00"}
    if valid_to is not None:
        valid_time["valid_to"] = f"{valid_to}T00:00:00"
    return {
        "mentioned_at": {"session_id": f"s_{date}", "timestamp": f"{date}T00:00:00"},
        "event_time": {"start": f"{date}T00:00:00", "granularity": "day", "confidence": 0.9},
        "valid_time": valid_time,
        "raw_time_expressions": [date],
    }


def _add(
    memory: SyncCognitiveMemory,
    content: str,
    date: str,
    status: str,
    *,
    category: MemoryCategory = MemoryCategory.EPISODIC,
    valid_to: str | None = None,
) -> None:
    memory.add_memory_object(
        Memory(
            content=content,
            category=category,
            importance=0.7,
            stability=0.4,
            created_at=_dt(f"{date}T00:00:00"),
            last_accessed_at=_dt(f"{date}T00:00:00"),
            temporal=_temporal(date, status, valid_to=valid_to),
        )
    )


def _build_memory(mode: str) -> SyncCognitiveMemory:
    config = CognitiveMemoryConfig(
        temporal_query_mode=mode,
        temporal_candidate_k=10,
        temporal_final_k=10,
        temporal_decay_alpha=0.25,
        temporal_anchor_neighbor_boost=0.30,
        temporal_validity_match_boost=0.35,
        temporal_time_expression_boost=0.15,
    )
    memory = SyncCognitiveMemory(config=config, embedder=ControlledEmbeddings())

    _add(memory, "Alex trained for the marathon.", "2024-01-01", "completed")
    _add(memory, "Alex injured her ankle.", "2024-01-05", "completed")
    _add(memory, "Alex started physiotherapy.", "2024-01-12", "completed")
    _add(memory, "Alex resumed light running.", "2024-01-20", "completed")
    _add(
        memory,
        "Jamie lives in Manchester.",
        "2024-01-01",
        "superseded",
        category=MemoryCategory.SEMANTIC,
        valid_to="2024-03-01",
    )
    _add(memory, "Jamie lives in London.", "2024-03-01", "current", category=MemoryCategory.SEMANTIC)
    return memory


def run_scenario(mode: str) -> ScenarioResult:
    memory = _build_memory(mode)
    after = memory.search(AFTER_QUERY, top_k=3, timestamp=_dt("2024-02-01T00:00:00"))
    current = memory.search(CURRENT_QUERY, top_k=2, timestamp=_dt("2024-04-01T00:00:00"))
    return ScenarioResult(
        mode=mode,
        after_results=[item.memory.content for item in after.results],
        after_temporal_evidence=[item["content"] for item in after.temporal_evidence],
        current_results=[item.memory.content for item in current.results],
        current_temporal_evidence=[item["content"] for item in current.temporal_evidence],
    )


def run_smoke() -> dict:
    off = run_scenario("off")
    auto = run_scenario("auto")
    checks = {
        "default_off_emits_no_temporal_evidence": off.after_temporal_evidence == [],
        "auto_orders_after_evidence_chronologically": auto.after_temporal_evidence == EXPECTED_AFTER_EVIDENCE,
        "off_current_query_can_pick_stale_semantic_state": off.current_results[0] == EXPECTED_STALE_STATE,
        "auto_current_query_prefers_current_state": auto.current_results[0] == EXPECTED_CURRENT,
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "scenarios": {
            "off": asdict(off),
            "auto": asdict(auto),
        },
        "notes": [
            "Controlled smoke only; not a LoCoMo quality estimate.",
            "Use this as a preflight before paid/slow LoCoMo A/B.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tuning/runs/phase14-temporal-reconstruction/controlled_smoke.json"),
    )
    args = parser.parse_args()

    result = run_smoke()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
