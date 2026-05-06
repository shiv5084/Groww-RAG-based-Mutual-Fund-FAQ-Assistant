"""
Generation submodule for Phase 5.

Contains the core Groq LLM client and answer generation logic.
"""

from .llm_client import LLMClient
from .generator import AnswerGenerator

__all__ = ['LLMClient', 'AnswerGenerator']
