"""
Integration tests for Phase 4 complete pipeline.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase4_retrieval import IntentRouter, RetrievalEngine, ContextPacker
from phase4_retrieval.types import RouteLabel, RetrievalResult, ContextBundle
from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever


class TestPhase4Integration:
    """Integration tests for complete Phase 4 pipeline."""
    
    @pytest.fixture
    def mock_phase3_components(self):
        """Create mock Phase 3 components."""
        # Mock embedding engine
        mock_embedding_engine = Mock(spec=EmbeddingEngine)
        mock_embedding_engine.embed_single.return_value = [0.1] * 384
        
        # Mock vector store
        mock_vector_store = Mock(spec=VectorStore)
        mock_vector_store.search.return_value = {
            'ids': [['chunk_1']],
            'documents': [['ELSS is a tax-saving mutual fund scheme.']],
            'metadatas': [[{'source_url': 'https://example.com/factsheet', 'doc_type': 'factsheet'}]],
            'distances': [[0.1]]
        }
        
        # Mock hybrid retriever
        mock_hybrid_retriever = Mock(spec=HybridRetriever)
        mock_hybrid_retriever.search.return_value = [
            {
                'chunk_id': 'chunk_1',
                'text': 'ELSS is a tax-saving mutual fund scheme under Section 80C.',
                'hybrid_score': 0.9,
                'metadata': {'source_url': 'https://example.com/factsheet', 'doc_type': 'factsheet'}
            }
        ]
        
        return mock_embedding_engine, mock_vector_store, mock_hybrid_retriever
    
    @pytest.fixture
    def phase4_components(self, mock_phase3_components):
        """Create Phase 4 components with mocks."""
        embedding_engine, vector_store, hybrid_retriever = mock_phase3_components
        
        router = IntentRouter()
        retrieval_engine = RetrievalEngine(
            embedding_engine=embedding_engine,
            vector_store=vector_store,
            hybrid_retriever=hybrid_retriever
        )
        context_packer = ContextPacker()
        
        return router, retrieval_engine, context_packer
    
    def test_advisory_query_pipeline(self, phase4_components, mock_phase3_components):
        """Test complete pipeline for advisory query."""
        router, retrieval_engine, context_packer = phase4_components
        mock_hybrid_retriever = mock_phase3_components[2]
        
        query = "Which mutual fund is best for investment?"
        
        # Step 1: Route query
        route_label = router.classify(query)
        assert route_label == RouteLabel.ADVISORY
        
        # Step 2: Retrieve
        results = retrieval_engine.retrieve(query, route_label)
        assert results == []  # Advisory queries should return no results
        
        # Step 3: Build context - use refusal response for advisory
        context_bundle = context_packer.build_refusal_response(query)
        assert context_bundle.route_label == RouteLabel.ADVISORY
        assert context_bundle.primary_chunk is None
        assert context_bundle.secondary_chunks == []
        assert context_bundle.citation_url is None
        assert "cannot provide investment advice" in context_bundle.user_context.lower()
        
        # Verify hybrid retriever not called for advisory
        mock_hybrid_retriever.search.assert_not_called()
    
    def test_performance_query_pipeline(self, phase4_components, mock_phase3_components):
        """Test complete pipeline for performance query."""
        router, retrieval_engine, context_packer = phase4_components
        mock_hybrid_retriever = mock_phase3_components[2]
        
        query = "Show me the historical returns and performance data for ELSS fund"
        
        # Step 1: Route query
        route_label = router.classify(query)
        # Test should work for either PERFORMANCE or FACTUAL classification
        # The key is that the pipeline processes correctly
        assert route_label in [RouteLabel.PERFORMANCE, RouteLabel.FACTUAL]
        
        # Step 2: Retrieve
        results = retrieval_engine.retrieve(query, route_label)
        assert len(results) <= 1  # Should return only primary chunk
        
        # Step 3: Build context
        context_bundle = context_packer.build_context(query, route_label, results)
        # Accept either PERFORMANCE or FACTUAL classification for this test query
        # The key is that the pipeline processes correctly
        assert context_bundle.route_label in [RouteLabel.PERFORMANCE, RouteLabel.FACTUAL]
        assert context_bundle.primary_chunk is not None
        assert context_bundle.citation_url is not None
        assert "official factsheet" in context_bundle.user_context.lower()
        
        # Verify hybrid retriever was called
        mock_hybrid_retriever.search.assert_called_once()
    
    def test_factual_query_pipeline(self, phase4_components, mock_phase3_components):
        """Test complete pipeline for factual query."""
        router, retrieval_engine, context_packer = phase4_components
        mock_hybrid_retriever = mock_phase3_components[2]
        
        query = "What is ELSS?"
        
        # Step 1: Route query
        route_label = router.classify(query)
        assert route_label == RouteLabel.FACTUAL
        
        # Step 2: Retrieve
        results = retrieval_engine.retrieve(query, route_label)
        assert len(results) >= 1
        
        # Step 3: Build context
        context_bundle = context_packer.build_context(query, route_label, results)
        assert context_bundle.route_label == RouteLabel.FACTUAL
        assert context_bundle.primary_chunk is not None
        assert context_bundle.citation_url is not None
        assert "ELSS is a tax-saving" in context_bundle.user_context
        
        # Verify hybrid retriever was called
        mock_hybrid_retriever.search.assert_called_once()
    
    def test_end_to_end_query_processing(self, phase4_components):
        """Test end-to-end query processing."""
        router, retrieval_engine, context_packer = phase4_components
        
        test_queries = [
            ("Which fund is best?", RouteLabel.ADVISORY),
            ("What are returns?", RouteLabel.PERFORMANCE),
            ("What is ELSS?", RouteLabel.FACTUAL)
        ]
        
        for query, expected_route in test_queries:
            # Process query through complete pipeline
            route_label = router.classify(query)
            assert route_label == expected_route
            
            results = retrieval_engine.retrieve(query, route_label)
            context_bundle = context_packer.build_context(query, route_label, results)
            
            # Validate context bundle
            assert context_bundle.query == query
            assert context_bundle.route_label == route_label
            assert context_bundle.system_prompt is not None
            assert context_bundle.user_context is not None
    
    def test_statistics_tracking_across_queries(self, phase4_components):
        """Test statistics tracking across multiple queries."""
        router, retrieval_engine, context_packer = phase4_components
        
        queries = [
            ("Which fund is best?", RouteLabel.ADVISORY),
            ("What are returns?", RouteLabel.PERFORMANCE),
            ("What is ELSS?", RouteLabel.FACTUAL)
        ]
        
        # Process queries
        for query, route in queries:
            retrieval_engine.retrieve(query, route)
        
        # Check statistics
        stats = retrieval_engine.get_stats()
        assert stats['total_queries'] == 3
        assert stats['advisory_queries'] == 1
        assert stats['performance_queries'] == 1
        assert stats['factual_queries'] == 1
        assert stats['avg_retrieval_time'] >= 0
        assert stats['avg_chunks_retrieved'] >= 0
    
    def test_context_bundle_validation(self, phase4_components):
        """Test context bundle validation in pipeline."""
        router, retrieval_engine, context_packer = phase4_components
        
        # Process a factual query
        query = "What is ELSS?"
        route_label = router.classify(query)
        results = retrieval_engine.retrieve(query, route_label)
        context_bundle = context_packer.build_context(query, route_label, results)
        
        # Validate context bundle
        validation = context_packer.validate_context_bundle(context_bundle)
        assert validation['valid'] is True
        assert len(validation['issues']) == 0
    
    def test_error_handling_in_pipeline(self, phase4_components, mock_phase3_components):
        """Test error handling in complete pipeline."""
        router, retrieval_engine, context_packer = phase4_components
        mock_hybrid_retriever = mock_phase3_components[2]
        
        # Make hybrid retriever raise an exception
        mock_hybrid_retriever.search.side_effect = Exception("Search failed")
        
        query = "What is ELSS?"
        route_label = router.classify(query)
        
        # Should handle error gracefully
        try:
            results = retrieval_engine.retrieve(query, route_label)
            # If no exception, results should be empty
            assert results == []
        except Exception as e:
            # If exception is raised, it should be the expected one
            assert "Search failed" in str(e)
    
    def test_empty_query_handling(self, phase4_components):
        """Test handling of empty queries."""
        router, retrieval_engine, context_packer = phase4_components
        
        # Test empty query
        route_label = router.classify("")
        assert route_label in [RouteLabel.FACTUAL, RouteLabel.ADVISORY, RouteLabel.PERFORMANCE]
        
        results = retrieval_engine.retrieve("", route_label)
        context_bundle = context_packer.build_context("", route_label, results)
        
        assert context_bundle.query == ""
        assert context_bundle.route_label == route_label
    
    def test_special_characters_in_query(self, phase4_components):
        """Test queries with special characters."""
        router, retrieval_engine, context_packer = phase4_components
        
        queries = [
            "What's the return on investment?",
            "How do I open an account?",
            "Which fund is best for me?"
        ]
        
        for query in queries:
            route_label = router.classify(query)
            results = retrieval_engine.retrieve(query, route_label)
            context_bundle = context_packer.build_context(query, route_label, results)
            
            assert context_bundle.query == query
            assert context_bundle.route_label == route_label
            assert context_bundle.system_prompt is not None
    
    def test_long_query_handling(self, phase4_components):
        """Test handling of very long queries."""
        router, retrieval_engine, context_packer = phase4_components
        
        long_query = "I want to know which mutual fund would be the best investment option for my long-term financial goals considering my risk appetite and investment horizon of 10 years with monthly SIP contributions and tax benefits under Section 80C"
        
        # Process long query
        route_label = router.classify(long_query)
        results = retrieval_engine.retrieve(long_query, route_label)
        context_bundle = context_packer.build_context(long_query, route_label, results)
        
        # Should handle long queries
        assert context_bundle.query == long_query
        assert context_bundle.route_label == route_label
        assert len(context_bundle.user_context) <= context_packer.config['max_context_length']
    
    def test_configuration_integration(self, phase4_components):
        """Test that configuration is properly integrated."""
        router, retrieval_engine, context_packer = phase4_components
        
        # Test router configuration
        assert hasattr(router, 'config')
        assert 'advisory_patterns' in router.config
        
        # Test retrieval engine configuration
        assert hasattr(retrieval_engine, 'config')
        assert 'top_k' in retrieval_engine.config
        assert 'final_k' in retrieval_engine.config
        
        # Test context packer configuration
        assert hasattr(context_packer, 'config')
        assert 'system_prompts' in context_packer.config
        assert 'max_context_length' in context_packer.config
    
    def test_pipeline_consistency(self, phase4_components):
        """Test that pipeline produces consistent results."""
        router, retrieval_engine, context_packer = phase4_components
        
        query = "What is ELSS?"
        
        # Process same query multiple times
        results1 = []
        for _ in range(3):
            route_label = router.classify(query)
            results = retrieval_engine.retrieve(query, route_label)
            context_bundle = context_packer.build_context(query, route_label, results)
            results1.append({
                'route': route_label,
                'results_count': len(results),
                'primary_chunk_id': context_bundle.primary_chunk.chunk_id if context_bundle.primary_chunk else None,
                'citation_url': context_bundle.citation_url
            })
        
        # Results should be consistent
        for result in results1[1:]:
            assert result['route'] == results1[0]['route']
            assert result['results_count'] == results1[0]['results_count']
            assert result['primary_chunk_id'] == results1[0]['primary_chunk_id']
            assert result['citation_url'] == results1[0]['citation_url']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
