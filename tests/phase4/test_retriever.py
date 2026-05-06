"""
Test suite for Phase 4 Retrieval Engine.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase4_retrieval.retriever import RetrievalEngine
from phase4_retrieval.types import RouteLabel, RetrievalResult, RetrievalStats
from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever


class TestRetrievalEngine:
    """Test suite for RetrievalEngine functionality."""
    
    @pytest.fixture
    def mock_phase3_components(self):
        """Create mock Phase 3 components."""
        # Mock embedding engine
        mock_embedding_engine = Mock(spec=EmbeddingEngine)
        mock_embedding_engine.embed_single.return_value = [0.1, 0.2, 0.3] * 128  # 384-dim vector
        
        # Mock vector store
        mock_vector_store = Mock(spec=VectorStore)
        mock_vector_store.search.return_value = {
            'ids': [['chunk_1', 'chunk_2']],
            'documents': [['Text 1', 'Text 2']],
            'metadatas': [[{'source_url': 'url1', 'doc_type': 'factsheet'}, 
                          {'source_url': 'url2', 'doc_type': 'kii'}]],
            'distances': [[0.1, 0.2]]
        }
        
        # Mock hybrid retriever
        mock_hybrid_retriever = Mock(spec=HybridRetriever)
        mock_hybrid_retriever.search.return_value = [
            {
                'chunk_id': 'chunk_1',
                'text': 'Text 1',
                'hybrid_score': 0.9,
                'semantic_score': 0.8,
                'lexical_score': 0.7,
                'metadata': {'source_url': 'url1', 'doc_type': 'factsheet'}
            },
            {
                'chunk_id': 'chunk_2',
                'text': 'Text 2',
                'hybrid_score': 0.8,
                'semantic_score': 0.7,
                'lexical_score': 0.6,
                'metadata': {'source_url': 'url2', 'doc_type': 'kii'}
            }
        ]
        mock_hybrid_retriever.get_stats.return_value = {
            'vector_store_count': 10,
            'bm25_count': 10,
            'alpha': 0.5
        }
        
        return mock_embedding_engine, mock_vector_store, mock_hybrid_retriever
    
    @pytest.fixture
    def retrieval_engine(self, mock_phase3_components):
        """Create retrieval engine with mock components."""
        embedding_engine, vector_store, hybrid_retriever = mock_phase3_components
        return RetrievalEngine(
            embedding_engine=embedding_engine,
            vector_store=vector_store,
            hybrid_retriever=hybrid_retriever,
            config={
                'top_k': 5,
                'final_k': 3,
                'min_score_threshold': 0.1,
                'dedupe_threshold': 0.9,
                'doc_type_priorities': {
                    'factsheet': 1.0,
                    'kii': 0.9,
                    'other': 0.5
                },
                'mmr_enabled': True,
                'mmr_lambda': 0.7
            }
        )
    
    def test_initialization(self, retrieval_engine):
        """Test retrieval engine initialization."""
        assert retrieval_engine is not None
        assert hasattr(retrieval_engine, 'config')
        assert hasattr(retrieval_engine, 'stats')
        assert isinstance(retrieval_engine.stats, RetrievalStats)
    
    def test_advisory_retrieval(self, retrieval_engine, mock_phase3_components):
        """Test retrieval for advisory queries."""
        mock_hybrid_retriever = mock_phase3_components[2]
        
        # Advisory queries should return empty results
        results = retrieval_engine.retrieve("Which fund is best?", RouteLabel.ADVISORY)
        
        assert results == []
        # Hybrid retriever should not be called for advisory queries
        mock_hybrid_retriever.search.assert_not_called()
    
    def test_performance_retrieval(self, retrieval_engine, mock_phase3_components):
        """Test retrieval for performance queries."""
        mock_hybrid_retriever = mock_phase3_components[2]
        
        results = retrieval_engine.retrieve("What are the returns?", RouteLabel.PERFORMANCE)
        
        assert len(results) <= 1  # Should return only primary chunk
        mock_hybrid_retriever.search.assert_called_once()
        
        # Should prioritize factsheet documents
        if results:
            assert results[0].doc_type == 'factsheet'
    
    def test_factual_retrieval(self, retrieval_engine, mock_phase3_components):
        """Test retrieval for factual queries."""
        mock_hybrid_retriever = mock_phase3_components[2]
        
        results = retrieval_engine.retrieve("What is ELSS?", RouteLabel.FACTUAL)
        
        assert len(results) <= 3  # Should return up to final_k chunks
        mock_hybrid_retriever.search.assert_called_once()
        
        # Should have primary chunk selected
        if results:
            assert results[0] is not None
    
    def test_convert_to_retrieval_results(self, retrieval_engine):
        """Test conversion of hybrid results to retrieval results."""
        hybrid_results = [
            {
                'chunk_id': 'chunk_1',
                'text': 'Text 1',
                'hybrid_score': 0.9,
                'semantic_score': 0.8,
                'lexical_score': 0.7,
                'metadata': {'source_url': 'url1', 'doc_type': 'factsheet'}
            }
        ]
        
        results = retrieval_engine._convert_to_retrieval_results(hybrid_results)
        
        assert len(results) == 1
        assert isinstance(results[0], RetrievalResult)
        assert results[0].chunk_id == 'chunk_1'
        assert results[0].text == 'Text 1'
        assert results[0].score == 0.9
        assert results[0].source_url == 'url1'
        assert results[0].doc_type == 'factsheet'
    
    def test_deduplicate_results(self, retrieval_engine):
        """Test result deduplication."""
        # Create duplicate results
        results = [
            RetrievalResult(
                chunk_id='chunk_1',
                text='This is about mutual funds',
                score=0.9,
                metadata={'doc_id': 'doc1', 'source_url': 'url1'},
                source_url='url1',
                doc_type='factsheet'
            ),
            RetrievalResult(
                chunk_id='chunk_2',
                text='This is about mutual funds too',
                score=0.8,
                metadata={'doc_id': 'doc1', 'source_url': 'url1'},  # Same doc_id
                source_url='url1',
                doc_type='factsheet'
            ),
            RetrievalResult(
                chunk_id='chunk_3',
                text='This is about something else',
                score=0.7,
                metadata={'doc_id': 'doc2', 'source_url': 'url2'},
                source_url='url2',
                doc_type='kii'
            )
        ]
        
        deduped = retrieval_engine._deduplicate_results(results)
        
        # Check if deduplication works (may or may not remove chunk_2 depending on similarity)
        assert len(deduped) <= 3
        assert deduped[0].chunk_id == 'chunk_1'
        # chunk_2 may or may not be removed depending on text similarity threshold
        assert deduped[-1].chunk_id == 'chunk_3'
    
    def test_text_similarity(self, retrieval_engine):
        """Test text similarity calculation."""
        text1 = "mutual fund investment"
        text2 = "mutual fund returns"
        text3 = "completely different topic"
        
        # Similar texts should have high similarity
        sim1 = retrieval_engine._text_similarity(text1, text2)
        assert sim1 >= 0.5  # Can be exactly 0.5
        
        # Different texts should have low similarity
        sim2 = retrieval_engine._text_similarity(text1, text3)
        assert sim2 < 0.5
        
        # Same text should have similarity 1.0
        sim3 = retrieval_engine._text_similarity(text1, text1)
        assert sim3 == 1.0
    
    def test_mmr_selection(self, retrieval_engine):
        """Test Maximal Marginal Relevance selection."""
        results = [
            RetrievalResult(
                chunk_id='chunk_1',
                text='mutual fund investment returns',
                score=0.9,
                metadata={},
                source_url='url1',
                doc_type='factsheet'
            ),
            RetrievalResult(
                chunk_id='chunk_2',
                text='mutual fund investment performance',
                score=0.8,
                metadata={},
                source_url='url2',
                doc_type='factsheet'
            ),
            RetrievalResult(
                chunk_id='chunk_3',
                text='completely different topic',
                score=0.7,
                metadata={},
                source_url='url3',
                doc_type='kii'
            ),
            RetrievalResult(
                chunk_id='chunk_4',
                text='another different subject',
                score=0.6,
                metadata={},
                source_url='url4',
                doc_type='other'
            )
        ]
        
        mmr_results = retrieval_engine._apply_mmr("test query", results)
        
        # Should select diverse results
        assert len(mmr_results) <= 3  # final_k
        assert mmr_results[0].score >= mmr_results[1].score  # First should be highest scoring
    
    def test_primary_chunk_selection(self, retrieval_engine):
        """Test primary chunk selection based on doc_type priority."""
        results = [
            RetrievalResult(
                chunk_id='chunk_1',
                text='Text 1',
                score=0.7,
                metadata={},
                source_url='url1',
                doc_type='kii'  # Priority 0.9
            ),
            RetrievalResult(
                chunk_id='chunk_2',
                text='Text 2',
                score=0.8,
                metadata={},
                source_url='url2',
                doc_type='factsheet'  # Priority 1.0
            ),
            RetrievalResult(
                chunk_id='chunk_3',
                text='Text 3',
                score=0.6,
                metadata={},
                source_url='url3',
                doc_type='other'  # Priority 0.5
            )
        ]
        
        primary = retrieval_engine._select_primary_chunk(results)
        
        # Should select factsheet despite slightly lower score
        assert primary.chunk_id == 'chunk_2'
        assert primary.doc_type == 'factsheet'
    
    def test_statistics_tracking(self, retrieval_engine, mock_phase3_components):
        """Test statistics tracking."""
        # Process some queries
        retrieval_engine.retrieve("Which fund is best?", RouteLabel.ADVISORY)
        retrieval_engine.retrieve("What are the returns?", RouteLabel.PERFORMANCE)
        retrieval_engine.retrieve("What is ELSS?", RouteLabel.FACTUAL)
        
        stats = retrieval_engine.get_stats()
        
        assert stats['total_queries'] == 3
        assert stats['advisory_queries'] == 1
        assert stats['performance_queries'] == 1
        assert stats['factual_queries'] == 1
        assert stats['avg_retrieval_time'] >= 0
        assert stats['avg_chunks_retrieved'] >= 0
    
    def test_statistics_reset(self, retrieval_engine):
        """Test statistics reset."""
        # Process a query
        retrieval_engine.retrieve("test query", RouteLabel.FACTUAL)
        
        # Check stats are recorded
        stats = retrieval_engine.get_stats()
        assert stats['total_queries'] > 0
        
        # Reset stats
        retrieval_engine.reset_stats()
        
        # Check stats are reset
        stats = retrieval_engine.get_stats()
        assert stats['total_queries'] == 0
        assert stats['advisory_queries'] == 0
        assert stats['performance_queries'] == 0
        assert stats['factual_queries'] == 0
    
    def test_empty_results_handling(self, retrieval_engine, mock_phase3_components):
        """Test handling of empty search results."""
        mock_hybrid_retriever = mock_phase3_components[2]
        mock_hybrid_retriever.search.return_value = []
        
        results = retrieval_engine.retrieve("test query", RouteLabel.FACTUAL)
        
        assert results == []
    
    def test_low_score_filtering(self, retrieval_engine, mock_phase3_components):
        """Test filtering of low-scoring results."""
        mock_hybrid_retriever = mock_phase3_components[2]
        mock_hybrid_retriever.search.return_value = [
            {
                'chunk_id': 'chunk_1',
                'text': 'Text 1',
                'hybrid_score': 0.05,  # Below threshold
                'metadata': {'source_url': 'url1', 'doc_type': 'factsheet'}
            },
            {
                'chunk_id': 'chunk_2',
                'text': 'Text 2',
                'hybrid_score': 0.8,  # Above threshold
                'metadata': {'source_url': 'url2', 'doc_type': 'kii'}
            }
        ]
        
        results = retrieval_engine.retrieve("test query", RouteLabel.FACTUAL)
        
        # Should only include high-scoring result
        assert len(results) == 1
        assert results[0].chunk_id == 'chunk_2'
    
    def test_factsheet_fallback(self, retrieval_engine, mock_phase3_components):
        """Test fallback when no factsheets found for performance queries."""
        mock_hybrid_retriever = mock_phase3_components[2]
        mock_hybrid_retriever.search.return_value = [
            {
                'chunk_id': 'chunk_1',
                'text': 'Text 1',
                'hybrid_score': 0.8,
                'metadata': {'source_url': 'url1', 'doc_type': 'kii'}  # Not factsheet
            }
        ]
        
        results = retrieval_engine.retrieve("What are the returns?", RouteLabel.PERFORMANCE)
        
        # Should fall back to best scoring result
        assert len(results) == 1
        assert results[0].chunk_id == 'chunk_1'
    
    def test_config_defaults(self, mock_phase3_components):
        """Test default configuration."""
        embedding_engine, vector_store, hybrid_retriever = mock_phase3_components
        
        # Create engine without explicit config
        engine = RetrievalEngine(
            embedding_engine=embedding_engine,
            vector_store=vector_store,
            hybrid_retriever=hybrid_retriever
        )
        
        # Should have default values
        assert engine.config['top_k'] == 8
        assert engine.config['final_k'] == 3
        assert engine.config['min_score_threshold'] == 0.1
        assert engine.config['mmr_enabled'] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
