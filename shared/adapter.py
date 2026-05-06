"""
Memory adapter interface for benchmark evaluation.

Implement MemoryAdapter to plug in any memory system. Includes:
- CognitiveMemoryAdapter: For the cognitive-memory SDK
- NaiveRAGAdapter: Simple embedding + cosine similarity baseline
- FullContextAdapter: Stuff everything in the context window
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import time
import json

@dataclass
class MemoryStats:
    """Statistics about the memory system state."""
    total_memories: int = 0
    hot_memories: int = 0
    cold_memories: int = 0
    core_memories: int = 0
    faint_memories: int = 0  # below 15% retention
    avg_retention: float = 0.0
    storage_bytes: int = 0


@dataclass
class RetrievalResult:
    """A single retrieved memory with scores."""
    content: str
    relevance_score: float
    retention_score: float
    combined_score: float
    memory_type: str = "episodic"  # episodic, semantic, procedural
    is_core: bool = False
    access_count: int = 0
    age_days: float = 0.0
    created_at: str = ""  # ISO timestamp string for memory formatting


@dataclass
class QueryResult:
    """Result of a memory query."""
    retrieved_memories: list[RetrievalResult] = field(default_factory=list)
    answer: str = ""
    retrieval_time_ms: float = 0.0
    memories_considered: int = 0


class MemoryAdapter(ABC):
    """
    Abstract interface for memory systems under evaluation.

    The benchmark calls these methods in order:
    1. reset() - clear state before each conversation
    2. ingest_session() - called per session, chronologically
    3. query() - called per QA question after all sessions ingested
    4. get_stats() - called after all queries for efficiency metrics
    """

    @abstractmethod
    def reset(self):
        """Clear all memories. Called before each new conversation."""
        pass

    @abstractmethod
    def ingest_session(
        self,
        turns: list[dict],
        session_id: str,
        timestamp: str,
        speaker_a: str,
        speaker_b: str,
    ):
        """
        Process a conversation session and extract/store memories.

        Args:
            turns: List of {"speaker": str, "text": str, "dia_id": str}
            session_id: e.g. "session_1"
            timestamp: ISO datetime string for the session
            speaker_a: Name of first speaker
            speaker_b: Name of second speaker
        """
        pass

    @abstractmethod
    def query(
        self,
        question: str,
        timestamp: Optional[str] = None,
        top_k: int = 10,
    ) -> QueryResult:
        """
        Query the memory system with a question.

        Args:
            question: The benchmark question
            timestamp: When the question is asked (for decay calculation)
            top_k: Max memories to retrieve

        Returns:
            QueryResult with retrieved memories and optional generated answer
        """
        pass

    @abstractmethod
    def get_stats(self) -> MemoryStats:
        """Return current memory system statistics."""
        pass


# ---------------------------------------------------------------------------
# Cognitive Memory SDK Adapter
# ---------------------------------------------------------------------------

class CognitiveMemoryAdapter(MemoryAdapter):
    """
    Adapter wiring the cognitive-memory SDK to the benchmark harness.

    This is the real thing: full decay, boosting, associations, cold
    storage, TTL, consolidation, and core promotion through the SDK.
    """

    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        use_hash_embeddings: bool = False,
        dual_perspective: bool = False,
        deep_recall: bool = False,
        custom_extraction_instructions: Optional[str] = None,
        rerank: bool = False,
        rerank_factor: int = 2,
        extraction_mode: str = "semantic",
        hybrid_search: bool = False,
        graph_hops: int = None,
        decay_model: str = None,
    ):
        from cognitive_memory import SyncCognitiveMemory, CognitiveMemoryConfig

        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.dual_perspective = dual_perspective
        self.deep_recall = deep_recall
        self.rerank = rerank
        self.rerank_factor = rerank_factor
        self._rerank_client = None
        self._last_ingest_ts = None
        self._last_trace = None

        config_kwargs = dict(
            extraction_model=llm_model,
            embedding_model=embedding_model,
            run_maintenance_during_ingestion=False,  # tick after each session instead
            # Lower core promotion thresholds for benchmark scenarios
            core_access_threshold=3,
            core_stability_threshold=0.50,
            core_session_threshold=2,
            custom_extraction_instructions=custom_extraction_instructions,
            extraction_mode=extraction_mode,
        )
        if hybrid_search:
            config_kwargs["hybrid_search"] = True
        if graph_hops is not None:
            config_kwargs["graph_expansion_hops"] = graph_hops
        if decay_model is not None:
            config_kwargs["decay_model"] = decay_model
        config = CognitiveMemoryConfig(**config_kwargs)

        embedder = "hash" if use_hash_embeddings else "openai"
        self.memory = SyncCognitiveMemory(config=config, embedder=embedder)

    def reset(self):
        self.memory.clear()

    def _format_conversation(self, turns, timestamp, user_speaker=None):
        """
        Format turns into conversation text.

        If user_speaker is set, formats from that speaker's perspective:
        their messages as "User: ...", the other as "Assistant: ...".
        This biases extraction toward the user's messages.
        """
        date_header = f"[This conversation took place on {timestamp}]\n" if timestamp else ""
        lines = []
        for t in turns:
            if user_speaker:
                role = "User" if t["speaker"] == user_speaker else "Assistant"
                lines.append(f"{role} ({t['speaker']}): {t['text']}")
            else:
                lines.append(f"{t['speaker']}: {t['text']}")
        return date_header + "\n".join(lines)

    def ingest_session(self, turns, session_id, timestamp, speaker_a, speaker_b):
        """
        Feed session through SDK's memory extraction pipeline.

        If dual_perspective is enabled, ingests twice: once from each speaker's
        perspective (their messages as User, other as Assistant). This mirrors
        how Mem0 handles two-person conversations and biases extraction toward
        user messages. Conflict detection and dedup handle overlap.
        """
        ts = _parse_timestamp(timestamp)
        self._last_ingest_ts = ts

        if self.dual_perspective:
            # Pass 1: speaker_a as user
            text_a = self._format_conversation(turns, timestamp, user_speaker=speaker_a)
            self.memory.extract_and_store(
                conversation_text=text_a,
                session_id=f"{session_id}_perspective_{speaker_a}",
                timestamp=ts,
            )
            # Pass 2: speaker_b as user
            text_b = self._format_conversation(turns, timestamp, user_speaker=speaker_b)
            self.memory.extract_and_store(
                conversation_text=text_b,
                session_id=f"{session_id}_perspective_{speaker_b}",
                timestamp=ts,
            )
        else:
            # Single pass: equal weight to both speakers
            conversation_text = self._format_conversation(turns, timestamp)
            self.memory.extract_and_store(
                conversation_text=conversation_text,
                session_id=session_id,
                timestamp=ts,
            )

        # Run maintenance after each session
        self.memory.tick(ts)

    def _get_rerank_client(self):
        if self._rerank_client is None:
            from openai import OpenAI
            self._rerank_client = OpenAI(timeout=120.0)
        return self._rerank_client

    def _rerank_memories(self, question: str, memories: list, top_k: int) -> list:
        """Re-rank retrieved memories using LLM relevance scoring."""
        if not memories or len(memories) <= top_k:
            return memories

        client = self._get_rerank_client()

        # Build prompt with truncated memory contents
        memory_lines = []
        for i, mem in enumerate(memories, 1):
            content = mem.content[:300]
            memory_lines.append(f"{i}. {content}")
        memories_text = "\n".join(memory_lines)

        prompt = (
            f'Given this question: "{question}"\n\n'
            f"Rate how relevant each memory below is to answering this question. "
            f"Score each from 0.0 (irrelevant) to 1.0 (directly answers or contains key facts needed).\n\n"
            f"Memories:\n{memories_text}\n\n"
            f"Return ONLY a JSON array of {len(memories)} scores: [0.8, 0.2, ...]"
        )

        try:
            resp = client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=len(memories) * 5,
            )
            raw = resp.choices[0].message.content.strip()
            scores = json.loads(raw)

            if len(scores) == len(memories):
                for mem, score in zip(memories, scores):
                    mem.combined_score = float(score)
        except Exception:
            pass  # Keep original scores on failure

        memories.sort(key=lambda x: x.combined_score, reverse=True)
        return memories[:top_k]

    def query(self, question, timestamp=None, top_k=10):
        """
        Query SDK's retrieval pipeline with full retention-weighted scoring,
        association traversal, boosting, and core promotion.
        """
        start = time.time()

        ts = _parse_timestamp(timestamp) if timestamp else datetime.now()

        # If re-ranking, retrieve more candidates
        search_top_k = top_k * self.rerank_factor if self.rerank else top_k

        # Search with the full engine (includes association graph, boosts, core promotion)
        search_response = self.memory.search(
            query=question,
            top_k=search_top_k,
            timestamp=ts,
            session_id="query",  # enable session-based boost tracking
            deep_recall=self.deep_recall,
            trace=True,
        )

        # Unwrap SearchResponse (v6) or plain list (v5 compat)
        results = search_response.results if hasattr(search_response, 'results') else search_response

        # Stash trace for instrumentation
        self._last_trace = getattr(search_response, 'trace', None)

        # Convert to adapter format
        retrieved = []
        for r in results:
            age_days = 0.0
            if r.memory.created_at:
                age_days = max(0.0, (ts - r.memory.created_at).total_seconds() / 86400)

            created_at_str = ""
            if r.memory.created_at:
                created_at_str = r.memory.created_at.strftime("%Y-%m-%d")

            retrieved.append(RetrievalResult(
                content=r.memory.content,
                relevance_score=r.relevance_score,
                retention_score=r.retention_score,
                combined_score=r.combined_score,
                memory_type=r.memory.category.value,
                is_core=r.memory.category.value == "core",
                access_count=r.memory.access_count,
                age_days=age_days,
                created_at=created_at_str,
            ))

        # Re-rank if enabled
        if self.rerank and len(retrieved) > top_k:
            retrieved = self._rerank_memories(question, retrieved, top_k)

        return QueryResult(
            retrieved_memories=retrieved,
            retrieval_time_ms=(time.time() - start) * 1000,
            memories_considered=len(self.memory.adapter.hot),
        )

    def get_stats(self):
        stats = self.memory.get_stats()
        return MemoryStats(
            total_memories=stats["total_memories"],
            hot_memories=stats["hot_memories"],
            cold_memories=stats["cold_memories"],
            core_memories=stats["core_memories"],
            faint_memories=stats["faint_memories"],
            avg_retention=stats["avg_retention"],
        )


# ---------------------------------------------------------------------------
# Cognitive Memory Raw Turn Adapter (FadeMem-comparable)
# ---------------------------------------------------------------------------

class CognitiveMemoryRawTurnAdapter(MemoryAdapter):
    """
    Stores each dialogue turn directly as a memory — NO LLM extraction
    of structured facts, but DOES use LLM for importance scoring.

    Comparable to FadeMem's approach: raw conversation turns stored and
    retrieved using the full cognitive-memory engine (decay, scoring,
    associations, consolidation). FadeMem also uses an LLM for importance
    scoring on raw turns.

    The difference from CognitiveMemoryAdapter is in ingestion:
    - CognitiveMemoryAdapter: LLM extracts structured facts from conversation
    - CognitiveMemoryRawTurnAdapter: each turn stored verbatim, LLM scores importance

    Retrieval, scoring, consolidation, and answer generation are identical.
    """

    IMPORTANCE_PROMPT = """Rate the importance of this dialogue turn for long-term memory on a scale of 0.0 to 1.0.

Consider:
- Identity info (name, age, medical, family): 0.8-1.0
- Lasting facts, preferences, plans: 0.6-0.8
- Specific events or activities: 0.4-0.6
- Casual conversation, greetings, filler: 0.1-0.3

Turn: "{turn}"

Respond with just a number between 0.0 and 1.0."""

    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
    ):
        from cognitive_memory import SyncCognitiveMemory, CognitiveMemoryConfig
        from cognitive_memory.types import MemoryCategory
        from cognitive_memory.embeddings import cosine_similarity as _cosine_sim

        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.MemoryCategory = MemoryCategory
        self._cosine_sim = _cosine_sim
        self._client = None

        config = CognitiveMemoryConfig(
            extraction_model=llm_model,
            embedding_model=embedding_model,
            run_maintenance_during_ingestion=False,  # tick after each session instead
            # Lower core promotion thresholds for benchmark scenarios
            core_access_threshold=3,
            core_stability_threshold=0.50,
            core_session_threshold=2,
        )

        self.memory = SyncCognitiveMemory(config=config, embedder="openai")

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def _score_importance_batch(self, turns: list[str]) -> list[float]:
        """Score importance of each turn using LLM. Batch for efficiency."""
        import time as _time
        client = self._get_client()
        scores = []
        for turn_text in turns:
            prompt = self.IMPORTANCE_PROMPT.format(turn=turn_text)
            for attempt in range(3):
                try:
                    resp = client.chat.completions.create(
                        model=self.llm_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                        max_tokens=5,
                    )
                    raw = resp.choices[0].message.content.strip()
                    score = float(raw)
                    scores.append(max(0.0, min(1.0, score)))
                    break
                except (ValueError, TypeError):
                    scores.append(0.5)  # fallback
                    break
                except Exception as e:
                    if attempt < 2 and ("500" in str(e) or "server_error" in str(e)):
                        _time.sleep(2 ** attempt)
                        continue
                    scores.append(0.5)
                    break
        return scores

    def reset(self):
        self.memory.clear()

    def ingest_session(self, turns, session_id, timestamp, speaker_a, speaker_b):
        """
        Store each dialogue turn directly as a memory with LLM importance scoring.
        No extraction of structured facts — mirrors FadeMem's raw-turn storage.
        Runs consolidation/maintenance after each session.
        """
        ts = _parse_timestamp(timestamp)

        # Format turn texts
        turn_texts = [f"{turn['speaker']}: {turn['text']}" for turn in turns]

        # Score importance for each turn via LLM
        importances = self._score_importance_batch(turn_texts)

        for text, importance in zip(turn_texts, importances):
            # Add memory with LLM-scored importance
            mem = self.memory.add(
                content=text,
                category=self.MemoryCategory.SEMANTIC,
                importance=importance,
                session_id=session_id,
                timestamp=ts,
            )

            # Ingestion-time similarity boost (repeated exposure reinforcement)
            if mem.embedding is not None:
                for existing_mem in list(self.memory.adapter.hot.values()):
                    if existing_mem.id == mem.id or existing_mem.embedding is None:
                        continue
                    sim = self._cosine_sim(mem.embedding, existing_mem.embedding)
                    if sim > 0.75:
                        existing_mem.stability = min(1.0, existing_mem.stability + 0.05)

        # Run maintenance after each session: consolidation, cold migration, TTL
        self.memory.tick(ts)

    def query(self, question, timestamp=None, top_k=10):
        """Full retrieval pipeline with association graph, boosts, core promotion."""
        start = time.time()
        ts = _parse_timestamp(timestamp) if timestamp else datetime.now()

        search_response = self.memory.search(
            query=question,
            top_k=top_k,
            timestamp=ts,
            session_id="query",
        )
        results = search_response.results if hasattr(search_response, 'results') else search_response

        retrieved = []
        for r in results:
            age_days = 0.0
            if r.memory.created_at:
                age_days = max(0.0, (ts - r.memory.created_at).total_seconds() / 86400)

            created_at_str = ""
            if r.memory.created_at:
                created_at_str = r.memory.created_at.strftime("%Y-%m-%d")

            retrieved.append(RetrievalResult(
                content=r.memory.content,
                relevance_score=r.relevance_score,
                retention_score=r.retention_score,
                combined_score=r.combined_score,
                memory_type=r.memory.category.value,
                is_core=r.memory.category.value == "core",
                access_count=r.memory.access_count,
                age_days=age_days,
                created_at=created_at_str,
            ))

        return QueryResult(
            retrieved_memories=retrieved,
            retrieval_time_ms=(time.time() - start) * 1000,
            memories_considered=len(self.memory.adapter.hot),
        )

    def get_stats(self):
        stats = self.memory.get_stats()
        return MemoryStats(
            total_memories=stats["total_memories"],
            hot_memories=stats["hot_memories"],
            cold_memories=stats["cold_memories"],
            core_memories=stats["core_memories"],
            faint_memories=stats["faint_memories"],
            avg_retention=stats["avg_retention"],
        )


# ---------------------------------------------------------------------------
# Naive RAG Baseline
# ---------------------------------------------------------------------------

class NaiveRAGAdapter(MemoryAdapter):
    """
    Simple RAG baseline: embed everything, retrieve by cosine similarity.
    No decay, no importance weighting, no forgetting. This is what most
    memory systems do today, and it's the thing we're arguing against.
    """

    def __init__(self, llm_model="gpt-4o-mini", embedding_model="text-embedding-3-small"):
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.chunks = []       # list of {"text": str, "embedding": list, "session_id": str}
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def _embed(self, text: str) -> list[float]:
        client = self._get_client()
        resp = client.embeddings.create(input=text, model=self.embedding_model)
        return resp.data[0].embedding

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        import numpy as np
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    def reset(self):
        self.chunks = []

    def ingest_session(self, turns, session_id, timestamp, speaker_a, speaker_b):
        """Chunk by turn, embed each turn."""
        for turn in turns:
            text = f"{turn['speaker']}: {turn['text']}"
            embedding = self._embed(text)
            self.chunks.append({
                "text": text,
                "embedding": embedding,
                "session_id": session_id,
                "timestamp": timestamp,
            })

    def query(self, question, timestamp=None, top_k=10):
        start = time.time()
        q_emb = self._embed(question)

        scored = []
        for chunk in self.chunks:
            sim = self._cosine_sim(q_emb, chunk["embedding"])
            scored.append((sim, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        retrieved = [
            RetrievalResult(
                content=c["text"],
                relevance_score=s,
                retention_score=1.0,  # no decay
                combined_score=s,
            )
            for s, c in top
        ]

        return QueryResult(
            retrieved_memories=retrieved,
            retrieval_time_ms=(time.time() - start) * 1000,
            memories_considered=len(self.chunks),
        )

    def get_stats(self):
        return MemoryStats(
            total_memories=len(self.chunks),
            hot_memories=len(self.chunks),
            avg_retention=1.0,  # everything is at 100% forever
        )


# ---------------------------------------------------------------------------
# Full Context Baseline
# ---------------------------------------------------------------------------

class FullContextAdapter(MemoryAdapter):
    """
    Stuff the entire conversation into the LLM context window.
    No memory system at all. Upper bound on recall (if it fits),
    but shows context window limitations.
    """

    def __init__(self, llm_model="gpt-4o-mini"):
        self.llm_model = llm_model
        self.full_text = ""

    def reset(self):
        self.full_text = ""

    def ingest_session(self, turns, session_id, timestamp, speaker_a, speaker_b):
        session_text = f"\n--- {session_id} ({timestamp}) ---\n"
        session_text += "\n".join(f"{t['speaker']}: {t['text']}" for t in turns)
        self.full_text += session_text + "\n"

    def query(self, question, timestamp=None, top_k=10):
        start = time.time()
        # The "retrieval" is just the full text
        return QueryResult(
            retrieved_memories=[
                RetrievalResult(
                    content=self.full_text[:50000],  # truncate if needed
                    relevance_score=1.0,
                    retention_score=1.0,
                    combined_score=1.0,
                )
            ],
            retrieval_time_ms=(time.time() - start) * 1000,
            memories_considered=1,
        )

    def get_stats(self):
        return MemoryStats(
            total_memories=1,
            hot_memories=1,
            storage_bytes=len(self.full_text.encode()),
        )


# ---------------------------------------------------------------------------
# Hybrid Memory Adapter (raw turns + extracted facts + BM25)
# ---------------------------------------------------------------------------

class HybridMemoryAdapter(MemoryAdapter):
    """
    Combines extracted facts (CognitiveMemoryAdapter) with raw turn storage
    and BM25 retrieval. Designed for dialog-heavy benchmarks like DialSim
    where granular episodic details matter.

    Retrieval merges three signals:
    1. Embedding similarity on extracted memories (semantic understanding)
    2. Embedding similarity on raw turns (exact detail preservation)
    3. BM25 keyword matching on raw turns (keyword recall)

    Results are fused via reciprocal rank fusion (RRF).
    """

    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        deep_recall: bool = False,
        rerank: bool = False,
        rerank_factor: int = 2,
        bm25_weight: float = 0.4,
        raw_turn_weight: float = 0.3,
        extracted_weight: float = 0.3,
        rrf_k: int = 60,
        context_window: int = 2,  # include ±N neighboring turns around hits
        extract: bool = True,
    ):
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.deep_recall = deep_recall
        self.rerank = rerank
        self.rerank_factor = rerank_factor
        self.bm25_weight = bm25_weight
        self.raw_turn_weight = raw_turn_weight
        self.extracted_weight = extracted_weight
        self.rrf_k = rrf_k
        self.context_window = context_window
        self.extract = extract

        # Extracted facts adapter (full cognitive memory pipeline)
        # Only created if extraction is enabled
        self._extracted = None
        if self.extract:
            self._extracted = CognitiveMemoryAdapter(
                llm_model=llm_model,
                embedding_model=embedding_model,
                deep_recall=deep_recall,
                rerank=False,  # we do our own fusion-then-rerank
            )

        # Raw turn storage
        self._raw_turns: list[dict] = []  # {"text": str, "embedding": list, "session_id": str, "timestamp": str}
        self._embed_client = None

        # BM25 index (built lazily at query time)
        self._bm25 = None
        self._bm25_dirty = True  # needs rebuild
        self._bm25_corpus: list[str] = []

        # Reranking
        self._rerank_client = None

    def _get_embed_client(self):
        if self._embed_client is None:
            from openai import OpenAI
            self._embed_client = OpenAI()
        return self._embed_client

    def _embed(self, text: str) -> list[float]:
        client = self._get_embed_client()
        resp = client.embeddings.create(input=text, model=self.embedding_model)
        return resp.data[0].embedding

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embed for efficiency. OpenAI supports up to 2048 inputs."""
        if not texts:
            return []
        client = self._get_embed_client()
        # Process in batches of 512
        all_embeddings = []
        for i in range(0, len(texts), 512):
            batch = texts[i:i + 512]
            resp = client.embeddings.create(input=batch, model=self.embedding_model)
            all_embeddings.extend([d.embedding for d in resp.data])
        return all_embeddings

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        import numpy as np
        a_arr, b_arr = np.array(a), np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-9))

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text for BM25: lowercase, strip punctuation, split."""
        import re
        text = text.lower()
        # Strip punctuation (keep alphanumeric and spaces)
        text = re.sub(r"[^\w\s]", " ", text)
        # Collapse whitespace
        return text.split()

    def _build_bm25(self):
        """Rebuild BM25 index from raw turns."""
        from rank_bm25 import BM25Okapi
        tokenized = [self._tokenize(text) for text in self._bm25_corpus]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def reset(self):
        if self._extracted:
            self._extracted.reset()
        self._raw_turns = []
        self._bm25 = None
        self._bm25_dirty = True
        self._bm25_corpus = []

    def ingest_session(self, turns, session_id, timestamp, speaker_a, speaker_b):
        # 1. Extract structured facts via cognitive memory (if enabled)
        if self._extracted:
            self._extracted.ingest_session(turns, session_id, timestamp, speaker_a, speaker_b)

        # 2. Store raw turns with embeddings for direct retrieval
        turn_texts = [f"[{timestamp}] {t['speaker']}: {t['text']}" for t in turns]
        embeddings = self._embed_batch(turn_texts)

        for text, emb in zip(turn_texts, embeddings):
            self._raw_turns.append({
                "text": text,
                "embedding": emb,
                "session_id": session_id,
                "timestamp": timestamp,
            })
            self._bm25_corpus.append(text)

        # Mark BM25 as needing rebuild (built lazily at query time)
        self._bm25_dirty = True

    def _get_rerank_client(self):
        if self._rerank_client is None:
            from openai import OpenAI
            self._rerank_client = OpenAI(timeout=120.0)
        return self._rerank_client

    def _rerank_results(self, question: str, results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]:
        """Re-rank fused results using LLM."""
        if not results or len(results) <= top_k:
            return results

        client = self._get_rerank_client()
        memory_lines = []
        for i, mem in enumerate(results, 1):
            memory_lines.append(f"{i}. {mem.content[:300]}")
        memories_text = "\n".join(memory_lines)

        prompt = (
            f'Given this question: "{question}"\n\n'
            f"Rate how relevant each item below is to answering this question. "
            f"Score each from 0.0 (irrelevant) to 1.0 (directly answers or contains key facts needed).\n\n"
            f"Items:\n{memories_text}\n\n"
            f"Return ONLY a JSON array of {len(results)} scores: [0.8, 0.2, ...]"
        )

        try:
            resp = client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=len(results) * 5,
            )
            raw = resp.choices[0].message.content.strip()
            scores = json.loads(raw)
            if len(scores) == len(results):
                for mem, score in zip(results, scores):
                    mem.combined_score = float(score)
        except Exception:
            pass

        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:top_k]

    def _extract_date_from_question(self, question: str) -> Optional[str]:
        """Extract a date reference from a question for temporal filtering."""
        import re
        # Match patterns like "December 25, 1995", "May 11, 1995", "October 10, 1994"
        date_match = re.search(
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            question
        )
        if date_match:
            return date_match.group(0).replace(",", "")
        return None

    def query(self, question, timestamp=None, top_k=10):
        start = time.time()
        ts = _parse_timestamp(timestamp) if timestamp else datetime.now()

        # Retrieve more candidates for fusion
        fusion_k = top_k * 3

        # Extract date from question for temporal boosting
        question_date = self._extract_date_from_question(question)

        # --- Signal 1: Extracted memories (embedding + cognitive scoring) ---
        extracted_ranked = []
        if self._extracted:
            extracted_result = self._extracted.query(question, timestamp=timestamp, top_k=fusion_k)
            extracted_ranked = [(i, mem) for i, mem in enumerate(extracted_result.retrieved_memories)]

        # --- Signal 2: Raw turns by embedding similarity (with temporal boost) ---
        q_emb = self._embed(question)
        raw_scored = []
        for turn in self._raw_turns:
            sim = self._cosine_sim(q_emb, turn["embedding"])
            # Temporal boost: if question mentions a date, boost turns from that date
            if question_date and question_date.lower().replace(",", "") in turn.get("timestamp", "").lower().replace(",", ""):
                sim = min(1.0, sim + 0.3)  # significant boost for date-matching turns
            raw_scored.append((sim, turn))
        raw_scored.sort(key=lambda x: x[0], reverse=True)
        raw_ranked = raw_scored[:fusion_k]

        # --- Signal 3: BM25 on raw turns ---
        bm25_ranked = []
        if self._bm25_dirty and self._bm25_corpus:
            self._build_bm25()
            self._bm25_dirty = False
        if self._bm25 and self._bm25_corpus:
            query_tokens = self._tokenize(question)
            bm25_scores = self._bm25.get_scores(query_tokens)
            # Apply temporal boost to BM25 scores
            if question_date:
                date_norm = question_date.lower().replace(",", "")
                for i, text in enumerate(self._bm25_corpus):
                    if date_norm in text.lower().replace(",", ""):
                        bm25_scores[i] += 5.0  # significant boost
            bm25_indexed = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)[:fusion_k]
            bm25_ranked = [(idx, score) for idx, score in bm25_indexed if score > 0]

        # --- Reciprocal Rank Fusion ---
        # Build a unified content -> score map
        content_scores: dict[str, float] = {}
        content_meta: dict[str, RetrievalResult] = {}

        # Extracted memories
        for rank, (_, mem) in enumerate(extracted_ranked):
            rrf_score = self.extracted_weight / (self.rrf_k + rank + 1)
            key = mem.content
            content_scores[key] = content_scores.get(key, 0) + rrf_score
            if key not in content_meta:
                content_meta[key] = mem

        # Raw turns by embedding
        for rank, (sim, turn) in enumerate(raw_ranked):
            rrf_score = self.raw_turn_weight / (self.rrf_k + rank + 1)
            key = turn["text"]
            content_scores[key] = content_scores.get(key, 0) + rrf_score
            if key not in content_meta:
                content_meta[key] = RetrievalResult(
                    content=turn["text"],
                    relevance_score=sim,
                    retention_score=1.0,
                    combined_score=sim,
                    memory_type="raw_turn",
                )

        # BM25 raw turns
        for rank, (idx, bm25_score) in enumerate(bm25_ranked):
            rrf_score = self.bm25_weight / (self.rrf_k + rank + 1)
            key = self._bm25_corpus[idx]
            content_scores[key] = content_scores.get(key, 0) + rrf_score
            if key not in content_meta:
                content_meta[key] = RetrievalResult(
                    content=key,
                    relevance_score=bm25_score,
                    retention_score=1.0,
                    combined_score=bm25_score,
                    memory_type="raw_turn",
                )

        # Sort by fused score
        fused = sorted(content_scores.items(), key=lambda x: x[1], reverse=True)

        # Context window expansion: include neighboring turns around top hits
        if self.context_window > 0 and self._raw_turns:
            # Build a set of raw turn texts in order for index lookup
            raw_texts = [t["text"] for t in self._raw_turns]
            raw_text_set = set(raw_texts)
            # Find indices of top hits that are raw turns
            neighbor_contents = set()
            for content, _ in fused[:top_k]:
                if content in raw_text_set:
                    try:
                        idx = raw_texts.index(content)
                    except ValueError:
                        continue
                    for offset in range(-self.context_window, self.context_window + 1):
                        ni = idx + offset
                        if 0 <= ni < len(raw_texts) and raw_texts[ni] not in content_scores:
                            neighbor_contents.add(raw_texts[ni])
            # Add neighbors with a small bonus score
            for nc in neighbor_contents:
                content_scores[nc] = 0.001  # low score, just ensures inclusion
                content_meta[nc] = RetrievalResult(
                    content=nc,
                    relevance_score=0.0,
                    retention_score=1.0,
                    combined_score=0.001,
                    memory_type="context_neighbor",
                )
            # Re-sort after adding neighbors
            fused = sorted(content_scores.items(), key=lambda x: x[1], reverse=True)

        # Build final results
        retrieved = []
        for content, fused_score in fused[:fusion_k]:
            mem = content_meta[content]
            retrieved.append(RetrievalResult(
                content=mem.content,
                relevance_score=mem.relevance_score,
                retention_score=mem.retention_score,
                combined_score=fused_score,
                memory_type=mem.memory_type,
                is_core=mem.is_core,
                access_count=mem.access_count,
                age_days=mem.age_days,
                created_at=mem.created_at,
            ))

        # Optionally rerank
        if self.rerank and len(retrieved) > top_k:
            retrieved = self._rerank_results(question, retrieved, top_k)
        else:
            retrieved = retrieved[:top_k]

        return QueryResult(
            retrieved_memories=retrieved,
            retrieval_time_ms=(time.time() - start) * 1000,
            memories_considered=len(self._raw_turns) + (len(self._extracted.memory.adapter.hot) if self._extracted else 0),
        )

    def get_stats(self):
        if self._extracted:
            extracted_stats = self._extracted.get_stats()
            return MemoryStats(
                total_memories=extracted_stats.total_memories + len(self._raw_turns),
                hot_memories=extracted_stats.hot_memories,
                cold_memories=extracted_stats.cold_memories,
                core_memories=extracted_stats.core_memories,
                faint_memories=extracted_stats.faint_memories,
                avg_retention=extracted_stats.avg_retention,
            )
        return MemoryStats(
            total_memories=len(self._raw_turns),
            hot_memories=len(self._raw_turns),
            avg_retention=1.0,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_timestamp(ts) -> datetime:
    """Parse a timestamp string or datetime into a datetime object."""
    if isinstance(ts, datetime):
        return ts
    if ts is None:
        return datetime.now()
    if isinstance(ts, str):
        # Try common formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%B %d, %Y %I:%M %p",
            "%d %B %Y",
        ]:
            try:
                return datetime.strptime(ts.strip(), fmt)
            except ValueError:
                continue
        # Last resort: try dateutil
        try:
            from dateutil.parser import parse as dateutil_parse
            return dateutil_parse(ts)
        except Exception:
            pass
    return datetime.now()
