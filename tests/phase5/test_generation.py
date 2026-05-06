"""
Tests for Phase 5 Generation module.

Tests Groq LLM client, answer generator, and prompt templates.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase5_generation.generation.llm_client import LLMClient, GroqProvider
from phase5_generation.generation.generator import AnswerGenerator
from phase4_retrieval.types import ContextBundle, RouteLabel, RetrievalResult


class TestGroqProvider:
    """Test Groq provider functionality."""
    
    def test_groq_provider_validation(self):
        """Test Groq provider configuration validation."""
        # Test invalid API key
        with pytest.raises(ValueError):
            provider = GroqProvider(api_key="your_api_key_here")
            provider.validate_config()
    
    @patch.dict(os.environ, {
        'GROQ_API_KEY': 'test_groq_key_123',
        'LLM_MODEL': 'llama3-70b-8192'
    })
    def test_groq_provider_initialization(self):
        """Test Groq provider initialization."""
        provider = GroqProvider(api_key="test_key_123")
        assert provider.api_key == "test_key_123"
        assert provider.model == "llama3-70b-8192"
        assert provider.temperature == 0.2
        assert provider.max_tokens == 512


class TestLLMClient:
    """Test LLM client functionality."""
    
    @patch.dict(os.environ, {
        'GROQ_API_KEY': 'test_groq_key_123',
        'LLM_MODEL': 'llama3-70b-8192'
    })
    def test_llm_client_from_env(self):
        """Test LLM client creation from environment."""
        client = LLMClient.from_env()
        assert client.provider == "groq"
        assert client.model == "llama3-70b-8192"
        assert client.api_key == "test_groq_key_123"
    
    def test_llm_client_validate_env(self):
        """Test environment validation."""
        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'valid_groq_key_123'
        }):
            validation = LLMClient.validate_env()
            assert isinstance(validation, dict)
            assert 'groq' in validation
            assert validation['groq'] is True
    
    def test_llm_client_fallback_api_key(self):
        """Test fallback to LLM_API_KEY when GROQ_API_KEY not set."""
        with patch.dict(os.environ, {
            'LLM_API_KEY': 'fallback_key_123'
        }, clear=True):
            # Remove GROQ_API_KEY to test fallback
            if 'GROQ_API_KEY' in os.environ:
                del os.environ['GROQ_API_KEY']
            
            client = LLMClient()
            assert client.api_key == "fallback_key_123"


class TestAnswerGenerator:
    """Test answer generator functionality."""
    
    @pytest.fixture
    def mock_groq_client(self):
        """Create mock Groq client for testing."""
        mock_client = Mock(spec=LLMClient)
        mock_client.generate.return_value = "This is a test answer."
        mock_client.get_config_info.return_value = {
            "provider": "groq",
            "model": "llama3-70b-8192",
            "configured": True
        }
        return mock_client
    
    @pytest.fixture
    def sample_context_bundle(self):
        """Create sample context bundle for testing."""
        sample_chunk = RetrievalResult(
            chunk_id="test_chunk_1",
            text="HDFC Equity Fund is a large-cap equity scheme with minimum SIP of ₹500.",
            score=0.85,
            metadata={"scheme": "HDFC Equity Fund", "doc_type": "factsheet"},
            source_url="https://example.com/factsheet",
            doc_type="factsheet"
        )
        
        return ContextBundle(
            query="What is the minimum SIP amount?",
            route_label=RouteLabel.FACTUAL,
            primary_chunk=sample_chunk,
            citation_url="https://example.com/factsheet"
        )
    
    def test_generator_initialization(self, mock_groq_client):
        """Test answer generator initialization."""
        generator = AnswerGenerator(llm_client=mock_groq_client)
        assert generator.llm_client == mock_groq_client
        assert generator.system_prompt
        assert generator.user_prompt_template
        assert generator.refusal_template
    
    def test_factual_answer_generation(self, mock_groq_client, sample_context_bundle):
        """Test factual answer generation."""
        generator = AnswerGenerator(llm_client=mock_groq_client)
        
        result = generator.generate_answer(sample_context_bundle)
        
        assert result["answer"] == "This is a test answer."
        assert result["citation_url"] == "https://example.com/factsheet"
        assert result["refusal"] is False
        assert result["route"] == "factual"
        assert result["context_used"] is True
        assert "generation_time" in result
    
    def test_advisory_refusal_generation(self, mock_groq_client):
        """Test refusal generation for advisory queries."""
        advisory_bundle = ContextBundle(
            query="Which fund is better for investment?",
            route_label=RouteLabel.ADVISORY
        )
        
        generator = AnswerGenerator(llm_client=mock_groq_client)
        result = generator.generate_answer(advisory_bundle)
        
        assert result["refusal"] is True
        assert result["route"] == "advisory"
        assert result["context_used"] is False
        assert "educational" in result["answer"].lower()
    
    def test_performance_response_generation(self, mock_groq_client):
        """Test performance-only response generation."""
        performance_bundle = ContextBundle(
            query="What are the returns of HDFC Equity Fund?",
            route_label=RouteLabel.PERFORMANCE
        )
        
        generator = AnswerGenerator(llm_client=mock_groq_client)
        result = generator.generate_answer(performance_bundle)
        
        assert result["refusal"] is False
        assert result["route"] == "performance"
        assert result["context_used"] is False
        assert "factsheet" in result["answer"].lower()
    
    def test_no_info_response_generation(self, mock_groq_client):
        """Test response generation when no context available."""
        no_context_bundle = ContextBundle(
            query="What is an unknown scheme?",
            route_label=RouteLabel.FACTUAL,
            primary_chunk=None
        )
        
        generator = AnswerGenerator(llm_client=mock_groq_client)
        result = generator.generate_answer(no_context_bundle)
        
        assert "don't have information" in result["answer"].lower()
        assert result["citation_url"] is None
        assert result["refusal"] is False
    
    def test_batch_generation(self, mock_groq_client, sample_context_bundle):
        """Test batch answer generation."""
        generator = AnswerGenerator(llm_client=mock_groq_client)
        
        bundles = [sample_context_bundle, sample_context_bundle]
        results = generator.batch_generate(bundles)
        
        assert len(results) == 2
        assert all("answer" in result for result in results)
        assert all("generation_time" in result for result in results)
    
    def test_generator_info(self, mock_groq_client):
        """Test generator configuration info."""
        generator = AnswerGenerator(llm_client=mock_groq_client)
        info = generator.get_generator_info()
        
        assert "llm_config" in info
        assert "prompts_loaded" in info
        assert "supported_routes" in info
        assert info["prompts_loaded"] is True


class TestPromptTemplates:
    """Test prompt template loading and formatting."""
    
    def test_system_prompt_loading(self):
        """Test system prompt template loading."""
        prompt_path = Path(__file__).parent.parent.parent / "src" / "phase5_generation" / "prompts" / "system.md"
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "facts-only" in content.lower()
            assert "maximum 3 sentences" in content.lower()
            assert "citation" in content.lower()
    
    def test_user_prompt_template_formatting(self):
        """Test user prompt template formatting."""
        template_path = Path(__file__).parent.parent.parent / "src" / "phase5_generation" / "prompts" / "user_wrap.md"
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Test template formatting
            formatted = template.format(
                context="Sample context text",
                citation_url="https://example.com",
                question="Sample question?",
                history="No history"
            )
            
            assert "Sample context text" in formatted
            assert "https://example.com" in formatted
            assert "Sample question?" in formatted
    
    def test_refusal_template_formatting(self):
        """Test refusal template formatting."""
        template_path = Path(__file__).parent.parent.parent / "src" / "phase5_generation" / "prompts" / "refusal.md"
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Test template formatting
            formatted = template.format(
                educational_link="https://www.amfiindia.com/investor-education"
            )
            
            assert "https://www.amfiindia.com/investor-education" in formatted
            assert "cannot provide investment advice" in formatted.lower()


class TestIntegration:
    """Integration tests for Phase 5 generation."""
    
    @pytest.mark.integration
    def test_end_to_end_generation(self):
        """Test end-to-end generation process."""
        # This would require actual Groq API keys
        # Skip in unit test environment
        pytest.skip("Integration test - requires Groq API keys")
    
    def test_error_handling(self):
        """Test error handling in generation."""
        # Test with failing Groq client
        mock_client = Mock(spec=LLMClient)
        mock_client.generate.side_effect = Exception("Groq API Error")
        
        generator = AnswerGenerator(llm_client=mock_client)
        sample_bundle = ContextBundle(
            query="Test query",
            route_label=RouteLabel.FACTUAL
        )
        
        result = generator.generate_answer(sample_bundle)
        
        assert result["refusal"] is True
        assert "error" in result
        assert "encountered an error" in result["answer"].lower()


if __name__ == "__main__":
    pytest.main([__file__])
