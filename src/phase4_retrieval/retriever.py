"""
Retrieval engine for Phase 4 with query embedding and hybrid search.

Handles embedding queries, hybrid search, and primary chunk selection
with deduplication and ranking logic.
"""

import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever
from .types import RouteLabel, RetrievalResult, RetrievalStats


class RetrievalEngine:
    """Advanced retrieval engine with hybrid search and chunk selection."""
    
    def __init__(self, 
                 embedding_engine: EmbeddingEngine,
                 vector_store: VectorStore,
                 hybrid_retriever: HybridRetriever,
                 config: Dict = None):
        """
        Initialize retrieval engine.
        
        Args:
            embedding_engine: Phase 3 embedding engine
            vector_store: Phase 3 vector store
            hybrid_retriever: Phase 3 hybrid retriever
            config: Retrieval configuration
        """
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.hybrid_retriever = hybrid_retriever
        self.config = config or self._default_config()
        self.stats = RetrievalStats()
        
    def _default_config(self) -> Dict:
        """Default retrieval configuration."""
        return {
            "top_k": 8,  # Initial retrieval count
            "final_k": 3,  # Final chunks to return
            "min_score_threshold": 0.1,  # Minimum similarity score
            "dedupe_threshold": 0.9,  # Deduplication similarity threshold
            "doc_type_priorities": {  # Priorities for doc_type selection
                "factsheet": 1.0,
                "kii": 0.9,  # Key Information Document
                "prospectus": 0.8,
                "amc_home": 0.7,
                "scheme_document": 0.6,
                "other": 0.5
            },
            "mmr_enabled": True,  # Maximal Marginal Relevance
            "mmr_lambda": 0.7,  # MMR diversity weight
            "cache_enabled": True,
            "cache_ttl": 3600  # Cache TTL in seconds
        }
    
    def retrieve(self, query: str, route_label: RouteLabel) -> List[RetrievalResult]:
        """
        Perform retrieval based on query and route.
        
        Args:
            query: User query string
            route_label: Query route classification
            
        Returns:
            List of ranked RetrievalResult objects
        """
        start_time = time.time()
        
        # Route-specific retrieval logic
        if route_label == RouteLabel.ADVISORY:
            # Advisory queries: minimal or no retrieval
            results = self._retrieve_for_advisory(query)
        elif route_label == RouteLabel.PERFORMANCE:
            # Performance queries: factsheet-focused retrieval
            results = self._retrieve_for_performance(query)
        else:  # RouteLabel.FACTUAL
            # Factual queries: full hybrid retrieval
            results = self._retrieve_for_factual(query)
        
        # Update statistics
        retrieval_time = time.time() - start_time
        self.stats.update(route_label, retrieval_time, len(results))
        
        return results
    
    def _retrieve_for_advisory(self, query: str) -> List[RetrievalResult]:
        """
        Minimal retrieval for advisory queries.
        
        Returns empty list as advisory queries should use refusal template.
        """
        return []
    
    def _retrieve_for_performance(self, query: str) -> List[RetrievalResult]:
        """
        Factsheet-focused retrieval for performance queries.
        
        Prioritizes factsheet documents for performance/returns queries.
        """
        # Get hybrid search results
        hybrid_results = self.hybrid_retriever.search(
            query, 
            top_k=self.config["top_k"]
        )
        
        # Convert to RetrievalResult objects
        retrieval_results = self._convert_to_retrieval_results(hybrid_results)
        
        # Filter and prioritize factsheets
        factsheet_results = [
            r for r in retrieval_results 
            if r.doc_type == "factsheet" and r.score >= self.config["min_score_threshold"]
        ]
        
        # If no factsheets found, fall back to best scoring results
        if not factsheet_results:
            factsheet_results = retrieval_results[:1]  # Take top result
        
        return factsheet_results[:1]  # Return only primary chunk
    
    def _retrieve_for_factual(self, query: str) -> List[RetrievalResult]:
        """
        Full hybrid retrieval for factual queries.
        
        Performs comprehensive search with deduplication and ranking.
        """
        # Get hybrid search results
        hybrid_results = self.hybrid_retriever.search(
            query, 
            top_k=self.config["top_k"]
        )
        
        # Convert to RetrievalResult objects
        retrieval_results = self._convert_to_retrieval_results(hybrid_results)
        
        # Filter by minimum score
        filtered_results = [
            r for r in retrieval_results 
            if r.score >= self.config["min_score_threshold"]
        ]
        
        # Apply deduplication
        deduped_results = self._deduplicate_results(filtered_results)
        
        # Apply MMR if enabled
        if self.config["mmr_enabled"] and len(deduped_results) > 1:
            deduped_results = self._apply_mmr(query, deduped_results)
        
        # Select primary chunk
        primary_chunk = self._select_primary_chunk(deduped_results)
        
        # Return primary + secondary chunks
        if primary_chunk:
            secondary_chunks = [r for r in deduped_results if r.chunk_id != primary_chunk.chunk_id]
            return [primary_chunk] + secondary_chunks[:self.config["final_k"]-1]
        
        return deduped_results[:self.config["final_k"]]
    
    def _convert_to_retrieval_results(self, hybrid_results: List[Dict]) -> List[RetrievalResult]:
        """Convert hybrid search results to RetrievalResult objects."""
        retrieval_results = []
        
        for result in hybrid_results:
            # Extract metadata
            metadata = result.get('metadata', {})
            
            retrieval_result = RetrievalResult(
                chunk_id=result.get('chunk_id', ''),
                text=result.get('text', ''),
                score=result.get('hybrid_score', result.get('score', 0.0)),
                metadata=metadata,
                source_url=metadata.get('source_url', ''),
                doc_type=metadata.get('doc_type', 'other'),
                hybrid_score=result.get('hybrid_score'),
                semantic_score=result.get('semantic_score'),
                lexical_score=result.get('lexical_score')
            )
            
            retrieval_results.append(retrieval_result)
        
        return retrieval_results
    
    def _deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Remove duplicate or highly similar results.
        
        Uses text similarity and metadata matching.
        """
        if len(results) <= 1:
            return results
        
        deduped = []
        threshold = self.config["dedupe_threshold"]
        
        for result in results:
            is_duplicate = False
            
            # Check against existing deduped results
            for existing in deduped:
                # Check same doc_id and similar content
                if (result.metadata.get('doc_id') == existing.metadata.get('doc_id') and
                    self._text_similarity(result.text, existing.text) > threshold):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduped.append(result)
        
        return deduped
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using simple overlap.
        
        Returns similarity score between 0 and 1.
        """
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _apply_mmr(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """
        Apply Maximal Marginal Relevance for diversity.
        
        Balances relevance and diversity in results.
        """
        if len(results) <= 1:
            return results
        
        mmr_lambda = self.config["mmr_lambda"]
        selected = []
        remaining = results.copy()
        
        # Select most relevant result first
        selected.append(remaining.pop(0))
        
        # Select remaining results using MMR
        while remaining and len(selected) < self.config["final_k"]:
            best_idx = 0
            best_score = -1
            
            for i, candidate in enumerate(remaining):
                # Calculate relevance score
                relevance = candidate.score
                
                # Calculate diversity (max similarity to selected)
                max_similarity = 0
                for selected_item in selected:
                    similarity = self._text_similarity(candidate.text, selected_item.text)
                    max_similarity = max(max_similarity, similarity)
                
                # MMR score: λ * relevance - (1-λ) * max_similarity
                mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * max_similarity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return selected
    
    def _select_primary_chunk(self, results: List[RetrievalResult]) -> Optional[RetrievalResult]:
        """
        Select primary chunk based on doc_type priority and score.
        
        Args:
            results: List of retrieval results
            
        Returns:
            Primary chunk or None if no results
        """
        if not results:
            return None
        
        # Sort by doc_type priority and score
        priorities = self.config["doc_type_priorities"]
        
        def sort_key(result):
            priority = priorities.get(result.doc_type, priorities.get("other", 0.5))
            return (priority, result.score)
        
        return max(results, key=sort_key)
    
    def get_stats(self) -> Dict:
        """Get retrieval statistics."""
        return {
            "total_queries": self.stats.total_queries,
            "advisory_queries": self.stats.advisory_queries,
            "performance_queries": self.stats.performance_queries,
            "factual_queries": self.stats.factual_queries,
            "avg_retrieval_time": self.stats.avg_retrieval_time,
            "avg_chunks_retrieved": self.stats.avg_chunks_retrieved,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses
        }
    
    def reset_stats(self):
        """Reset retrieval statistics."""
        self.stats = RetrievalStats()
