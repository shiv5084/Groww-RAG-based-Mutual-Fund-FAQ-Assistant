"""
Tests for Phase 5.2 - Answer Guards.

Tests sentence count limits, URL validation, allowlist enforcement,
and forbidden content detection.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase5_generation.formatting.guards import AnswerGuards, create_default_guards


class TestAnswerGuards:
    """Test AnswerGuards functionality."""
    
    def test_default_initialization(self):
        """Test default guard initialization."""
        guards = create_default_guards()
        config = guards.get_guard_config()
        
        assert config["max_sentences"] == 3
        assert config["max_urls"] == 1
        assert len(config["url_allowlist"]) > 0
        assert len(config["forbidden_patterns"]) > 0
    
    def test_sentence_count_validation(self):
        """Test sentence count validation."""
        guards = create_default_guards()
        
        # Test valid sentences
        is_valid, count = guards.check_sentence_count("This is one sentence.")
        assert is_valid is True
        assert count == 1
        
        # Test invalid sentences
        is_valid, count = guards.check_sentence_count(
            "First sentence. Second sentence. Third sentence. Fourth sentence."
        )
        assert is_valid is False
        assert count == 4
    
    def test_url_validation(self):
        """Test URL validation and allowlist."""
        guards = create_default_guards()
        
        # Test valid URL from allowlist
        is_valid, urls = guards.check_url_count(
            "Check https://www.amfiindia.com for more information."
        )
        assert is_valid is True
        assert len(urls) == 1
        assert "amfiindia.com" in urls[0]
        
        # Test invalid URL
        is_valid, urls = guards.check_url_count(
            "Check https://www.badsite.com for more information."
        )
        assert is_valid is False
        assert len(urls) == 0  # Not in allowlist
        
        # Test too many URLs
        is_valid, urls = guards.check_url_count(
            "Check https://www.amfiindia.com and https://www.hdfcfund.com for info."
        )
        assert is_valid is False
        assert len(urls) == 2
    
    def test_forbidden_content_detection(self):
        """Test forbidden content detection."""
        guards = create_default_guards()
        
        # Test investment advice
        is_valid, matches = guards.check_forbidden_content(
            "I recommend investing in this fund."
        )
        assert is_valid is False
        assert any("recommend" in match.lower() for match in matches)
        
        # Test comparison words
        is_valid, matches = guards.check_forbidden_content(
            "This is the best fund for your needs."
        )
        assert is_valid is False
        assert any("best" in match.lower() for match in matches)
        
        # Test safe content
        is_valid, matches = guards.check_forbidden_content(
            "HDFC Equity Fund is a large-cap equity scheme."
        )
        assert is_valid is True
        assert len(matches) == 0
    
    def test_footer_injection(self):
        """Test footer injection functionality."""
        guards = create_default_guards()
        
        # Test with citation
        text = "This is the answer."
        citation_url = "https://www.hdfcfund.com"
        
        result = guards.inject_footer(text, citation_url)
        
        assert "This is the answer." in result
        assert "Last updated from sources:" in result
        assert citation_url in result
        assert "Source: https://www.hdfcfund.com" in result
        
        # Test without citation
        result = guards.inject_footer(text, None)
        
        assert "This is the answer." in result
        assert "Last updated from sources:" in result
        assert "Source:" not in result
    
    def test_comprehensive_guard_application(self):
        """Test all guards applied together."""
        guards = create_default_guards()
        
        # Test valid content
        text = "HDFC Equity Fund is a large-cap scheme. It invests in large companies."
        citation_url = "https://www.hdfcfund.com"
        
        result = guards.apply_all_guards(text, citation_url)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert "formatted_text" in result
        assert "Last updated from sources:" in result["formatted_text"]
        
        # Test invalid content (too many sentences)
        text = ("First sentence. Second sentence. Third sentence. "
                "Fourth sentence. Fifth sentence.")
        result = guards.apply_all_guards(text, citation_url)
        
        assert result["is_valid"] is False
        assert any("Too many sentences" in error for error in result["errors"])
        
        # Test forbidden content
        text = "I recommend this fund as it's the best option."
        result = guards.apply_all_guards(text, citation_url)
        
        assert result["is_valid"] is False
        assert any("Forbidden content" in error for error in result["errors"])
    
    def test_config_updates(self):
        """Test configuration updates."""
        guards = create_default_guards()
        
        # Update configuration
        new_config = {
            "max_sentences": 5,
            "max_urls": 2,
            "footer_template": "Updated: {date}"
        }
        
        guards.update_config(new_config)
        updated_config = guards.get_guard_config()
        
        assert updated_config["max_sentences"] == 5
        assert updated_config["max_urls"] == 2
        assert updated_config["footer_template"] == "Updated: {date}"
    
    def test_url_allowlist_patterns(self):
        """Test URL allowlist pattern matching."""
        guards = create_default_guards()
        
        # Test various allowed URLs
        test_urls = [
            "https://www.amfiindia.com/investor-corner",
            "https://www.hdfcfund.com/factsheet",
        ]
        
        for url in test_urls:
            is_valid, urls = guards.check_url_count(f"Check {url} for details.")
            assert is_valid is True, f"URL should be valid: {url}"
            assert len(urls) == 1


if __name__ == "__main__":
    pytest.main([__file__])
