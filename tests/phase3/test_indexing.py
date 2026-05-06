"""
Tests for Phase 3 indexing functionality.
"""

import json
import tempfile
from pathlib import Path
import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever
from phase3_indexing.hybrid import BM25Index


class TestEmbeddingEngine:
    """Test the embedding engine."""
    
    def test_initialization(self):
        """Test embedding engine initialization."""
        engine = EmbeddingEngine(model_name="BAAI/bge-small-en-v1.5", device="cpu")
        assert engine.model is not None
        assert engine.model_name == "BAAI/bge-small-en-v1.5"
        assert engine.device == "cpu"
    
    def test_embed_single(self):
        """Test embedding a single text."""
        engine = EmbeddingEngine(model_name="BAAI/bge-small-en-v1.5", device="cpu")
        text = "This is a test document about mutual funds."
        embedding = engine.embed_single(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0  # Should have non-zero dimensions
        assert all(isinstance(x, float) for x in embedding)
    
    def test_embed_chunks(self):
        """Test embedding multiple chunks."""
        engine = EmbeddingEngine(model_name="BAAI/bge-small-en-v1.5", device="cpu")
        
        chunks = [
            {"chunk_id": "chunk_1", "text": "Mutual funds are investment vehicles."},
            {"chunk_id": "chunk_2", "text": "Exit load is a fee charged when redeeming units."},
            {"chunk_id": "chunk_3", "text": "NAV is the net asset value of a mutual fund."}
        ]
        
        embedded_chunks = engine.embed_chunks(chunks, batch_size=2)
        
        assert len(embedded_chunks) == 3
        for chunk in embedded_chunks:
            assert "embedding" in chunk
            assert isinstance(chunk["embedding"], list)
            assert len(chunk["embedding"]) > 0


class TestVectorStore:
    """Test the vector store functionality."""
    
    @pytest.fixture
    def temp_vector_store(self):
        """Create a temporary vector store for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = VectorStore(
                persist_directory=Path(temp_dir) / "chroma",
                collection_name="test_collection"
            )
            yield store
    
    def test_initialization(self, temp_vector_store):
        """Test vector store initialization."""
        assert temp_vector_store.collection is not None
        assert temp_vector_store.collection_name == "test_collection"
    
    def test_add_and_search(self, temp_vector_store):
        """Test adding chunks and searching."""
        # Create test chunks with embeddings
        chunks = [
            {
                "chunk_id": "chunk_1",
                "text": "Mutual funds pool money from many investors.",
                "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                "doc_type": "factsheet",
                "source_url": "https://example.com/factsheet1"
            },
            {
                "chunk_id": "chunk_2", 
                "text": "Exit load charges apply for early redemption.",
                "embedding": [0.2, 0.3, 0.4, 0.5, 0.6],
                "doc_type": "factsheet",
                "source_url": "https://example.com/factsheet2"
            }
        ]
        
        # Add chunks
        temp_vector_store.add_chunks(chunks)
        
        # Search
        query_embedding = [0.15, 0.25, 0.35, 0.45, 0.55]
        results = temp_vector_store.search(query_embedding, n_results=2)
        
        assert 'ids' in results
        assert 'distances' in results
        assert len(results['ids'][0]) <= 2


class TestBM25Index:
    """Test the BM25 index functionality."""
    
    @pytest.fixture
    def temp_bm25_index(self):
        """Create a temporary BM25 index for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            index = BM25Index(Path(temp_dir))
            yield index
    
    def test_initialization(self, temp_bm25_index):
        """Test BM25 index initialization."""
        assert temp_bm25_index.index is not None
    
    def test_add_and_search(self, temp_bm25_index):
        """Test adding documents and searching."""
        chunks = [
            {
                "chunk_id": "chunk_1",
                "text": "Mutual funds pool money from many investors to purchase securities.",
                "doc_type": "factsheet",
                "source_url": "https://example.com/factsheet1"
            },
            {
                "chunk_id": "chunk_2",
                "text": "Exit load is a fee charged when you redeem mutual fund units early.",
                "doc_type": "factsheet", 
                "source_url": "https://example.com/factsheet2"
            }
        ]
        
        # Add documents
        temp_bm25_index.add_documents(chunks)
        
        # Search
        results = temp_bm25_index.search("mutual fund exit load", limit=2)
        
        assert len(results) <= 2
        for result in results:
            assert "chunk_id" in result
            assert "text" in result
            assert "score" in result


class TestHybridRetriever:
    """Test the hybrid retriever functionality."""
    
    @pytest.fixture
    def temp_hybrid_retriever(self):
        """Create a temporary hybrid retriever for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize components
            embed_engine = EmbeddingEngine(model_name="BAAI/bge-small-en-v1.5", device="cpu")
            vector_store = VectorStore(
                persist_directory=Path(temp_dir) / "chroma",
                collection_name="test_collection"
            )
            bm25_index = BM25Index(Path(temp_dir) / "bm25")
            
            # Create retriever
            retriever = HybridRetriever(
                embedding_engine=embed_engine,
                vector_store=vector_store,
                bm25_index=bm25_index,
                alpha=0.5
            )
            
            yield retriever
    
    def test_hybrid_search(self, temp_hybrid_retriever):
        """Test hybrid search functionality."""
        # Create test chunks
        chunks = [
            {
                "chunk_id": "chunk_1",
                "text": "Mutual funds pool money from many investors to purchase securities.",
                "doc_type": "factsheet",
                "source_url": "https://example.com/factsheet1"
            },
            {
                "chunk_id": "chunk_2",
                "text": "Exit load is a fee charged when you redeem mutual fund units early.",
                "doc_type": "factsheet",
                "source_url": "https://example.com/factsheet2"
            }
        ]
        
        # Embed chunks
        embedded_chunks = temp_hybrid_retriever.embedding_engine.embed_chunks(chunks)
        
        # Add to vector store and BM25 index
        temp_hybrid_retriever.vector_store.add_chunks(embedded_chunks)
        temp_hybrid_retriever.bm25_index.add_documents(chunks)
        
        # Perform hybrid search
        results = temp_hybrid_retriever.search("mutual fund exit load", top_k=2)
        
        assert len(results) <= 2
        for result in results:
            assert "chunk_id" in result
            assert "text" in result
            assert "hybrid_score" in result
            assert 0 <= result["hybrid_score"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
