"""
Test suite for Phase 4 Context Packer.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase4_retrieval.context_packer import ContextPacker
from phase4_retrieval.types import RouteLabel, RetrievalResult, ContextBundle


class TestContextPacker:
    """Test suite for ContextPacker functionality."""
    
    @pytest.fixture
    def context_packer(self):
        """Create context packer instance for testing."""
        return ContextPacker()
    
    @pytest.fixture
    def sample_retrieval_results(self):
        """Create sample retrieval results."""
        return [
            RetrievalResult(
                chunk_id='chunk_1',
                text='ELSS is a tax-saving mutual fund scheme under Section 80C.',
                score=0.9,
                metadata={'doc_id': 'doc1', 'source_url': 'https://example.com/factsheet.pdf'},
                source_url='https://example.com/factsheet.pdf',
                doc_type='factsheet'
            ),
            RetrievalResult(
                chunk_id='chunk_2',
                text='Investors can claim tax deduction up to Rs. 1.5 lakh under ELSS.',
                score=0.8,
                metadata={'doc_id': 'doc2', 'source_url': 'https://example.com/kii.pdf'},
                source_url='https://example.com/kii.pdf',
                doc_type='kii'
            )
        ]
    
    def test_initialization(self, context_packer):
        """Test context packer initialization."""
        assert context_packer is not None
        assert hasattr(context_packer, 'config')
        assert 'system_prompts' in context_packer.config
        assert RouteLabel.ADVISORY in context_packer.config['system_prompts']
    
    def test_build_context_factual(self, context_packer, sample_retrieval_results):
        """Test context building for factual queries."""
        query = "What is ELSS?"
        
        context_bundle = context_packer.build_context(
            query=query,
            route_label=RouteLabel.FACTUAL,
            retrieval_results=sample_retrieval_results
        )
        
        assert isinstance(context_bundle, ContextBundle)
        assert context_bundle.query == query
        assert context_bundle.route_label == RouteLabel.FACTUAL
        assert context_bundle.primary_chunk is not None
        assert len(context_bundle.secondary_chunks) == 1
        assert context_bundle.system_prompt is not None
        assert context_bundle.user_context is not None
        assert context_bundle.citation_url == 'https://example.com/factsheet.pdf'
    
    def test_build_context_advisory_no_results(self, context_packer):
        """Test context building for advisory queries with no retrieval results."""
        query = "Which mutual fund is best for investment?"
        
        context_bundle = context_packer.build_context(
            query=query,
            route_label=RouteLabel.ADVISORY,
            retrieval_results=[]
        )
        
        assert context_bundle.route_label == RouteLabel.ADVISORY
        assert context_bundle.primary_chunk is None
        assert context_bundle.secondary_chunks == []
        assert context_bundle.citation_url is None
    
    def test_build_context_performance(self, context_packer, sample_retrieval_results):
        """Test context building for performance queries."""
        query = "What are the returns of ELSS?"
        
        context_bundle = context_packer.build_context(
            query=query,
            route_label=RouteLabel.PERFORMANCE,
            retrieval_results=sample_retrieval_results
        )
        
        assert context_bundle.route_label == RouteLabel.PERFORMANCE
        assert context_bundle.primary_chunk is not None
        assert context_bundle.citation_url == 'https://example.com/factsheet.pdf'
    
    def test_build_refusal_response(self, context_packer):
        """Test refusal response building."""
        query = "Which mutual fund should I invest in?"
        
        context_bundle = context_packer.build_refusal_response(query)
        
        assert context_bundle.route_label == RouteLabel.ADVISORY
        assert context_bundle.query == query
        assert context_bundle.primary_chunk is None
        assert context_bundle.secondary_chunks == []
        assert context_bundle.citation_url is None
        assert "cannot provide investment advice" in context_bundle.user_context.lower()
    
    def test_build_performance_response(self, context_packer):
        """Test performance response building."""
        query = "What are the returns?"
        factsheet_url = "https://example.com/factsheet.pdf"
        
        context_bundle = context_packer.build_performance_response(query, factsheet_url)
        
        assert context_bundle.route_label == RouteLabel.PERFORMANCE
        assert context_bundle.query == query
        assert context_bundle.citation_url == factsheet_url
        assert factsheet_url in context_bundle.user_context
        assert "official factsheet" in context_bundle.user_context.lower()
    
    def test_select_chunks(self, context_packer, sample_retrieval_results):
        """Test chunk selection logic."""
        primary_chunk, secondary_chunks = context_packer._select_chunks(sample_retrieval_results)
        
        assert primary_chunk.chunk_id == 'chunk_1'  # First/highest scoring
        assert len(secondary_chunks) == 1
        assert secondary_chunks[0].chunk_id == 'chunk_2'
    
    def test_select_chunks_empty(self, context_packer):
        """Test chunk selection with empty results."""
        primary_chunk, secondary_chunks = context_packer._select_chunks([])
        
        assert primary_chunk is None
        assert secondary_chunks == []
    
    def test_build_system_prompt_factual(self, context_packer, sample_retrieval_results):
        """Test system prompt building for factual queries."""
        primary_chunk = sample_retrieval_results[0]
        
        system_prompt = context_packer._build_system_prompt(RouteLabel.FACTUAL, primary_chunk)
        
        assert "factual answers" in system_prompt.lower()
        assert "only on the provided context" in system_prompt.lower()
        assert primary_chunk.source_url in system_prompt
    
    def test_build_system_prompt_advisory(self, context_packer):
        """Test system prompt building for advisory queries."""
        system_prompt = context_packer._build_system_prompt(RouteLabel.ADVISORY, None)
        
        assert "must not provide investment advice" in system_prompt.lower()
        assert "refusal template" in system_prompt.lower()
    
    def test_build_system_prompt_performance(self, context_packer, sample_retrieval_results):
        """Test system prompt building for performance queries."""
        primary_chunk = sample_retrieval_results[0]
        
        system_prompt = context_packer._build_system_prompt(RouteLabel.PERFORMANCE, primary_chunk)
        
        assert "brief factual response" in system_prompt.lower()
        assert "official factsheet url" in system_prompt.lower()
    
    def test_format_chunk(self, context_packer, sample_retrieval_results):
        """Test chunk formatting."""
        chunk = sample_retrieval_results[0]
        
        formatted = context_packer._format_chunk(chunk)
        
        assert chunk.text in formatted
        assert chunk.source_url in formatted
        assert chunk.doc_type in formatted
        assert f"Score: {chunk.score:.3f}" in formatted
    
    def test_determine_citation_url(self, context_packer, sample_retrieval_results):
        """Test citation URL determination."""
        chunk = sample_retrieval_results[0]
        
        citation_url = context_packer._determine_citation_url(chunk)
        
        assert citation_url == chunk.source_url
    
    def test_determine_citation_url_none(self, context_packer):
        """Test citation URL determination with no chunk."""
        citation_url = context_packer._determine_citation_url(None)
        assert citation_url is None
    
    def test_build_user_context_length_limit(self, context_packer, sample_retrieval_results):
        """Test user context length limiting."""
        # Create a very long query
        long_query = "What is " + "very " * 1000 + "long query?"
        
        context_bundle = context_packer.build_context(
            query=long_query,
            route_label=RouteLabel.FACTUAL,
            retrieval_results=sample_retrieval_results
        )
        
        # Should be truncated to max length
        assert len(context_bundle.user_context) <= context_packer.config['max_context_length']
        assert context_bundle.user_context.endswith('...')
    
    def test_validate_context_bundle_valid(self, context_packer, sample_retrieval_results):
        """Test validation of valid context bundle."""
        context_bundle = context_packer.build_context(
            query="What is ELSS?",
            route_label=RouteLabel.FACTUAL,
            retrieval_results=sample_retrieval_results
        )
        
        validation = context_packer.validate_context_bundle(context_bundle)
        
        assert validation['valid'] is True
        assert len(validation['issues']) == 0
    
    def test_validate_context_bundle_missing_query(self, context_packer):
        """Test validation of context bundle with missing query."""
        context_bundle = ContextBundle(
            query="",
            route_label=RouteLabel.FACTUAL,
            system_prompt="test",
            user_context="test"
        )
        
        validation = context_packer.validate_context_bundle(context_bundle)
        
        assert validation['valid'] is False
        assert "Missing query" in validation['issues']
    
    def test_validate_context_bundle_factual_no_chunk(self, context_packer):
        """Test validation of factual context bundle with no primary chunk."""
        context_bundle = ContextBundle(
            query="What is ELSS?",
            route_label=RouteLabel.FACTUAL,
            primary_chunk=None,
            system_prompt="test",
            user_context="test"
        )
        
        validation = context_packer.validate_context_bundle(context_bundle)
        
        assert validation['valid'] is False
        assert "Factual queries require primary chunk" in validation['issues']
    
    def test_validate_context_bundle_performance_no_citation(self, context_packer):
        """Test validation of performance context bundle with no citation."""
        context_bundle = ContextBundle(
            query="What are returns?",
            route_label=RouteLabel.PERFORMANCE,
            system_prompt="test",
            user_context="test",
            citation_url=None
        )
        
        validation = context_packer.validate_context_bundle(context_bundle)
        
        assert validation['valid'] is False
        assert "Performance queries require citation URL" in validation['issues']
    
    def test_validate_context_bundle_too_long(self, context_packer):
        """Test validation of context bundle that's too long."""
        long_context = "x" * 5000  # Exceeds default max length
        
        context_bundle = ContextBundle(
            query="Test query",
            route_label=RouteLabel.FACTUAL,
            system_prompt="test",
            user_context=long_context
        )
        
        validation = context_packer.validate_context_bundle(context_bundle)
        
        assert validation['valid'] is False
        assert "exceeds max length" in validation['issues'][0].lower()
    
    def test_custom_config(self):
        """Test context packer with custom configuration."""
        custom_config = {
            'max_context_length': 1000,
            'include_metadata': False,
            'citation_format': 'chunk_id',
            'educational_links': ['https://custom-link.com']
        }
        
        packer = ContextPacker(custom_config)
        
        assert packer.config['max_context_length'] == 1000
        assert packer.config['include_metadata'] is False
        assert packer.config['citation_format'] == 'chunk_id'
        assert packer.config['educational_links'] == ['https://custom-link.com']
    
    def test_chunk_id_citation_format(self):
        """Test citation format using chunk ID."""
        packer = ContextPacker({'citation_format': 'chunk_id'})
        
        chunk = RetrievalResult(
            chunk_id='test_chunk_123',
            text='Test text',
            score=0.9,
            metadata={},
            source_url='https://example.com',
            doc_type='factsheet'
        )
        
        citation_url = packer._determine_citation_url(chunk)
        
        assert citation_url == 'chunk:test_chunk_123'
    
    def test_metadata_inclusion_disabled(self):
        """Test chunk formatting without metadata."""
        packer = ContextPacker({'include_metadata': False})
        
        chunk = RetrievalResult(
            chunk_id='chunk_1',
            text='Test text',
            score=0.9,
            metadata={},
            source_url='https://example.com',
            doc_type='factsheet'
        )
        
        formatted = packer._format_chunk(chunk)
        
        assert chunk.text in formatted
        assert chunk.source_url not in formatted
        assert chunk.doc_type not in formatted
        assert "Score:" not in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
