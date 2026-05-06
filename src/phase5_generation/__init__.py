"""
Phase 5 Generation module for Mutual Fund FAQ Assistant.

This module handles generation of factual answers based on retrieved context,
with proper citation handling and facts-only constraints using Groq LLM.
"""

from .generation.generator import AnswerGenerator
from .generation.llm_client import LLMClient

__all__ = ['AnswerGenerator', 'LLMClient']
