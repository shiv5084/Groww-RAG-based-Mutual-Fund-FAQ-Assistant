"""
Quick integration test for Phase 3 functionality.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever
from phase3_indexing.hybrid import BM25Index
import tempfile
import json

def test_integration():
    """Test the complete Phase 3 integration."""
    print("Running Phase 3 Integration Test...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. Test Embedding Engine
        print("1. Testing Embedding Engine...")
        embed_engine = EmbeddingEngine(model_name="BAAI/bge-small-en-v1.5", device="cpu")
        
        test_chunks = [
            {
                "chunk_id": "test_chunk_1",
                "text": "Mutual funds pool money from many investors to purchase securities.",
                "doc_type": "factsheet",
                "source_url": "https://example.com/factsheet1"
            },
            {
                "chunk_id": "test_chunk_2",
                "text": "Exit load is a fee charged when you redeem mutual fund units early.",
                "doc_type": "factsheet",
                "source_url": "https://example.com/factsheet2"
            }
        ]
        
        # Embed chunks
        embedded_chunks = embed_engine.embed_chunks(test_chunks)
        assert len(embedded_chunks) == 2
        assert all('embedding' in chunk for chunk in embedded_chunks)
        print("PASS: Embedding Engine")
        
        # 2. Test Vector Store
        print("2. Testing Vector Store...")
        vector_store = VectorStore(
            persist_directory=temp_path / "chroma",
            collection_name="test_collection"
        )
        vector_store.add_chunks(embedded_chunks)
        
        # Test search
        query_embedding = embed_engine.embed_single("mutual fund")
        results = vector_store.search(query_embedding, n_results=2)
        assert 'ids' in results
        assert len(results['ids'][0]) <= 2
        print("PASS: Vector Store")
        
        # 3. Test BM25 Index
        print("3. Testing BM25 Index...")
        bm25_index = BM25Index(temp_path / "bm25")
        bm25_index.add_documents(test_chunks)
        
        # Test search
        bm25_results = bm25_index.search("mutual fund exit load", limit=2)
        assert len(bm25_results) <= 2
        assert all('chunk_id' in result for result in bm25_results)
        print("PASS: BM25 Index")
        
        # 4. Test Hybrid Retrieval
        print("4. Testing Hybrid Retrieval...")
        hybrid_retriever = HybridRetriever(
            embedding_engine=embed_engine,
            vector_store=vector_store,
            bm25_index=bm25_index,
            alpha=0.5
        )
        
        # Test hybrid search
        hybrid_results = hybrid_retriever.search("mutual fund exit load", top_k=2)
        assert len(hybrid_results) <= 2
        assert all('hybrid_score' in result for result in hybrid_results)
        assert all(0 <= result['hybrid_score'] <= 1 for result in hybrid_results)
        print("PASS: Hybrid Retrieval")
        
        # 5. Test Statistics
        print("5. Testing Statistics...")
        stats = hybrid_retriever.get_stats()
        assert 'vector_store_count' in stats
        assert 'bm25_count' in stats
        assert 'alpha' in stats
        assert stats['vector_store_count'] == 2
        assert stats['bm25_count'] == 2
        assert stats['alpha'] == 0.5
        print("PASS: Statistics")
        
        print("\nAll Phase 3 Integration Tests PASSED!")
        print(f"Final Stats: {stats}")
        
        return True

if __name__ == "__main__":
    test_integration()
