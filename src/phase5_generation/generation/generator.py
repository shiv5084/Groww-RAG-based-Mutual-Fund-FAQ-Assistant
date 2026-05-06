"""
Core generation logic for Phase 5.

Handles answer generation using retrieved context and Groq LLM, with proper
facts-only constraints and citation handling.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from phase4_retrieval.types import ContextBundle, RouteLabel
from .llm_client import LLMClient


logger = logging.getLogger(__name__)


class AnswerGenerator:
    """
    Core answer generation component for Phase 5.
    
    Generates factual answers based on retrieved context using Groq LLM,
    enforcing facts-only constraints and proper citation handling.
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None,
                 system_prompt_path: Optional[str] = None,
                 user_prompt_path: Optional[str] = None,
                 refusal_prompt_path: Optional[str] = None):
        """
        Initialize the answer generator.
        
        Args:
            llm_client: Configured Groq LLM client. If None, creates from environment.
            system_prompt_path: Path to system prompt template.
            user_prompt_path: Path to user prompt template.
            refusal_prompt_path: Path to refusal prompt template.
        """
        self.llm_client = llm_client or LLMClient.from_env()
        
        # Load prompt templates
        self.system_prompt = self._load_prompt(
            system_prompt_path or os.path.join(
                os.path.dirname(__file__), 
                "..", "prompts", "system.md"
            )
        )
        
        self.user_prompt_template = self._load_prompt(
            user_prompt_path or os.path.join(
                os.path.dirname(__file__), 
                "..", "prompts", "user_wrap.md"
            )
        )
        
        self.refusal_template = self._load_prompt(
            refusal_prompt_path or os.path.join(
                os.path.dirname(__file__), 
                "..", "prompts", "refusal.md"
            )
        )
        
        logger.info("AnswerGenerator initialized with Groq LLM")
    
    def _load_prompt(self, path: str) -> str:
        """Load prompt template from file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt template not found: {path}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt template {path}: {e}")
            raise
    
    def generate_answer(self, context_bundle: ContextBundle) -> Dict[str, Any]:
        """
        Generate answer based on context bundle.
        
        Args:
            context_bundle: Complete context with query, route, and retrieved chunks
            
        Returns:
            Dictionary with generated answer and metadata
        """
        start_time = datetime.now()
        
        try:
            if context_bundle.route_label == RouteLabel.ADVISORY:
                return self._generate_refusal(context_bundle)
            elif context_bundle.route_label == RouteLabel.PERFORMANCE:
                return self._generate_performance_response(context_bundle)
            elif context_bundle.route_label == RouteLabel.FACTUAL:
                return self._generate_factual_answer(context_bundle)
            else:
                logger.error(f"Unknown route label: {context_bundle.route_label}")
                return self._generate_refusal(context_bundle)
        
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return {
                "answer": "I apologize, but I encountered an error generating your response. Please try again.",
                "citation_url": None,
                "refusal": True,
                "error": str(e),
                "generation_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _generate_factual_answer(self, context_bundle: ContextBundle) -> Dict[str, Any]:
        """Generate factual answer using retrieved context."""
        start_time = datetime.now()
        
        if not context_bundle.primary_chunk:
            return self._generate_no_info_response(context_bundle)
        
        # Prepare context text
        context_text = self._prepare_context_text(context_bundle)
        
        # Build user prompt
        user_prompt = self.user_prompt_template.format(
            context=context_text,
            citation_url=context_bundle.citation_url or context_bundle.primary_chunk.source_url,
            question=context_bundle.query,
            history=self._format_history(context_bundle)
        )
        
        # Build messages for Groq LLM
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Generate response using Groq
        response = self.llm_client.generate(messages)
        
        # Post-process to enforce 3-sentence limit
        response = self._enforce_sentence_limit(response)
        
        return {
            "answer": response,
            "citation_url": context_bundle.citation_url or context_bundle.primary_chunk.source_url,
            "refusal": False,
            "route": context_bundle.route_label.value,
            "context_used": True,
            "chunk_ids_used": [context_bundle.primary_chunk.chunk_id],
            "generation_time": (datetime.now() - start_time).total_seconds()
        }
    
    def _generate_performance_response(self, context_bundle: ContextBundle) -> Dict[str, Any]:
        """Generate performance-only response with factsheet link."""
        start_time = datetime.now()
        factsheet_url = self._get_factsheet_url(context_bundle)
        
        if factsheet_url:
            answer = f"For detailed performance information, please refer to the official factsheet: {factsheet_url}"
        else:
            answer = "For detailed performance information, please refer to the official scheme factsheet."
        
        return {
            "answer": answer,
            "citation_url": factsheet_url,
            "refusal": False,
            "route": context_bundle.route_label.value,
            "context_used": False,
            "chunk_ids_used": [],
            "generation_time": (datetime.now() - start_time).total_seconds()
        }
    
    def _generate_refusal(self, context_bundle: ContextBundle) -> Dict[str, Any]:
        """Generate refusal response for advisory queries."""
        start_time = datetime.now()
        educational_link = self._get_educational_link()
        
        answer = self.refusal_template.format(educational_link=educational_link)
        
        # Post-process to enforce 3-sentence limit
        answer = self._enforce_sentence_limit(answer)
        
        return {
            "answer": answer,
            "citation_url": educational_link,
            "refusal": True,
            "route": context_bundle.route_label.value,
            "context_used": False,
            "chunk_ids_used": [],
            "generation_time": (datetime.now() - start_time).total_seconds()
        }
    
    def _generate_no_info_response(self, context_bundle: ContextBundle) -> Dict[str, Any]:
        """Generate response when no relevant information found."""
        start_time = datetime.now()
        answer = "I don't have information about this specific query in the provided sources."
        
        return {
            "answer": answer,
            "citation_url": None,
            "refusal": False,
            "route": context_bundle.route_label.value,
            "context_used": False,
            "chunk_ids_used": [],
            "generation_time": (datetime.now() - start_time).total_seconds()
        }
    
    def _enforce_sentence_limit(self, text: str, max_sentences: int = 3) -> str:
        """Enforce sentence limit by truncating excess sentences."""
        import re
        
        # Split sentences using common delimiters
        sentences = re.split(r'[.!?]+', text)
        # Filter out empty strings and whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Take only the first max_sentences sentences
        if len(sentences) <= max_sentences:
            return text
        
        # Truncate to max_sentences and ensure proper ending
        truncated_sentences = sentences[:max_sentences]
        result = '. '.join(truncated_sentences)
        
        # Ensure it ends with proper punctuation
        if not result.endswith(('.', '!', '?')):
            result += '.'
            
        return result
    
    def _prepare_context_text(self, context_bundle: ContextBundle) -> str:
        """Prepare context text for LLM."""
        # Use pre-packed user_context if available (it has truncation and formatting)
        if hasattr(context_bundle, 'user_context') and context_bundle.user_context:
            return context_bundle.user_context
            
        # Fallback to primary chunk text
        if context_bundle.primary_chunk:
            return context_bundle.primary_chunk.text
        return ""
    
    def _format_history(self, context_bundle: ContextBundle) -> str:
        """Format conversation history for context."""
        # This would be implemented when Phase 6 (sessions) is integrated
        # For now, return empty string
        return "No relevant conversation history."
    
    def _get_factsheet_url(self, context_bundle: ContextBundle) -> Optional[str]:
        """Get factsheet URL from context chunks."""
        # Look for factsheet URLs in retrieved chunks
        if context_bundle.primary_chunk and "factsheet" in context_bundle.primary_chunk.doc_type.lower():
            return context_bundle.primary_chunk.source_url
        
        for chunk in context_bundle.secondary_chunks:
            if "factsheet" in chunk.doc_type.lower():
                return chunk.source_url
        
        return None
    
    def _get_educational_link(self) -> str:
        """Get educational link for refusal responses."""
        # Default educational links - could be made configurable
        return "https://www.amfiindia.com/investor-education"
    
    def batch_generate(self, context_bundles: List[ContextBundle]) -> List[Dict[str, Any]]:
        """
        Generate answers for multiple context bundles.
        
        Args:
            context_bundles: List of context bundles
            
        Returns:
            List of generation results
        """
        results = []
        for bundle in context_bundles:
            result = self.generate_answer(bundle)
            results.append(result)
        
        return results
    
    def get_generator_info(self) -> Dict[str, Any]:
        """Get generator configuration information."""
        return {
            "llm_config": self.llm_client.get_config_info(),
            "prompts_loaded": bool(self.system_prompt and self.user_prompt_template and self.refusal_template),
            "supported_routes": [label.value for label in RouteLabel]
        }


# Factory function for easy initialization
def create_answer_generator(**kwargs) -> AnswerGenerator:
    """
    Factory function to create AnswerGenerator with sensible defaults.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Configured AnswerGenerator instance
    """
    return AnswerGenerator(**kwargs)
