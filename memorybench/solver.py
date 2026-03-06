"""
CognitiveMemory solver for MemoryBench framework.

Plugs the cognitive-memory SDK into MemoryBench's BaseSolver/BaseAgent interface.
Supports both OpenAI and vLLM backends (vLLM requires Linux + GPU).

Usage (within MemoryBench framework):
    python -m src.predict --memory_system cognitive_memory --domain Open-Domain

Or standalone (for testing):
    python memorybench/solver.py --test
"""

import os
import sys
import json
import time
from typing import List, Dict, Optional, Literal, Union
from pathlib import Path

# Add parent dir for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.adapter import (
    CognitiveMemoryAdapter,
    _parse_timestamp,
    QueryResult,
)


class CognitiveMemoryBenchAgent:
    """
    Agent compatible with MemoryBench's BaseAgent interface.
    Uses our CognitiveMemoryAdapter internally.
    """

    def __init__(self, config: dict):
        self.config = config
        self.llm_model = config.get("llm_model", "gpt-4o-mini")
        self.retrieve_k = config.get("retrieve_k", 20)
        self.deep_recall = config.get("deep_recall", True)
        self.rerank = config.get("rerank", True)
        self.rerank_factor = config.get("rerank_factor", 2)
        self.memory_cache_dir = config.get("memory_cache_dir", "./cognitive_memory_cache")

        # LLM client for response generation
        self._llm_client = None
        self._llm_provider = config.get("llm_provider", "openai")
        self._llm_config = config.get("llm_config", {})

        # Initialize adapter
        self.adapter = CognitiveMemoryAdapter(
            llm_model=self.llm_model,
            deep_recall=self.deep_recall,
            rerank=self.rerank,
            rerank_factor=self.rerank_factor,
        )

    def _get_llm_client(self):
        if self._llm_client is None:
            from openai import OpenAI
            if self._llm_provider == "vllm":
                base_url = self._llm_config.get("vllm_base_url", "http://localhost:12366/v1")
                self._llm_client = OpenAI(base_url=base_url, api_key="dummy")
            else:
                self._llm_client = OpenAI()
        return self._llm_client

    def _generate_llm(self, messages: list, max_tokens: int = 2048) -> str:
        client = self._get_llm_client()
        model = self._llm_config.get("model", self.llm_model)
        temp = self._llm_config.get("temperature", 0.1)

        for attempt in range(5):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                err_str = str(e).lower()
                if attempt < 4 and any(k in err_str for k in ("500", "502", "503", "rate_limit", "timeout")):
                    time.sleep(min(60, 2 ** attempt * 2))
                    continue
                raise

    def add_conversation_to_memory(
        self,
        messages: List[Dict[str, str]],
        conversation_idx: Union[int, str] = 0,
    ):
        """
        Ingest a conversation into cognitive memory.
        MemoryBench format: [{role: "user"/"assistant", content: "..."}]
        """
        # Convert to adapter turn format
        turns = []
        for i, msg in enumerate(messages):
            speaker = "User" if msg["role"] == "user" else "Assistant"
            turns.append({
                "speaker": speaker,
                "text": msg["content"],
                "dia_id": f"conv{conversation_idx}_turn{i}",
            })

        session_id = f"conv_{conversation_idx}"
        self.adapter.ingest_session(
            turns=turns,
            session_id=session_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            speaker_a="User",
            speaker_b="Assistant",
        )

    def save_memories(self):
        """Save memories to cache dir (for MemoryBench caching)."""
        os.makedirs(self.memory_cache_dir, exist_ok=True)
        # Export memory state
        memories = list(self.adapter.memory.adapter.hot.values())
        serialized = []
        for m in memories:
            serialized.append({
                "id": m.id,
                "content": m.content,
                "category": m.category.value,
                "importance": m.importance,
                "stability": m.stability,
                "access_count": m.access_count,
            })
        with open(os.path.join(self.memory_cache_dir, "memories.json"), "w") as f:
            json.dump(serialized, f, indent=2, default=str)

    def load_memories(self):
        """Load memories from cache (not fully implemented — re-ingest is safer)."""
        cache_path = os.path.join(self.memory_cache_dir, "memories.json")
        if os.path.exists(cache_path):
            print(f"Note: Memory cache exists at {cache_path} but re-ingestion is recommended for full fidelity")

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        lang: Literal["en", "zh"] = "en",
        retrieve_k: int = None,
    ) -> str:
        """Retrieve memories and generate response."""
        if retrieve_k is None:
            retrieve_k = self.retrieve_k

        question = messages[-1]["content"]

        # Retrieve from cognitive memory
        query_result = self.adapter.query(
            question=question,
            top_k=retrieve_k,
        )

        # Format context from retrieved memories
        if query_result.retrieved_memories:
            docs = [mem.content for mem in query_result.retrieved_memories]
            context = "\n".join(docs)
        else:
            context = "(No relevant memories found)"

        # Build prompt
        if lang == "en":
            user_prompt = (
                f"Context:\n{context}\n\n"
                f"User:\n{question}\n\n"
                f"Based on the context provided, respond naturally and appropriately to the user's input above."
            )
        else:
            user_prompt = (
                f"Context:\n{context}\n\n"
                f"User:\n{question}\n\n"
                f"Based on the context provided, respond naturally."
            )

        messages[-1]["content"] = user_prompt
        return self._generate_llm(messages)


class CognitiveMemoryBenchSolver:
    """
    Solver compatible with MemoryBench's BaseSolver interface.
    """

    AGENT_CLASS = CognitiveMemoryBenchAgent
    MAX_THREADS = 1  # Sequential to avoid API rate limits

    def __init__(self, config: dict, memory_cache_dir: str):
        self.config = config
        self.memory_cache_dir = memory_cache_dir
        self.method_name = "cognitive_memory"
        config["memory_cache_dir"] = memory_cache_dir
        self.agent = self.AGENT_CLASS(config)

    def create_or_load_memory(self, dialogs: List[Dict], dialogs_dir: str):
        """Ingest all dialogs into cognitive memory."""
        cache_marker = os.path.join(self.memory_cache_dir, ".cached")
        if os.path.exists(cache_marker):
            print(f"Loading memory cache from {self.memory_cache_dir}")
            self.agent.load_memories()
            return

        print(f"Creating memory cache at {self.memory_cache_dir}")
        for i, dialog in enumerate(dialogs):
            print(f"  Ingesting dialog {i+1}/{len(dialogs)}...")
            self.agent.add_conversation_to_memory(
                dialog["dialog"],
                dialog["test_idx"],
            )
        self.agent.save_memories()
        with open(cache_marker, "w") as f:
            f.write("cached")

    def memory_locomo_conversation(self, conversation: dict, session_cnt: int):
        """Ingest LoCoMo-format conversation sessions."""
        session_idx = 1
        while f"session_{session_idx}" in conversation:
            session = conversation[f"session_{session_idx}"]
            session_date = conversation.get(f"session_{session_idx}_date_time", "")

            turns = []
            for turn in session:
                turns.append({
                    "speaker": turn["speaker"],
                    "text": turn["text"],
                    "dia_id": turn.get("dia_id", f"s{session_idx}"),
                })

            self.agent.adapter.ingest_session(
                turns=turns,
                session_id=f"session_{session_idx}",
                timestamp=session_date,
                speaker_a=conversation.get("speaker_a", "Speaker A"),
                speaker_b=conversation.get("speaker_b", "Speaker B"),
            )
            session_idx += 1

    def delete_conversation_memory(self):
        """Clear memory for next conversation."""
        self.agent.adapter.reset()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run basic sanity check")
    args = parser.parse_args()

    if args.test:
        config = {
            "llm_model": "gpt-4o-mini",
            "retrieve_k": 10,
            "deep_recall": True,
            "rerank": False,
        }
        solver = CognitiveMemoryBenchSolver(config, memory_cache_dir="/tmp/cm_bench_test")

        # Simulate a conversation
        dialog = [
            {"role": "user", "content": "My name is Alice and I'm a software engineer."},
            {"role": "assistant", "content": "Nice to meet you Alice!"},
            {"role": "user", "content": "I love hiking and I went to Mount Rainier last weekend."},
            {"role": "assistant", "content": "That sounds wonderful!"},
        ]
        solver.agent.add_conversation_to_memory(dialog, conversation_idx=0)

        # Test retrieval
        response = solver.agent.generate_response(
            messages=[{"role": "user", "content": "What is Alice's profession?"}],
        )
        print(f"Response: {response}")
        print("Solver test passed!")
