"""
Phase 3: Embeddings and vector store

This phase handles:
- Embedding chunks using sentence-transformers
- Storing vectors in ChromaDB
- Building BM25 index for hybrid retrieval
"""

from .embed import EmbeddingEngine
from .vector_store import VectorStore
from .hybrid import HybridRetriever

__all__ = [
    "EmbeddingEngine",
    "VectorStore", 
    "HybridRetriever",
    "BM25Index"
]
