"""
Phase 5.2 - Answer Rendering.

Converts JSON schema output from LLM to user-visible string format.
Handles answer formatting, citation placement, and final output assembly.
"""

import json
import re
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime


logger = logging.getLogger(__name__)


class AnswerRenderer:
    """
    Renders LLM JSON output into user-visible answer strings.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize answer renderer with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default renderer configuration."""
        return {
            "include_citation": True,
            "citation_format": "Source: {url}",
            "include_timestamp": True,
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
            "max_answer_length": 1000,
            "truncate_indicator": "...",
            "cleanup_patterns": [
                (r'\s+', ' '),  # Multiple spaces to single space
                (r'\n+', '\n'),  # Multiple newlines to single
                (r'^\s+|\s+$', '')  # Trim whitespace
            ]
        }
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text using configured patterns.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        cleaned = text
        for pattern, replacement in self.config["cleanup_patterns"]:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        return cleaned.strip()
    
    def _truncate_if_needed(self, text: str) -> str:
        """
        Truncate text if it exceeds maximum length.
        
        Args:
            text: Text to check
            
        Returns:
            Possibly truncated text
        """
        if len(text) <= self.config["max_answer_length"]:
            return text
        
        truncated = text[:self.config["max_answer_length"] - len(self.config["truncate_indicator"])]
        return truncated + self.config["truncate_indicator"]
    
    def _format_citation(self, citation_url: Optional[str]) -> Optional[str]:
        """
        Format citation URL according to configuration.
        
        Args:
            citation_url: Citation URL to format
            
        Returns:
            Formatted citation string or None
        """
        if not citation_url or not self.config["include_citation"]:
            return None
        
        return self.config["citation_format"].format(url=citation_url)
    
    def _format_timestamp(self) -> Optional[str]:
        """
        Format timestamp according to configuration.
        
        Args:
            
        Returns:
            Formatted timestamp string or None
        """
        if not self.config["include_timestamp"]:
            return None
        
        return datetime.now().strftime(self.config["timestamp_format"])
    
    def render_from_json(self, json_output: Union[str, Dict[str, Any]], 
                     citation_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Render answer from JSON output.
        
        Args:
            json_output: JSON string or dictionary from LLM
            citation_url: Optional citation URL
            
        Returns:
            Dictionary with rendered components
        """
        # Parse JSON if it's a string
        if isinstance(json_output, str):
            try:
                parsed_data = json.loads(json_output)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON output: {e}")
                return {
                    "success": False,
                    "error": "Invalid JSON format",
                    "raw_output": json_output,
                    "rendered_answer": json_output  # Fallback to raw
                }
        else:
            parsed_data = json_output
        
        # Extract answer text from different possible JSON structures
        answer_text = self._extract_answer_text(parsed_data)
        
        # Clean and process the text
        cleaned_text = self._clean_text(answer_text)
        truncated_text = self._truncate_if_needed(cleaned_text)
        
        # Format components
        citation = self._format_citation(citation_url)
        timestamp = self._format_timestamp()
        
        # Assemble final answer
        components = [truncated_text]
        
        if citation:
            components.append(citation)
        
        if timestamp:
            components.append(f"Generated: {timestamp}")
        
        rendered_answer = "\n\n".join(components)
        
        return {
            "success": True,
            "rendered_answer": rendered_answer,
            "original_text": answer_text,
            "cleaned_text": cleaned_text,
            "truncated": len(cleaned_text) > self.config["max_answer_length"],
            "citation": citation,
            "timestamp": timestamp,
            "components": {
                "answer": truncated_text,
                "citation": citation,
                "timestamp": timestamp
            }
        }
    
    def _extract_answer_text(self, parsed_data: Dict[str, Any]) -> str:
        """
        Extract answer text from parsed JSON data.
        
        Args:
            parsed_data: Parsed JSON dictionary
            
        Returns:
            Extracted answer text
        """
        # Try different possible keys for answer text
        possible_keys = ["answer", "text", "response", "content", "message"]
        
        for key in possible_keys:
            if key in parsed_data:
                answer = parsed_data[key]
                if isinstance(answer, str):
                    return answer
                elif isinstance(answer, dict) and "text" in answer:
                    return answer["text"]
        
        # If no standard keys found, try to find any string value
        for value in parsed_data.values():
            if isinstance(value, str) and len(value.strip()) > 0:
                return value.strip()
        
        # Fallback: convert entire dict to string
        logger.warning("Could not extract answer text, using fallback method")
        return str(parsed_data)
    
    def render_simple_text(self, text: str, citation_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Render simple text answer with citation.
        
        Args:
            text: Simple text answer
            citation_url: Optional citation URL
            
        Returns:
            Dictionary with rendered components
        """
        cleaned_text = self._clean_text(text)
        truncated_text = self._truncate_if_needed(cleaned_text)
        
        citation = self._format_citation(citation_url)
        timestamp = self._format_timestamp()
        
        # Assemble final answer
        components = [truncated_text]
        
        if citation:
            components.append(citation)
        
        if timestamp:
            components.append(f"Generated: {timestamp}")
        
        rendered_answer = "\n\n".join(components)
        
        return {
            "success": True,
            "rendered_answer": rendered_answer,
            "original_text": text,
            "cleaned_text": cleaned_text,
            "truncated": len(cleaned_text) > self.config["max_answer_length"],
            "citation": citation,
            "timestamp": timestamp,
            "components": {
                "answer": truncated_text,
                "citation": citation,
                "timestamp": timestamp
            }
        }
    
    def get_renderer_config(self) -> Dict[str, Any]:
        """Get current renderer configuration."""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update renderer configuration."""
        self.config.update(new_config)
        logger.info("Renderer configuration updated")


def create_default_renderer() -> AnswerRenderer:
    """Create default AnswerRenderer instance."""
    return AnswerRenderer()
