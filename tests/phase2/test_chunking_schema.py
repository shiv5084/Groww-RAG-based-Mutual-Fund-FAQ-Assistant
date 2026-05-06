"""Test cases for Phase 2 chunking schema and metadata."""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase2_chunking.schema import (
    Chunk,
    ChunkMetadata,
    ChunkSchema,
    DocType,
    create_chunk_metadata
)


class TestChunkMetadata:
    """Test chunk metadata creation and validation."""
    
    def test_chunk_metadata_creation(self):
        """Test creating chunk metadata with all fields."""
        metadata = ChunkMetadata(
            chunk_id="DOC-001_section_aware_0000",
            source_url="https://example.com/fund",
            doc_type=DocType.SCHEME_PAGE,
            scheme="HDFC-LargeCap",
            doc_id="DOC-001",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=0,
            total_chunks=5,
            chunk_strategy="section_aware",
            text_length=250,
            token_count=62,
            section_title="Investment Objective",
            heading_level=2,
            content_quality_score=0.8,
            has_meaningful_content=True,
            char_start=100,
            char_end=350,
            keywords=["mutual fund", "investment", "returns"],
            entities=["HDFC", "Large Cap"],
            language="en"
        )
        
        assert metadata.chunk_id == "DOC-001_section_aware_0000"
        assert metadata.source_url == "https://example.com/fund"
        assert metadata.doc_type == DocType.SCHEME_PAGE
        assert metadata.scheme == "HDFC-LargeCap"
        assert metadata.doc_id == "DOC-001"
        assert metadata.fetched_at == "2023-12-01T10:00:00Z"
        assert metadata.indexed_at == "2023-12-01T10:05:00Z"
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 5
        assert metadata.chunk_strategy == "section_aware"
        assert metadata.text_length == 250
        assert metadata.token_count == 62
        assert metadata.section_title == "Investment Objective"
        assert metadata.heading_level == 2
        assert metadata.content_quality_score == 0.8
        assert metadata.has_meaningful_content is True
        assert metadata.char_start == 100
        assert metadata.char_end == 350
        assert metadata.keywords == ["mutual fund", "investment", "returns"]
        assert metadata.entities == ["HDFC", "Large Cap"]
        assert metadata.language == "en"
    
    def test_chunk_metadata_minimal(self):
        """Test creating chunk metadata with minimal required fields."""
        metadata = ChunkMetadata(
            chunk_id="DOC-002_fixed_0000",
            source_url="https://example.com/short",
            doc_type=DocType.GENERAL,
            scheme=None,
            doc_id="DOC-002",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=0,
            total_chunks=1,
            chunk_strategy="fixed_window",
            text_length=50,
            token_count=12,
            section_title=None,
            heading_level=None,
            content_quality_score=0.2,
            has_meaningful_content=False,
            char_start=None,
            char_end=None,
            keywords=[],
            entities=[],
            language="en"
        )
        
        assert metadata.chunk_id == "DOC-002_fixed_0000"
        assert metadata.scheme is None
        assert metadata.section_title is None
        assert metadata.heading_level is None
        assert metadata.has_meaningful_content is False
        assert metadata.keywords == []
        assert metadata.entities == []
    
    def test_chunk_metadata_serialization(self):
        """Test chunk metadata serialization to/from dict."""
        original = ChunkMetadata(
            chunk_id="DOC-003_hybrid_0001",
            source_url="https://example.com/test",
            doc_type=DocType.FACTSHEET,
            scheme="Test-Scheme",
            doc_id="DOC-003",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=1,
            total_chunks=3,
            chunk_strategy="hybrid",
            text_length=300,
            token_count=75,
            section_title="Performance Metrics",
            heading_level=3,
            content_quality_score=0.9,
            has_meaningful_content=True,
            char_start=200,
            char_end=500,
            keywords=["performance", "returns", "nav"],
            entities=["HDFC", "NAV"],
            language="en"
        )
        
        # Convert to dict
        metadata_dict = original.to_dict()
        assert isinstance(metadata_dict, dict)
        assert metadata_dict["chunk_id"] == "DOC-003_hybrid_0001"
        assert metadata_dict["doc_type"] == "factsheet"  # Enum converted to string
        
        # Convert back from dict
        restored = ChunkMetadata.from_dict(metadata_dict)
        assert restored.chunk_id == original.chunk_id
        assert restored.source_url == original.source_url
        assert restored.doc_type == original.doc_type
        assert restored.scheme == original.scheme
        assert restored.doc_id == original.doc_id
        assert restored.fetched_at == original.fetched_at
        assert restored.indexed_at == original.indexed_at
        assert restored.chunk_index == original.chunk_index
        assert restored.total_chunks == original.total_chunks
        assert restored.chunk_strategy == original.chunk_strategy
        assert restored.text_length == original.text_length
        assert restored.token_count == original.token_count
        assert restored.section_title == original.section_title
        assert restored.heading_level == original.heading_level
        assert restored.content_quality_score == original.content_quality_score
        assert restored.has_meaningful_content == original.has_meaningful_content
        assert restored.char_start == original.char_start
        assert restored.char_end == original.char_end
        assert restored.keywords == original.keywords
        assert restored.entities == original.entities
        assert restored.language == original.language


class TestChunk:
    """Test chunk creation and serialization."""
    
    def test_chunk_creation(self):
        """Test creating a chunk with text and metadata."""
        metadata = ChunkMetadata(
            chunk_id="DOC-004_section_0002",
            source_url="https://example.com/chunk",
            doc_type=DocType.SCHEME_PAGE,
            scheme=None,
            doc_id="DOC-004",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=2,
            total_chunks=4,
            chunk_strategy="section",
            text_length=192,
            token_count=45,
            section_title="Risk Factors",
            heading_level=2,
            content_quality_score=0.7,
            has_meaningful_content=True,
            char_start=300,
            char_end=480,
            keywords=["risk", "market", "volatility"],
            entities=["SEBI"],
            language="en"
        )
        
        chunk = Chunk(
            text="This chunk contains information about risk factors including market volatility, interest rate changes, and regulatory risks. Investors should carefully consider these factors before investing.",
            metadata=metadata
        )
        
        assert chunk.text == "This chunk contains information about risk factors including market volatility, interest rate changes, and regulatory risks. Investors should carefully consider these factors before investing."
        assert chunk.metadata.chunk_id == "DOC-004_section_0002"
        assert chunk.metadata.section_title == "Risk Factors"
        assert len(chunk.text) == chunk.metadata.text_length
    
    def test_chunk_serialization(self):
        """Test chunk serialization to/from JSONL."""
        original = Chunk(
            text="HDFC Mutual Fund offers various investment schemes including equity, debt, and hybrid funds for different risk profiles.",
            metadata=ChunkMetadata(
                chunk_id="DOC-005_fixed_0000",
                source_url="https://hdfcfund.com/schemes",
                doc_type=DocType.INVESTOR_GUIDE,
                scheme=None,
                doc_id="DOC-005",
                fetched_at="2023-12-01T10:00:00Z",
                indexed_at="2023-12-01T10:05:00Z",
                chunk_index=0,
                total_chunks=1,
                chunk_strategy="fixed_window",
                text_length=192,
                token_count=45,
                section_title=None,
                heading_level=None,
                content_quality_score=0.6,
                has_meaningful_content=True,
                char_start=None,
                char_end=None,
                keywords=["hdfc", "mutual fund", "investment", "schemes"],
                entities=["HDFC"],
                language="en"
            )
        )
        
        # Convert to JSONL
        jsonl_line = original.to_jsonl()
        assert isinstance(jsonl_line, str)
        
        # Parse back from JSONL
        restored = Chunk.from_jsonl(jsonl_line)
        assert restored.text == original.text
        assert restored.metadata.chunk_id == original.metadata.chunk_id
        assert restored.metadata.source_url == original.metadata.source_url
        assert restored.metadata.doc_type == original.metadata.doc_type
        assert restored.metadata.text_length == original.metadata.text_length
    
    def test_chunk_jsonl_roundtrip(self):
        """Test chunk JSONL roundtrip maintains all data."""
        original = Chunk(
            text="The fund's NAV is updated daily and reflects the current market value of investments.",
            metadata=ChunkMetadata(
                chunk_id="DOC-006_hybrid_0001",
                source_url="https://example.com/nav",
                doc_type=DocType.FACTSHEET,
                scheme="Growth-Fund",
                doc_id="DOC-006",
                fetched_at="2023-12-01T10:00:00Z",
                indexed_at="2023-12-01T10:05:00Z",
                chunk_index=1,
                total_chunks=2,
                chunk_strategy="hybrid",
                text_length=85,
                token_count=21,
                section_title="NAV Information",
                heading_level=3,
                content_quality_score=0.8,
                has_meaningful_content=True,
                char_start=100,
                char_end=185,
                keywords=["nav", "market value", "investments"],
                entities=["NAV"],
                language="en"
            )
        )
        
        # Multiple roundtrips
        current = original
        for i in range(3):
            jsonl_line = current.to_jsonl()
            current = Chunk.from_jsonl(jsonl_line)
        
        # Verify data integrity
        assert current.text == original.text
        assert current.metadata.chunk_id == original.metadata.chunk_id
        assert current.metadata.source_url == original.metadata.source_url
        assert current.metadata.doc_type == original.metadata.doc_type
        assert current.metadata.scheme == original.metadata.scheme
        assert current.metadata.doc_id == original.metadata.doc_id
        assert current.metadata.fetched_at == original.metadata.fetched_at
        assert current.metadata.indexed_at == original.metadata.indexed_at
        assert current.metadata.chunk_index == original.metadata.chunk_index
        assert current.metadata.total_chunks == original.metadata.total_chunks
        assert current.metadata.chunk_strategy == original.metadata.chunk_strategy
        assert current.metadata.text_length == original.metadata.text_length
        assert current.metadata.token_count == original.metadata.token_count
        assert current.metadata.section_title == original.metadata.section_title
        assert current.metadata.heading_level == original.metadata.heading_level
        assert current.metadata.content_quality_score == original.metadata.content_quality_score
        assert current.metadata.has_meaningful_content == original.metadata.has_meaningful_content
        assert current.metadata.char_start == original.metadata.char_start
        assert current.metadata.char_end == original.metadata.char_end
        assert current.metadata.keywords == original.metadata.keywords
        assert current.metadata.entities == original.metadata.entities
        assert current.metadata.language == original.metadata.language


class TestChunkSchema:
    """Test chunk schema validation and utilities."""
    
    def test_validate_metadata_valid(self):
        """Test validating valid metadata."""
        metadata = ChunkMetadata(
            chunk_id="DOC-007_valid_0000",
            source_url="https://example.com/valid",
            doc_type=DocType.SCHEME_PAGE,
            scheme=None,
            doc_id="DOC-007",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=0,
            total_chunks=1,
            chunk_strategy="valid",
            text_length=200,
            token_count=50,
            section_title=None,
            heading_level=None,
            content_quality_score=0.7,
            has_meaningful_content=True,
            char_start=None,
            char_end=None,
            keywords=[],
            entities=[],
            language="en"
        )
        
        issues = ChunkSchema.validate_metadata(metadata)
        assert len(issues) == 0
    
    def test_validate_metadata_missing_fields(self):
        """Test validating metadata with missing required fields."""
        # Test missing chunk_id
        metadata = ChunkMetadata(
            chunk_id="",  # Empty chunk_id
            source_url="https://example.com",
            doc_type=DocType.GENERAL,
            scheme=None,
            doc_id="DOC-008",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=0,
            total_chunks=1,
            chunk_strategy="test",
            text_length=100,
            token_count=25,
            section_title=None,
            heading_level=None,
            content_quality_score=0.5,
            has_meaningful_content=True,
            char_start=None,
            char_end=None,
            keywords=[],
            entities=[],
            language="en"
        )
        
        issues = ChunkSchema.validate_metadata(metadata)
        assert "Missing chunk_id" in issues
    
    def test_validate_metadata_invalid_url(self):
        """Test validating metadata with invalid URL."""
        metadata = ChunkMetadata(
            chunk_id="DOC-009_invalid_url",
            source_url="invalid-url",  # Invalid URL format
            doc_type=DocType.GENERAL,
            scheme=None,
            doc_id="DOC-009",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=0,
            total_chunks=1,
            chunk_strategy="test",
            text_length=100,
            token_count=25,
            section_title=None,
            heading_level=None,
            content_quality_score=0.5,
            has_meaningful_content=True,
            char_start=None,
            char_end=None,
            keywords=[],
            entities=[],
            language="en"
        )
        
        issues = ChunkSchema.validate_metadata(metadata)
        assert "Invalid source_url format" in issues
    
    def test_validate_metadata_invalid_indices(self):
        """Test validating metadata with invalid chunk indices."""
        metadata = ChunkMetadata(
            chunk_id="DOC-010_invalid_indices",
            source_url="https://example.com",
            doc_type=DocType.GENERAL,
            scheme=None,
            doc_id="DOC-010",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=5,  # Invalid: chunk_index >= total_chunks
            total_chunks=3,
            chunk_strategy="test",
            text_length=100,
            token_count=25,
            section_title=None,
            heading_level=None,
            content_quality_score=0.5,
            has_meaningful_content=True,
            char_start=None,
            char_end=None,
            keywords=[],
            entities=[],
            language="en"
        )
        
        issues = ChunkSchema.validate_metadata(metadata)
        assert "chunk_index >= total_chunks" in issues
    
    def test_validate_metadata_invalid_quality_score(self):
        """Test validating metadata with invalid quality score."""
        metadata = ChunkMetadata(
            chunk_id="DOC-011_invalid_quality",
            source_url="https://example.com",
            doc_type=DocType.GENERAL,
            scheme=None,
            doc_id="DOC-011",
            fetched_at="2023-12-01T10:00:00Z",
            indexed_at="2023-12-01T10:05:00Z",
            chunk_index=0,
            total_chunks=1,
            chunk_strategy="test",
            text_length=100,
            token_count=25,
            section_title=None,
            heading_level=None,
            content_quality_score=1.5,  # Invalid: > 1.0
            has_meaningful_content=True,
            char_start=None,
            char_end=None,
            keywords=[],
            entities=[],
            language="en"
        )
        
        issues = ChunkSchema.validate_metadata(metadata)
        assert "content_quality_score must be between 0.0 and 1.0" in issues
    
    def test_validate_chunk_valid(self):
        """Test validating a complete valid chunk."""
        chunk = Chunk(
            text="This is a valid chunk with sufficient content and proper metadata.",
            metadata=ChunkMetadata(
                chunk_id="DOC-012_valid_chunk",
                source_url="https://example.com/valid",
                doc_type=DocType.SCHEME_PAGE,
                scheme=None,
                doc_id="DOC-012",
                fetched_at="2023-12-01T10:00:00Z",
                indexed_at="2023-12-01T10:05:00Z",
                chunk_index=0,
                total_chunks=1,
                chunk_strategy="valid",
                text_length=66,
                token_count=19,
                section_title=None,
                heading_level=None,
                content_quality_score=0.6,
                has_meaningful_content=True,
                char_start=None,
                char_end=None,
                keywords=[],
                entities=[],
                language="en"
            )
        )
        
        issues = ChunkSchema.validate_chunk(chunk)
        assert len(issues) == 0
    
    def test_validate_chunk_empty_text(self):
        """Test validating chunk with empty text."""
        chunk = Chunk(
            text="",  # Empty text
            metadata=ChunkMetadata(
                chunk_id="DOC-013_empty",
                source_url="https://example.com/empty",
                doc_type=DocType.GENERAL,
                scheme=None,
                doc_id="DOC-013",
                fetched_at="2023-12-01T10:00:00Z",
                indexed_at="2023-12-01T10:05:00Z",
                chunk_index=0,
                total_chunks=1,
                chunk_strategy="empty",
                text_length=0,
                token_count=0,
                section_title=None,
                heading_level=None,
                content_quality_score=0.0,
                has_meaningful_content=False,
                char_start=None,
                char_end=None,
                keywords=[],
                entities=[],
                language="en"
            )
        )
        
        issues = ChunkSchema.validate_chunk(chunk)
        assert "Empty chunk text" in issues
    
    def test_validate_chunk_text_length_mismatch(self):
        """Test validating chunk with text length mismatch."""
        chunk = Chunk(
            text="Short text",  # 10 characters
            metadata=ChunkMetadata(
                chunk_id="DOC-014_mismatch",
                source_url="https://example.com/mismatch",
                doc_type=DocType.GENERAL,
                scheme=None,
                doc_id="DOC-014",
                fetched_at="2023-12-01T10:00:00Z",
                indexed_at="2023-12-01T10:05:00Z",
                chunk_index=0,
                total_chunks=1,
                chunk_strategy="mismatch",
                text_length=100,  # Mismatch: actual length is 10
                token_count=25,
                section_title=None,
                heading_level=None,
                content_quality_score=0.5,
                has_meaningful_content=True,
                char_start=None,
                char_end=None,
                keywords=[],
                entities=[],
                language="en"
            )
        )
        
        issues = ChunkSchema.validate_chunk(chunk)
        assert "text_length in metadata doesn't match actual text length" in issues
    
    def test_generate_chunk_id(self):
        """Test chunk ID generation."""
        chunk_id = ChunkSchema.generate_chunk_id("DOC-015", 0, "section_aware")
        assert chunk_id == "DOC-015_section_aware_0000"
        
        chunk_id = ChunkSchema.generate_chunk_id("DOC-016", 5, "fixed_window")
        assert chunk_id == "DOC-016_fixed_window_0005"
        
        chunk_id = ChunkSchema.generate_chunk_id("DOC-017", 123, "hybrid")
        assert chunk_id == "DOC-017_hybrid_0123"
    
    def test_estimate_token_count(self):
        """Test token count estimation."""
        # Short text
        count = ChunkSchema.estimate_token_count("Short text")
        assert count == 2  # "Short text" is 10 chars / 4 = 2.5, rounded down to 2
        
        # Longer text
        count = ChunkSchema.estimate_token_count("This is a longer text with multiple words for testing.")
        assert count > 10
        
        # Empty text
        count = ChunkSchema.estimate_token_count("")
        assert count == 1  # Minimum 1 token
    
    def test_detect_language(self):
        """Test language detection."""
        # English text
        lang = ChunkSchema.detect_language("This is English text about mutual funds and investments.")
        assert lang == "en"
        
        # Hindi text (with Hindi indicators)
        lang = ChunkSchema.detect_language("यह हिंदी टेक्स्ट है निवेश योजनाओं के बारे में")
        assert lang == "hi"
        
        # Mixed text (should default to English)
        lang = ChunkSchema.detect_language("This text has निवेश some Hindi words")
        assert lang == "hi"  # Should detect Hindi presence
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        text = "This mutual fund scheme offers SIP investments with good returns and low risk. The NAV is updated regularly."
        keywords = ChunkSchema.extract_keywords(text)
        
        # Should extract relevant mutual fund keywords
        assert "mutual fund" in keywords
        assert "scheme" in keywords
        assert "sip" in keywords
        assert "investment" in keywords
        assert "returns" in keywords
        assert "risk" in keywords
        assert "nav" in keywords
        
        # Should limit to reasonable number
        assert len(keywords) <= 10
    
    def test_assess_content_quality(self):
        """Test content quality assessment."""
        # High quality text
        high_quality = """
        HDFC Mutual Fund offers comprehensive investment solutions for Indian investors. 
        The HDFC Large Cap Fund invests in established companies with strong fundamentals 
        and follows a systematic investment approach with regular portfolio rebalancing.
        """
        score = ChunkSchema.assess_content_quality(high_quality)
        assert score > 0.5
        
        # Low quality text
        low_quality = "Short"
        score = ChunkSchema.assess_content_quality(low_quality)
        assert score < 0.3
        
        # Empty text
        score = ChunkSchema.assess_content_quality("")
        assert score == 0.0
        
        # Medium quality text
        medium_quality = "This is medium length text with some mutual fund terms like nav and scheme."
        score = ChunkSchema.assess_content_quality(medium_quality)
        assert 0.3 <= score <= 0.7


class TestCreateChunkMetadata:
    """Test chunk metadata creation utility function."""
    
    def test_create_chunk_metadata_basic(self):
        """Test creating chunk metadata with basic parameters."""
        metadata = create_chunk_metadata(
            doc_id="DOC-018",
            source_url="https://example.com/basic",
            doc_type=DocType.SCHEME_PAGE,
            chunk_index=0,
            total_chunks=1,
            text="This is basic text for testing metadata creation.",
            chunk_strategy="section_aware",
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert metadata.doc_id == "DOC-018"
        assert metadata.source_url == "https://example.com/basic"
        assert metadata.doc_type == DocType.SCHEME_PAGE
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 1
        assert metadata.chunk_strategy == "section_aware"
        assert metadata.fetched_at == "2023-12-01T10:00:00Z"
        
        # Auto-generated fields
        assert metadata.chunk_id == "DOC-018_section_aware_0000"
        assert metadata.indexed_at is not None  # Should be auto-generated
        assert metadata.text_length == len("This is basic text for testing metadata creation.")
        assert metadata.token_count > 0
        assert metadata.content_quality_score is not None
        assert metadata.has_meaningful_content is not None
        assert metadata.keywords is not None
        assert metadata.language is not None
    
    def test_create_chunk_metadata_with_optional_fields(self):
        """Test creating chunk metadata with optional fields."""
        metadata = create_chunk_metadata(
            doc_id="DOC-019",
            source_url="https://example.com/optional",
            doc_type="factsheet",  # String instead of enum
            chunk_index=1,
            total_chunks=3,
            text="This text has optional fields like section title and heading level.",
            chunk_strategy="section_aware",
            fetched_at="2023-12-01T10:00:00Z",
            scheme="Test-Scheme",
            section_title="Performance Metrics",
            heading_level=3,
            char_start=100,
            char_end=200
        )
        
        assert metadata.scheme == "Test-Scheme"
        assert metadata.section_title == "Performance Metrics"
        assert metadata.heading_level == 3
        assert metadata.char_start == 100
        assert metadata.char_end == 200
        assert metadata.doc_type == DocType.FACTSHEET  # Should be converted to enum
    
    def test_create_chunk_metadata_string_doc_type(self):
        """Test creating chunk metadata with string doc_type."""
        metadata = create_chunk_metadata(
            doc_id="DOC-020",
            source_url="https://example.com/string_type",
            doc_type="investor_guide",  # String
            chunk_index=0,
            total_chunks=1,
            text="Test text with string doc_type.",
            chunk_strategy="fixed_window",
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert metadata.doc_type == DocType.INVESTOR_GUIDE  # Should be converted to enum


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
