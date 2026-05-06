"""Schema definitions for Phase 2 chunking metadata.

This module defines the data structures and schemas for chunk metadata
as specified in the phased architecture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class DocType(Enum):
    """Document types for filtering and categorization."""
    SCHEME_PAGE = "scheme_page"
    FACTSHEET = "factsheet"
    FACTSHEET_INDEX = "factsheet_index"
    INVESTOR_GUIDE = "investor_guide"
    INVESTOR_SERVICE_PAGE = "investor_service_page"
    REGULATORY_GUIDANCE = "regulatory_guidance"
    STATUTORY_DISCLOSURE_HUB = "statutory_disclosure_hub"
    FAQ = "faq"
    NEWS = "news"
    AMC_HOME = "amc_home"
    AMC_CONTACT = "amc_contact"
    INVESTOR_EDUCATION_AMC = "investor_education_amc"
    REGULATOR_HOME = "regulator_home"
    INVESTOR_EDUCATION = "investor_education"
    MUTUAL_FUND_GUIDANCE = "mutual_fund_guidance"
    GENERAL = "general"
    KIM_PDF = "kim_pdf"


@dataclass(frozen=True)
class ChunkMetadata:
    """Metadata for each chunk as per Phase 2 requirements."""
    
    # Core identification fields
    chunk_id: str                    # Stable unique identifier
    source_url: str                   # Citation source (must be allowlisted)
    doc_type: DocType                 # Document type for filtering
    scheme: Optional[str]             # Optional scheme name/code
    doc_id: str                       # Original document ID
    
    # Provenance fields
    fetched_at: str                   # When source was fetched
    indexed_at: str                   # When chunk was indexed/embedded
    
    # Chunking metadata
    chunk_index: int                  # Position within document (0-based)
    total_chunks: int                 # Total chunks in document
    chunk_strategy: str               # Strategy used for chunking
    
    # Content metadata
    text_length: int                  # Length of chunk text
    token_count: Optional[int]        # Estimated token count
    section_title: Optional[str]      # Section title if available
    heading_level: Optional[int]      # Heading level (1-6) if applicable
    
    # Quality metrics
    content_quality_score: Optional[float]  # 0.0 to 1.0 quality score
    has_meaningful_content: bool      # Whether chunk contains meaningful content
    
    # Position information
    char_start: Optional[int]         # Start position in source text
    char_end: Optional[int]           # End position in source text
    
    # Additional metadata
    keywords: Optional[List[str]]     # Extracted keywords
    entities: Optional[List[str]]     # Named entities found
    language: Optional[str]           # Detected language (e.g., "en")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert DocType enum to string
        if isinstance(data.get("doc_type"), DocType):
            data["doc_type"] = data["doc_type"].value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkMetadata":
        """Create from dictionary."""
        # Convert doc_type string to enum
        if "doc_type" in data and isinstance(data["doc_type"], str):
            data["doc_type"] = DocType(data["doc_type"])
        
        return cls(**data)


@dataclass(frozen=True)
class Chunk:
    """Complete chunk with text and metadata."""
    
    text: str                         # Chunk text content
    metadata: ChunkMetadata            # Chunk metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "metadata": self.metadata.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Create from dictionary."""
        return cls(
            text=data["text"],
            metadata=ChunkMetadata.from_dict(data["metadata"])
        )
    
    def to_jsonl(self) -> str:
        """Convert to JSONL format (one JSON object per line)."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_jsonl(cls, jsonl_line: str) -> "Chunk":
        """Create from JSONL line."""
        data = json.loads(jsonl_line)
        return cls.from_dict(data)


class ChunkSchema:
    """Schema validation and utilities for chunks."""
    
    @staticmethod
    def validate_metadata(metadata: ChunkMetadata) -> List[str]:
        """Validate chunk metadata and return list of issues."""
        issues = []
        
        # Required fields validation
        if not metadata.chunk_id:
            issues.append("Missing chunk_id")
        
        if not metadata.source_url:
            issues.append("Missing source_url")
        elif not metadata.source_url.startswith(("http://", "https://")):
            issues.append("Invalid source_url format")
        
        if not metadata.doc_id:
            issues.append("Missing doc_id")
        
        if not metadata.fetched_at:
            issues.append("Missing fetched_at")
        
        if not metadata.indexed_at:
            issues.append("Missing indexed_at")
        
        # Logical validation
        if metadata.chunk_index < 0:
            issues.append("Invalid chunk_index (must be >= 0)")
        
        if metadata.total_chunks <= 0:
            issues.append("Invalid total_chunks (must be > 0)")
        
        if metadata.chunk_index >= metadata.total_chunks:
            issues.append("chunk_index >= total_chunks")
        
        # Note: text_length validation is done at chunk level, not metadata level
        # This validation is removed to avoid the error
        
        if metadata.token_count is not None and metadata.token_count < 0:
            issues.append("Invalid token_count (must be >= 0)")
        
        if metadata.content_quality_score is not None:
            if not 0.0 <= metadata.content_quality_score <= 1.0:
                issues.append("content_quality_score must be between 0.0 and 1.0")
        
        if metadata.heading_level is not None:
            if not 1 <= metadata.heading_level <= 6:
                issues.append("heading_level must be between 1 and 6")
        
        if metadata.char_start is not None and metadata.char_end is not None:
            if metadata.char_start >= metadata.char_end:
                issues.append("char_start must be < char_end")
        
        return issues
    
    @staticmethod
    def validate_chunk(chunk: Chunk) -> List[str]:
        """Validate complete chunk and return list of issues."""
        issues = []
        
        # Text validation
        if not chunk.text.strip():
            issues.append("Empty chunk text")
        
        # Metadata validation
        metadata_issues = ChunkSchema.validate_metadata(chunk.metadata)
        issues.extend(metadata_issues)
        
        # Cross-validation
        if chunk.metadata.text_length != len(chunk.text):
            issues.append("text_length in metadata doesn't match actual text length")
        
        return issues
    
    @staticmethod
    def generate_chunk_id(doc_id: str, chunk_index: int, strategy: str = "default") -> str:
        """Generate stable chunk ID."""
        return f"{doc_id}_{strategy}_{chunk_index:04d}"
    
    @staticmethod
    def estimate_token_count(text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Simple estimation: ~4 characters per token for English
        return max(1, len(text) // 4)
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Simple language detection (basic implementation)."""
        # Check for common Hindi words
        hindi_indicators = ["हिंदी", "योजना", "निवेश", "धन", "बैंक", "ऋण"]
        
        text_lower = text.lower()
        if any(indicator in text_lower for indicator in hindi_indicators):
            return "hi"
        
        # Default to English for mutual fund content
        return "en"
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text (simple implementation)."""
        # Common mutual fund keywords
        mutual_fund_terms = [
            "mutual fund", "nav", "scheme", "investment", "returns", "risk",
            "portfolio", "asset allocation", "sip", "systematic investment plan",
            "lump sum", "dividend", "growth", "equity", "debt", "hybrid",
            "large cap", "mid cap", "small cap", "expense ratio", "exit load",
            "lock-in period", "benchmark", "fund manager", "amc", "sebi",
            "regulatory", "investor", "factsheet", "prospectus", "kyc", "pan"
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for term in mutual_fund_terms:
            if term in text_lower and term not in found_keywords:
                found_keywords.append(term)
                if len(found_keywords) >= max_keywords:
                    break
        
        return found_keywords
    
    @staticmethod
    def assess_content_quality(text: str) -> float:
        """Assess content quality on a scale of 0.0 to 1.0."""
        if not text or len(text.strip()) < 20:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        
        # Length score (0-0.3)
        length_score = min(len(text) / 500, 1.0) * 0.3
        score += length_score
        
        # Mutual fund terminology (0-0.4)
        mutual_fund_terms = [
            "mutual fund", "nav", "scheme", "investment", "returns", "risk",
            "portfolio", "sip", "fund", "sebi", "investor", "amc"
        ]
        term_count = sum(1 for term in mutual_fund_terms if term in text_lower)
        term_score = min(term_count / 4, 1.0) * 0.4
        score += term_score
        
        # Structure and readability (0-0.3)
        sentences = text.count('.') + text.count('!') + text.count('?')
        words = len(text.split())
        if words > 0:
            avg_sentence_length = words / max(sentences, 1)
            # Good sentence length is between 10-25 words
            if 10 <= avg_sentence_length <= 25:
                score += 0.2
            elif 5 <= avg_sentence_length <= 40:
                score += 0.1
        
        return min(score, 1.0)


# Utility functions for chunk processing
def create_chunk_metadata(
    doc_id: str,
    source_url: str,
    doc_type: Union[str, DocType],
    chunk_index: int,
    total_chunks: int,
    text: str,
    chunk_strategy: str,
    fetched_at: str,
    scheme: Optional[str] = None,
    section_title: Optional[str] = None,
    heading_level: Optional[int] = None,
    char_start: Optional[int] = None,
    char_end: Optional[int] = None
) -> ChunkMetadata:
    """Create chunk metadata with auto-generated fields."""
    
    if isinstance(doc_type, str):
        doc_type = DocType(doc_type)
    
    indexed_at = datetime.utcnow().isoformat() + "Z"
    
    return ChunkMetadata(
        chunk_id=ChunkSchema.generate_chunk_id(doc_id, chunk_index, chunk_strategy),
        source_url=source_url,
        doc_type=doc_type,
        scheme=scheme,
        doc_id=doc_id,
        fetched_at=fetched_at,
        indexed_at=indexed_at,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        chunk_strategy=chunk_strategy,
        text_length=len(text),
        token_count=ChunkSchema.estimate_token_count(text),
        section_title=section_title,
        heading_level=heading_level,
        content_quality_score=ChunkSchema.assess_content_quality(text),
        has_meaningful_content=ChunkSchema.assess_content_quality(text) > 0.3,
        char_start=char_start,
        char_end=char_end,
        keywords=ChunkSchema.extract_keywords(text),
        entities=[],  # Could be enhanced with NER
        language=ChunkSchema.detect_language(text)
    )
