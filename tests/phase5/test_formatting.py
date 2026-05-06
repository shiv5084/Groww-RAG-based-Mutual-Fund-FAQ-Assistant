"""
Tests for Phase 5.2 - Answer Rendering.

Tests JSON schema to user-visible string conversion,
citation formatting, and output assembly.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase5_generation.formatting.render_answer import AnswerRenderer, create_default_renderer


class TestAnswerRenderer:
    """Test AnswerRenderer functionality."""
    
    def test_default_initialization(self):
        """Test default renderer initialization."""
        renderer = create_default_renderer()
        config = renderer.get_renderer_config()
        
        assert config["include_citation"] is True
        assert config["citation_format"] == "Source: {url}"
        assert config["include_timestamp"] is True
        assert config["max_answer_length"] == 1000
        assert config["truncate_indicator"] == "..."
    
    def test_text_cleaning(self):
        """Test text cleaning functionality."""
        renderer = create_default_renderer()
        
        # Test multiple spaces
        dirty_text = "This    has    multiple    spaces."
        cleaned = renderer._clean_text(dirty_text)
        assert cleaned == "This has multiple spaces."
        
        # Test multiple newlines
        dirty_text = "Line 1\n\n\nLine 2\n\nLine 3"
        cleaned = renderer._clean_text(dirty_text)
        assert cleaned == "Line 1\nLine 2\nLine 3"
        
        # Test whitespace trimming
        dirty_text = "   Text with spaces   "
        cleaned = renderer._clean_text(dirty_text)
        assert cleaned == "Text with spaces"
    
    def test_text_truncation(self):
        """Test text truncation functionality."""
        renderer = create_default_renderer()
        
        # Test short text (no truncation)
        short_text = "This is short."
        result = renderer._truncate_if_needed(short_text)
        assert result == short_text
        
        # Test long text (truncation)
        long_text = "A" * 1100  # Longer than max_length
        result = renderer._truncate_if_needed(long_text)
        assert len(result) <= 1003  # max_length + len(truncate_indicator)
        assert result.endswith("...")
    
    def test_citation_formatting(self):
        """Test citation formatting."""
        renderer = create_default_renderer()
        
        # Test with citation
        citation = renderer._format_citation("https://www.hdfcfund.com")
        assert citation == "Source: https://www.hdfcfund.com"
        
        # Test without citation
        citation = renderer._format_citation(None)
        assert citation is None
        
        # Test with citation disabled
        renderer.update_config({"include_citation": False})
        citation = renderer._format_citation("https://www.hdfcfund.com")
        assert citation is None
    
    def test_timestamp_formatting(self):
        """Test timestamp formatting."""
        renderer = create_default_renderer()
        
        # Test with timestamp enabled
        timestamp = renderer._format_timestamp()
        assert timestamp is not None
        assert len(timestamp) > 0  # Should have date and time
        
        # Test with timestamp disabled
        renderer.update_config({"include_timestamp": False})
        timestamp = renderer._format_timestamp()
        assert timestamp is None
    
    def test_json_rendering(self):
        """Test rendering from JSON output."""
        renderer = create_default_renderer()
        
        # Test simple JSON
        json_data = {"answer": "HDFC Equity Fund is a large-cap scheme."}
        citation_url = "https://www.hdfcfund.com"
        
        result = renderer.render_from_json(json_data, citation_url)
        
        assert result["success"] is True
        assert "HDFC Equity Fund is a large-cap scheme." in result["rendered_answer"]
        assert "Source: https://www.hdfcfund.com" in result["rendered_answer"]
        assert "Generated:" in result["rendered_answer"]
        assert result["citation"] == "Source: https://www.hdfcfund.com"
        assert result["truncated"] is False
    
    def test_json_string_rendering(self):
        """Test rendering from JSON string."""
        renderer = create_default_renderer()
        
        # Test JSON string
        json_str = '{"answer": "Test answer from JSON string."}'
        citation_url = "https://www.amfiindia.com"
        
        result = renderer.render_from_json(json_str, citation_url)
        
        assert result["success"] is True
        assert "Test answer from JSON string." in result["rendered_answer"]
        assert result["original_text"] == "Test answer from JSON string."
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON."""
        renderer = create_default_renderer()
        
        # Test invalid JSON string
        invalid_json = '{"answer": "Incomplete json'
        citation_url = "https://www.hdfcfund.com"
        
        result = renderer.render_from_json(invalid_json, citation_url)
        
        assert result["success"] is False
        assert "Invalid JSON format" in result["error"]
        assert result["rendered_answer"] == invalid_json  # Fallback to raw
    
    def test_complex_json_structure(self):
        """Test handling of complex JSON structures."""
        renderer = create_default_renderer()
        
        # Test nested JSON
        complex_json = {
            "response": {
                "data": {
                    "text": "Complex nested answer."
                }
            }
        }
        
        result = renderer.render_from_json(complex_json)
        
        assert result["success"] is True
        assert "Complex nested answer." in result["rendered_answer"]
    
    def test_simple_text_rendering(self):
        """Test rendering simple text."""
        renderer = create_default_renderer()
        
        text = "Simple text answer."
        citation_url = "https://www.hdfcfund.com"
        
        result = renderer.render_simple_text(text, citation_url)
        
        assert result["success"] is True
        assert "Simple text answer." in result["rendered_answer"]
        assert "Source: https://www.hdfcfund.com" in result["rendered_answer"]
        assert result["original_text"] == text
    
    def test_config_updates(self):
        """Test configuration updates."""
        renderer = create_default_renderer()
        
        # Update configuration
        new_config = {
            "include_citation": False,
            "citation_format": "Reference: {url}",
            "max_answer_length": 500
        }
        
        renderer.update_config(new_config)
        updated_config = renderer.get_renderer_config()
        
        assert updated_config["include_citation"] is False
        assert updated_config["citation_format"] == "Reference: {url}"
        assert updated_config["max_answer_length"] == 500
        
        # Original values should remain unchanged
        assert updated_config["include_timestamp"] is True
        assert updated_config["truncate_indicator"] == "..."
    
    def test_component_extraction(self):
        """Test extraction of answer text from various JSON structures."""
        renderer = create_default_renderer()
        
        # Test different key names
        test_cases = [
            {"answer": "Direct answer"},
            {"text": "Text field answer"},
            {"response": "Response field answer"},
            {"content": "Content field answer"},
            {"message": "Message field answer"},
            {"nested": {"text": "Nested text answer"}},
            {"data": {"content": {"text": "Deep nested answer"}}}
        ]
        
        for test_case in test_cases:
            extracted = renderer._extract_answer_text(test_case)
            assert extracted is not None
            assert len(extracted.strip()) > 0
    
    def test_rendered_components(self):
        """Test that all components are properly assembled."""
        renderer = create_default_renderer()
        
        text = "Test answer."
        citation_url = "https://www.hdfcfund.com"
        
        result = renderer.render_simple_text(text, citation_url)
        components = result["components"]
        
        assert components["answer"] == "Test answer."
        assert "Source: https://www.hdfcfund.com" in components["citation"]
        assert components["timestamp"] is not None
        assert len(components["timestamp"]) > 0
        
        # Check final assembly
        final_answer = result["rendered_answer"]
        assert final_answer.startswith("Test answer.")
        assert "Source: https://www.hdfcfund.com" in final_answer
        assert "Generated:" in final_answer


if __name__ == "__main__":
    pytest.main([__file__])
