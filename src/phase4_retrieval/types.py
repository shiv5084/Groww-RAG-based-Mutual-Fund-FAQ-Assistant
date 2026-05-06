"""
Type definitions for Phase 4 retrieval system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


class RouteLabel(Enum):
    """Query routing labels."""
    ADVISORY = "advisory"  # Comparative/advice queries → refusal template
    PERFORMANCE = "performance"  # Returns/performance queries → factsheet URL only
    FACTUAL = "factual"  # Factual/scheme/process queries → full RAG


@dataclass
class RetrievalResult:
    """Single retrieval result with metadata."""
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    source_url: str
    doc_type: str
    hybrid_score: Optional[float] = None
    semantic_score: Optional[float] = None
    lexical_score: Optional[float] = None


@dataclass
class ContextBundle:
    """Complete context bundle for LLM generation."""
    query: str
    route_label: RouteLabel
    primary_chunk: Optional[RetrievalResult] = None
    secondary_chunks: List[RetrievalResult] = None
    system_prompt: Optional[str] = None
    user_context: Optional[str] = None
    citation_url: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.secondary_chunks is None:
            self.secondary_chunks = []
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class RetrievalStats:
    """Statistics for retrieval operations."""
    total_queries: int = 0
    advisory_queries: int = 0
    performance_queries: int = 0
    factual_queries: int = 0
    avg_retrieval_time: float = 0.0
    avg_chunks_retrieved: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def update(self, route_label: RouteLabel, retrieval_time: float, num_chunks: int):
        """Update statistics with new query."""
        self.total_queries += 1
        self.avg_retrieval_time = (self.avg_retrieval_time * (self.total_queries - 1) + retrieval_time) / self.total_queries
        self.avg_chunks_retrieved = (self.avg_chunks_retrieved * (self.total_queries - 1) + num_chunks) / self.total_queries
        
        if route_label == RouteLabel.ADVISORY:
            self.advisory_queries += 1
        elif route_label == RouteLabel.PERFORMANCE:
            self.performance_queries += 1
        elif route_label == RouteLabel.FACTUAL:
            self.factual_queries += 1
