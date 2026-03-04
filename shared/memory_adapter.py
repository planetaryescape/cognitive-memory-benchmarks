"""
Compatibility shim: re-exports from cognitive_memory.adapter so that
locomo_eval.py and lti_bench.py imports continue to work unchanged.

    from memory_adapter import CognitiveMemoryAdapter, NaiveRAGAdapter, ...
"""

from .adapter import (
    MemoryAdapter,
    MemoryStats,
    RetrievalResult,
    QueryResult,
    CognitiveMemoryAdapter,
    CognitiveMemoryRawTurnAdapter,
    NaiveRAGAdapter,
    FullContextAdapter,
)

__all__ = [
    "MemoryAdapter",
    "MemoryStats",
    "RetrievalResult",
    "QueryResult",
    "CognitiveMemoryAdapter",
    "CognitiveMemoryRawTurnAdapter",
    "NaiveRAGAdapter",
    "FullContextAdapter",
]
