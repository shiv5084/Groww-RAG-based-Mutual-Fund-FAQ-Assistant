"""
Phase 5.2 - Formatting Module.

Implements output formatting, guardrails, and validation for Phase 5 answers.
This subphase handles the post-processing of LLM outputs to ensure
compliance with formatting rules and quality standards.

Components:
- guards.py: Sentence count, URL count, allowlist, footer injection
- render_answer.py: JSON schema to user-visible string conversion
- validator.py: Comprehensive validation logic
"""

from .guards import AnswerGuards, create_default_guards
from .render_answer import AnswerRenderer, create_default_renderer
from .validator import OutputValidator, create_default_validator

__all__ = [
    "AnswerGuards",
    "AnswerRenderer", 
    "OutputValidator",
    "create_default_guards",
    "create_default_renderer",
    "create_default_validator"
]

__version__ = "5.2.0"
__author__ = "Phase 5.2 Implementation Team"
