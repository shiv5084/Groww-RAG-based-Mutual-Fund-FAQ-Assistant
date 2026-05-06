"""
Phase 5.2 - Formatting Guards.

Implements output guardrails for answer formatting, including:
- Sentence count limits
- URL count validation
- Allowlist enforcement
- Footer injection
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


logger = logging.getLogger(__name__)


class AnswerGuards:
    """
    Implements guardrails for answer formatting and compliance.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize answer guards with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()
        self._compile_patterns()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default guard configuration."""
        return {
            "max_sentences": 3,
            "max_urls": 1,
            "url_allowlist": [
                # HDFC Mutual Fund domains (from source_allowlist.txt and url_registry.yaml)
                r"https?://(www\.)?hdfcfund\.com",
                r"https?://files\.hdfcfund\.com",
                r"https?://investor-web\.hdfcfund\.com",
                
                # AMFI (Association of Mutual Funds in India)
                r"https?://(www\.)?amfiindia\.com",
                
                # SEBI (Securities and Exchange Board of India)
                r"https?://(www\.)?sebi\.gov\.in",
                r"https?://investor\.sebi\.gov\.in",
                
                # Groww (Third-party aggregator - allowed for mixed source approach)
                r"https?://(www\.)?groww\.in",
                r"https?://groww\.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                r"https?://groww\.in/mutual-funds/hdfc-equity-fund-direct-growth",
                r"https?://groww\.in/mutual-funds/hdfc-focused-fund-direct-growth",
                r"https?://groww\.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
                r"https?://groww\.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
                
                # Additional HDFC subdomains and services
                r"https?://(www\.)?hdfcfund\.com",
                r"https?://hdfcfund\.com/explore/mutual-funds",
                r"https?://hdfcfund\.com/services",
                r"https?://hdfcfund\.com/statutory-disclosure",
                r"https?://hdfcfund\.com/contact-us",
                r"https?://hdfcfund\.com/learn/blog"
            ],
            "footer_template": "Last updated from sources: {date}",
            "forbidden_patterns": [
                r"\b(invest|investment advice|recommend|suggest|advice|guidance|counsel)\b",
                r"\b(better|best|worst|good|bad|should|prefer|choose|pick|select)\b",
                r"\b(guaranteed|assured|risk-free|safe investment)\b",
                r"\b(quick money|fast returns|double your money)\b"
            ]
        }
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        self.url_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.config["url_allowlist"]]
        self.forbidden_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.config["forbidden_patterns"]]
    
    def check_sentence_count(self, text: str) -> Tuple[bool, int]:
        """
        Check if text exceeds maximum sentence count.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_valid, sentence_count)
        """
        # Count sentences using common delimiters
        sentences = re.split(r'[.!?]+', text)
        # Filter out empty strings and whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        
        sentence_count = len(sentences)
        is_valid = sentence_count <= self.config["max_sentences"]
        
        logger.debug(f"Sentence count check: {sentence_count} sentences, valid: {is_valid}")
        return is_valid, sentence_count
    
    def check_url_count(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains valid URLs and count them.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_valid, list_of_urls)
        """
        # Find all URLs in text
        url_pattern = r'https?://[^\s<>"\'\)]+'
        urls = re.findall(url_pattern, text.lower())
        
        # Check if URLs are in allowlist
        valid_urls = []
        for url in urls:
            is_allowed = any(pattern.search(url) for pattern in self.url_patterns)
            if is_allowed:
                valid_urls.append(url)
        
        url_count = len(valid_urls)
        is_valid = url_count <= self.config["max_urls"]
        
        logger.debug(f"URL count check: {url_count} URLs, valid: {is_valid}")
        return is_valid, valid_urls
    
    def check_forbidden_content(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check if text contains forbidden patterns.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_valid, list_of_matches)
        """
        matches = []
        for pattern in self.forbidden_patterns:
            found = pattern.findall(text)
            if found:
                matches.extend(found)
        
        is_valid = len(matches) == 0
        
        logger.debug(f"Forbidden content check: {len(matches)} matches, valid: {is_valid}")
        return is_valid, matches
    
    def inject_footer(self, text: str, citation_url: Optional[str] = None) -> str:
        """
        Inject footer with date and citation information.
        
        Args:
            text: Original text
            citation_url: Optional citation URL
            
        Returns:
            Text with footer injected
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        footer = self.config["footer_template"].format(date=current_date)
        
        # Add citation if provided
        citation_text = ""
        if citation_url:
            citation_text = f"\n\nSource: {citation_url}"
        
        return f"{text}\n\n{footer}{citation_text}"
    
    def apply_all_guards(self, text: str, citation_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply all guardrails to text.
        
        Args:
            text: Text to validate
            citation_url: Optional citation URL
            
        Returns:
            Dictionary with validation results
        """
        results = {
            "original_text": text,
            "sentence_check": self.check_sentence_count(text),
            "url_check": self.check_url_count(text),
            "forbidden_check": self.check_forbidden_content(text),
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check overall validity
        sentence_valid, sentence_count = results["sentence_check"]
        url_valid, urls = results["url_check"]
        forbidden_valid, forbidden_matches = results["forbidden_check"]
        
        if not sentence_valid:
            results["errors"].append(f"Too many sentences: {sentence_count} (max: {self.config['max_sentences']})")
            results["is_valid"] = False
        
        if not url_valid:
            results["errors"].append(f"Invalid or too many URLs: {len(urls)} (max: {self.config['max_urls']})")
            results["is_valid"] = False
        
        if not forbidden_valid:
            results["errors"].append(f"Forbidden content detected: {forbidden_matches[:3]}")
            results["is_valid"] = False
        
        # Add warnings
        if len(urls) == 0 and citation_url:
            results["warnings"].append("Citation URL not found in text")
        
        # Apply footer if valid
        if results["is_valid"]:
            results["formatted_text"] = self.inject_footer(text, citation_url)
        else:
            results["formatted_text"] = text
        
        return results
    
    def get_guard_config(self) -> Dict[str, Any]:
        """Get current guard configuration."""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update guard configuration."""
        self.config.update(new_config)
        self._compile_patterns()
        logger.info("Guard configuration updated")


def create_default_guards() -> AnswerGuards:
    """Create default AnswerGuards instance."""
    return AnswerGuards()
