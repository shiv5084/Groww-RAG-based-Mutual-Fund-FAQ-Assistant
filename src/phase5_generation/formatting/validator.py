"""
Phase 5.2 - Output Validation.

Implements comprehensive validation logic for formatted answers,
ensuring compliance with formatting rules and guardrails.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

from .guards import AnswerGuards
from .render_answer import AnswerRenderer


logger = logging.getLogger(__name__)


class OutputValidator:
    """
    Comprehensive validator for formatted answers.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize output validator with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._default_config()
        self.guards = AnswerGuards(self.config.get("guards", {}))
        self.renderer = AnswerRenderer(self.config.get("renderer", {}))
    
    def _default_config(self) -> Dict[str, Any]:
        """Default validator configuration."""
        return {
            "strict_mode": True,
            "validate_urls": True,
            "validate_sentence_count": True,
            "validate_forbidden_content": True,
            "validate_citation_presence": True,
            "max_validation_errors": 5,
            "guards": {
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
                    r"https?://hdfcfund\.com/learn/blog",
                    
                    # SEBI subdomains and services
                    r"https?://(www\.)?sebi\.gov\.in",
                    r"https?://sebi\.gov\.in",
                    r"https?://investor\.sebi\.gov\.in"
                ],
                "forbidden_patterns": [
                    r"\b(invest|investment advice|recommend|suggest|advice|guidance|counsel)\b",
                    r"\b(better|best|worst|good|bad|should|prefer|choose|pick|select)\b",
                    r"\b(guaranteed|assured|risk-free|safe investment)\b",
                    r"\b(quick money|fast returns|double your money)\b"
                ],
                "footer_template": "Last updated from sources: {date}"
            },
            "renderer": {
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
        }
    
    def validate_json_output(self, json_output: Union[str, Dict[str, Any]], 
                          citation_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate LLM JSON output.
        
        Args:
            json_output: JSON string or dictionary from LLM
            citation_url: Expected citation URL
            
        Returns:
            Validation result dictionary
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "validation_details": {}
        }
        
        # Parse JSON if needed
        if isinstance(json_output, str):
            try:
                parsed_data = json.loads(json_output)
            except json.JSONDecodeError as e:
                result["valid"] = False
                result["errors"].append(f"Invalid JSON: {e}")
                result["validation_details"]["json_parse"] = False
                return result
        else:
            parsed_data = json_output
        
        result["validation_details"]["json_parse"] = True
        
        # Extract answer text
        answer_text = self._extract_answer_text(parsed_data)
        result["validation_details"]["answer_extracted"] = bool(answer_text)
        
        if not answer_text:
            result["valid"] = False
            result["errors"].append("No answer text found in JSON")
            return result
        
        # Apply guard validation
        guard_result = self.guards.apply_all_guards(answer_text, citation_url)
        result["validation_details"]["guards"] = guard_result
        
        if not guard_result["is_valid"]:
            result["valid"] = False
            result["errors"].extend(guard_result["errors"])
        
        result["warnings"].extend(guard_result["warnings"])
        
        return result
    
    def validate_rendered_output(self, rendered_answer: str, 
                              citation_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate rendered answer string.
        
        Args:
            rendered_answer: Rendered answer string
            citation_url: Expected citation URL
            
        Returns:
            Validation result dictionary
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "validation_details": {}
        }
        
        # Basic checks
        if not rendered_answer or not rendered_answer.strip():
            result["valid"] = False
            result["errors"].append("Empty rendered answer")
            result["validation_details"]["empty_answer"] = True
            return result
        
        result["validation_details"]["empty_answer"] = False
        result["validation_details"]["answer_length"] = len(rendered_answer)
        
        # Check for citation presence if required
        if citation_url and self.config["validate_citation_presence"]:
            if citation_url.lower() not in rendered_answer.lower():
                result["warnings"].append("Citation URL not found in rendered answer")
                result["validation_details"]["citation_present"] = False
            else:
                result["validation_details"]["citation_present"] = True
        
        # Apply guard validation to the answer part only
        answer_part = rendered_answer.split('\n\n')[0]  # Get first part before citation/timestamp
        guard_result = self.guards.apply_all_guards(answer_part, citation_url)
        result["validation_details"]["guards"] = guard_result
        
        if not guard_result["is_valid"]:
            result["valid"] = False
            result["errors"].extend(guard_result["errors"])
        
        result["warnings"].extend(guard_result["warnings"])
        
        return result
    
    def validate_complete_flow(self, json_output: Union[str, Dict[str, Any]], 
                           citation_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate complete flow from JSON to rendered output.
        
        Args:
            json_output: JSON string or dictionary from LLM
            citation_url: Expected citation URL
            
        Returns:
            Comprehensive validation result
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "validation_details": {}
        }
        
        # Step 1: Validate JSON output
        json_validation = self.validate_json_output(json_output, citation_url)
        result["validation_details"]["json_validation"] = json_validation
        
        if not json_validation["valid"]:
            result["valid"] = False
            result["errors"].extend(json_validation["errors"])
            result["warnings"].extend(json_validation["warnings"])
            return result
        
        # Step 2: Render answer
        render_result = self.renderer.render_from_json(json_output, citation_url)
        result["validation_details"]["render_result"] = render_result
        
        if not render_result["success"]:
            result["valid"] = False
            result["errors"].append(f"Rendering failed: {render_result.get('error', 'Unknown error')}")
            return result
        
        # Step 3: Validate rendered output
        rendered_validation = self.validate_rendered_output(
            render_result["rendered_answer"], citation_url
        )
        result["validation_details"]["rendered_validation"] = rendered_validation
        
        if not rendered_validation["valid"]:
            result["valid"] = False
            result["errors"].extend(rendered_validation["errors"])
            result["warnings"].extend(rendered_validation["warnings"])
        
        # Combine all warnings
        all_warnings = (json_validation["warnings"] + 
                       render_result.get("warnings", []) + 
                       rendered_validation["warnings"])
        result["warnings"] = list(set(all_warnings))  # Remove duplicates
        
        return result
    
    def _extract_answer_text(self, parsed_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract answer text from parsed JSON data.
        
        Args:
            parsed_data: Parsed JSON dictionary
            
        Returns:
            Extracted answer text or None
        """
        # Try different possible keys for answer text
        possible_keys = ["answer", "text", "response", "content", "message"]
        
        for key in possible_keys:
            if key in parsed_data:
                answer = parsed_data[key]
                if isinstance(answer, str):
                    return answer.strip()
                elif isinstance(answer, dict) and "text" in answer:
                    return answer["text"].strip()
        
        # If no standard keys found, try to find any string value
        for value in parsed_data.values():
            if isinstance(value, str) and len(value.strip()) > 0:
                return value.strip()
        
        return None
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Get human-readable validation summary.
        
        Args:
            validation_result: Validation result dictionary
            
        Returns:
            Human-readable summary string
        """
        if validation_result["valid"]:
            return "✅ Validation passed"
        
        summary_parts = ["❌ Validation failed:"]
        
        if validation_result["errors"]:
            summary_parts.append(f"Errors: {', '.join(validation_result['errors'][:3])}")
            if len(validation_result["errors"]) > 3:
                summary_parts.append(f"... and {len(validation_result['errors']) - 3} more")
        
        if validation_result["warnings"]:
            summary_parts.append(f"Warnings: {', '.join(validation_result['warnings'][:2])}")
            if len(validation_result["warnings"]) > 2:
                summary_parts.append(f"... and {len(validation_result['warnings']) - 2} more")
        
        return " | ".join(summary_parts)
    
    def get_validator_config(self) -> Dict[str, Any]:
        """Get current validator configuration."""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update validator configuration."""
        self.config.update(new_config)
        self.guards = AnswerGuards(self.config.get("guards", {}))
        self.renderer = AnswerRenderer(self.config.get("renderer", {}))
        logger.info("Validator configuration updated")


def create_default_validator() -> OutputValidator:
    """Create default OutputValidator instance."""
    return OutputValidator()
