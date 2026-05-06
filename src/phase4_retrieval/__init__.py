"""
Phase 4 - Query routing and RAG retrieval.

This module provides the complete Phase 4 pipeline for:
1. Intent routing (advisory/performance/factual classification)
2. Hybrid retrieval with chunk selection
3. Context packing for LLM generation
"""

from .router import IntentRouter, RouteLabel
from .retriever import RetrievalEngine, RetrievalResult
from .context_packer import ContextPacker, ContextBundle
from .types import RouteLabel, RetrievalResult, ContextBundle

__version__ = "0.1.0"
__all__ = [
    "IntentRouter",
    "RouteLabel", 
    "RetrievalEngine",
    "RetrievalResult",
    "ContextPacker",
    "ContextBundle"
]
