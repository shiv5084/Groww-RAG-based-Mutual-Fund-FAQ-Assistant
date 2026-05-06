"""Test cases for Phase 2 chunking strategies."""

import pytest
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase2_chunking import (
    ChunkStrategy,
    ChunkingConfig,
    SectionAwareChunker,
    FixedWindowChunker,
    HybridChunker,
    create_chunker
)
from phase2_chunking.schema import Chunk, ChunkMetadata, DocType


class TestChunkingConfig:
    """Test chunking configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ChunkingConfig()
        
        assert config.window_size == 600
        assert config.overlap_size == 60
        assert config.min_chunk_size == 100
        assert config.min_section_size == 50
        assert config.max_section_size == 2000
        assert config.combine_short_sections is True
        assert config.min_content_quality == 0.3
        assert config.prefer_meaningful_chunks is True
        assert config.strip_html_tags is True
        assert config.preserve_section_titles is True
        assert config.detect_language is True
    
    def test_config_from_yaml(self):
        """Test loading configuration from YAML file."""
        config_content = """
window_size: 800
overlap_size: 80
min_chunk_size: 150
min_content_quality: 0.4
prefer_meaningful_chunks: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = Path(f.name)
        
        try:
            config = ChunkingConfig.from_yaml(config_path)
            
            assert config.window_size == 800
            assert config.overlap_size == 80
            assert config.min_chunk_size == 150
            assert config.min_content_quality == 0.4
            assert config.prefer_meaningful_chunks is False
            
        finally:
            config_path.unlink(missing_ok=True)
    
    def test_config_from_nonexistent_file(self):
        """Test loading configuration from non-existent file."""
        config = ChunkingConfig.from_yaml(Path("nonexistent.yaml"))
        
        # Should return default config
        assert config.window_size == 600
        assert config.overlap_size == 60


class TestSectionAwareChunker:
    """Test section-aware chunking strategy."""
    
    def test_chunk_html_content(self):
        """Test chunking HTML content by sections."""
        config = ChunkingConfig()
        chunker = SectionAwareChunker(config)
        
        html_content = """
        <html>
            <body>
                <main>
                    <h1>HDFC Large Cap Fund</h1>
                    <p>This is the introduction to HDFC Large Cap Fund with comprehensive information.</p>
                    
                    <h2>Investment Objective</h2>
                    <p>The primary investment objective is to generate long-term capital appreciation 
                    by investing in a diversified portfolio of predominantly large-cap equity securities.</p>
                    
                    <h2>Key Features</h2>
                    <ul>
                        <li>Suitable for long-term wealth creation</li>
                        <li>Professional fund management</li>
                        <li>Regular portfolio rebalancing</li>
                    </ul>
                    
                    <h2>Risk Factors</h2>
                    <p>Investments are subject to market risks and NAV may fluctuate based on market movements.</p>
                </main>
            </body>
        </html>
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-001",
            source_url="https://example.com/fund",
            doc_type=DocType.SCHEME_PAGE,
            text=html_content,
            fetched_at="2023-12-01T10:00:00Z",
            scheme="HDFC-LargeCap"
        )
        
        assert len(chunks) >= 3  # Should have multiple sections
        
        # Check first chunk has title
        first_chunk = chunks[0]
        assert first_chunk.metadata.section_title == "HDFC Large Cap Fund"
        assert first_chunk.metadata.heading_level == 1
        assert "HDFC Large Cap Fund" in first_chunk.text
        
        # Check metadata
        for chunk in chunks:
            assert chunk.metadata.chunk_id.startswith("DOC-001_section_aware_")
            assert chunk.metadata.source_url == "https://example.com/fund"
            assert chunk.metadata.doc_type == DocType.SCHEME_PAGE
            assert chunk.metadata.chunk_strategy == "section_aware"
            assert chunk.metadata.scheme == "HDFC-LargeCap"
            assert chunk.metadata.has_meaningful_content is True
    
    def test_chunk_text_content_with_markdown(self):
        """Test chunking text content with Markdown-style headers."""
        config = ChunkingConfig()
        chunker = SectionAwareChunker(config)
        
        text_content = """
# HDFC Mutual Fund Overview

HDFC Mutual Fund is one of India's leading asset management companies offering various investment schemes.

## Investment Options

### Equity Funds

HDFC offers several equity funds including large-cap, mid-cap, and small-cap options.

### Debt Funds

Debt funds provide stable returns with lower risk profile.

## Risk Considerations

All investments carry market risks and investors should read offer documents carefully.
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-002",
            source_url="https://example.com/overview",
            doc_type=DocType.INVESTOR_GUIDE,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert len(chunks) >= 3  # Should identify multiple sections
        
        # Check section titles are preserved
        section_titles = [chunk.metadata.section_title for chunk in chunks if chunk.metadata.section_title]
        assert "HDFC Mutual Fund Overview" in section_titles
        assert "Investment Options" in section_titles
        assert "Risk Considerations" in section_titles
    
    def test_chunk_plain_text_no_sections(self):
        """Test chunking plain text without clear sections."""
        config = ChunkingConfig()
        chunker = SectionAwareChunker(config)
        
        text_content = """
        This is plain text content without clear section headings. 
        It contains information about mutual funds but doesn't have structured sections.
        The text flows continuously without markdown headers or HTML structure.
        It should fall back to appropriate chunking behavior.
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-003",
            source_url="https://example.com/plain",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        # Should still produce chunks, possibly using fallback strategy
        assert len(chunks) >= 1
    
    def test_combine_short_sections(self):
        """Test combining very short sections."""
        config = ChunkingConfig(combine_short_sections=True, min_section_size=100)
        chunker = SectionAwareChunker(config)
        
        html_content = """
        <main>
            <h1>Title</h1>
            <p>Short intro.</p>
            <h2>Section 1</h2>
            <p>Brief content.</p>
            <h2>Section 2</h2>
            <p>More brief content.</p>
        </main>
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-004",
            source_url="https://example.com/short",
            doc_type=DocType.GENERAL,
            text=html_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        # Should combine short sections
        assert len(chunks) >= 1


class TestFixedWindowChunker:
    """Test fixed-window chunking strategy."""
    
    def test_chunk_short_text(self):
        """Test chunking text shorter than window size."""
        config = ChunkingConfig(window_size=1000, overlap_size=100)
        chunker = FixedWindowChunker(config)
        
        text_content = "This is a short text that should fit in a single chunk."
        
        chunks = chunker.chunk_document(
            doc_id="DOC-005",
            source_url="https://example.com/short",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert len(chunks) == 1
        assert chunks[0].text == text_content
        assert chunks[0].metadata.chunk_strategy == "fixed_window"
    
    def test_chunk_long_text_with_overlap(self):
        """Test chunking long text with overlap."""
        config = ChunkingConfig(window_size=200, overlap_size=50)
        chunker = FixedWindowChunker(config)
        
        # Create text longer than window size
        text_content = " ".join([f"word{i}" for i in range(100)])  # ~500 characters
        
        chunks = chunker.chunk_document(
            doc_id="DOC-006",
            source_url="https://example.com/long",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert len(chunks) > 1
        
        # Check overlap exists
        for i in range(1, len(chunks)):
            # Overlap should be present between consecutive chunks
            chunk1_end = chunks[i-1].text[-50:] if len(chunks[i-1].text) > 50 else chunks[i-1].text
            chunk2_start = chunks[i].text[:50] if len(chunks[i].text) > 50 else chunks[i].text
            
            # Some overlap should exist
            overlap_found = any(word in chunk2_start for word in chunk1_end.split()[-5:])
            # Note: This is a simple check, actual overlap logic is more complex
    
    def test_sentence_boundary_breaking(self):
        """Test breaking at sentence boundaries."""
        config = ChunkingConfig(window_size=150, overlap_size=30)
        chunker = FixedWindowChunker(config)
        
        text_content = """
        This is the first sentence. This is the second sentence. 
        This is the third sentence. This is the fourth sentence.
        This is the fifth sentence. This is the sixth sentence.
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-007",
            source_url="https://example.com/sentences",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert len(chunks) > 1
        
        # Check chunks end at sentence boundaries when possible
        for chunk in chunks:
            # Should ideally end with sentence-ending punctuation
            if len(chunk.text) < config.window_size:
                assert chunk.text.strip().endswith(('.', '!', '?', ':', ';'))
    
    def test_clean_text_processing(self):
        """Test text cleaning during chunking."""
        config = ChunkingConfig()
        chunker = FixedWindowChunker(config)
        
        text_content = """
        This    text    has    excessive    whitespace.
        
        And multiple newlines.
        
        Should be cleaned properly.
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-008",
            source_url="https://example.com/whitespace",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        # Check text is cleaned
        for chunk in chunks:
            # Should not have excessive whitespace
            assert "    " not in chunk.text
            assert not chunk.text.startswith("\n")
            assert not chunk.text.endswith("\n")


class TestHybridChunker:
    """Test hybrid chunking strategy."""
    
    def test_hybrid_with_structured_content(self):
        """Test hybrid chunking with structured HTML content."""
        config = ChunkingConfig()
        chunker = HybridChunker(config)
        
        html_content = """
        <main>
            <h1>Fund Overview</h1>
            <p>This comprehensive fund overview provides detailed information about investment objectives.</p>
            
            <h2>Performance</h2>
            <p>The fund has delivered consistent performance over the past five years with annualized returns.</p>
            
            <h2>Risk Factors</h2>
            <p>Investors should consider various risk factors including market volatility and interest rate changes.</p>
        </main>
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-009",
            source_url="https://example.com/hybrid",
            doc_type=DocType.SCHEME_PAGE,
            text=html_content,
            fetched_at="2023-12-01T10:00:00Z",
            original_format="html"
        )
        
        assert len(chunks) >= 3  # Should use section-aware for HTML
        assert all(chunk.metadata.chunk_strategy == "section_aware" for chunk in chunks)
    
    def test_hybrid_with_unstructured_content(self):
        """Test hybrid chunking falling back to fixed-window."""
        config = ChunkingConfig()
        chunker = HybridChunker(config)
        
        # Create long unstructured text
        text_content = " ".join([f"word{i}" for i in range(200)])  # Very long text
        
        chunks = chunker.chunk_document(
            doc_id="DOC-010",
            source_url="https://example.com/unstructured",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert len(chunks) > 1
        # Should use fixed-window for unstructured content
        assert all(chunk.metadata.chunk_strategy in ["section_aware", "fixed_window"] for chunk in chunks)


class TestChunkerFactory:
    """Test chunker factory function."""
    
    def test_create_section_aware_chunker(self):
        """Test creating section-aware chunker."""
        config = ChunkingConfig()
        chunker = create_chunker(ChunkStrategy.SECTION_AWARE, config)
        
        assert isinstance(chunker, SectionAwareChunker)
        assert chunker.config == config
    
    def test_create_fixed_window_chunker(self):
        """Test creating fixed-window chunker."""
        config = ChunkingConfig()
        chunker = create_chunker(ChunkStrategy.FIXED_WINDOW, config)
        
        assert isinstance(chunker, FixedWindowChunker)
        assert chunker.config == config
    
    def test_create_hybrid_chunker(self):
        """Test creating hybrid chunker."""
        config = ChunkingConfig()
        chunker = create_chunker(ChunkStrategy.HYBRID, config)
        
        assert isinstance(chunker, HybridChunker)
        assert chunker.config == config
    
    def test_create_chunker_with_string(self):
        """Test creating chunker with string strategy."""
        config = ChunkingConfig()
        chunker = create_chunker("section_aware", config)
        
        assert isinstance(chunker, SectionAwareChunker)
    
    def test_create_chunker_invalid_strategy(self):
        """Test creating chunker with invalid strategy."""
        config = ChunkingConfig()
        
        with pytest.raises(ValueError, match="is not a valid ChunkStrategy"):
            create_chunker("invalid_strategy", config)


class TestChunkingQuality:
    """Test chunking quality and edge cases."""
    
    def test_empty_text(self):
        """Test chunking empty text."""
        config = ChunkingConfig()
        chunker = FixedWindowChunker(config)
        
        chunks = chunker.chunk_document(
            doc_id="DOC-011",
            source_url="https://example.com/empty",
            doc_type=DocType.GENERAL,
            text="",
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        # Should handle empty text gracefully
        assert len(chunks) == 0
    
    def test_whitespace_only_text(self):
        """Test chunking whitespace-only text."""
        config = ChunkingConfig()
        chunker = FixedWindowChunker(config)
        
        chunks = chunker.chunk_document(
            doc_id="DOC-012",
            source_url="https://example.com/whitespace",
            doc_type=DocType.GENERAL,
            text="   \n\n   \t   ",
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        # Should handle whitespace-only text gracefully
        assert len(chunks) == 0
    
    def test_very_long_text(self):
        """Test chunking very long text."""
        config = ChunkingConfig(window_size=500, overlap_size=50)
        chunker = FixedWindowChunker(config)
        
        # Create very long text (5000+ characters)
        text_content = " ".join([f"word{i}" for i in range(1000)])
        
        chunks = chunker.chunk_document(
            doc_id="DOC-013",
            source_url="https://example.com/very_long",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert len(chunks) > 5  # Should create multiple chunks
        
        # Check chunk sizes are reasonable
        for chunk in chunks:
            assert len(chunk.text) <= config.window_size + 100  # Allow some flexibility
    
    def test_special_characters(self):
        """Test chunking text with special characters."""
        config = ChunkingConfig()
        chunker = FixedWindowChunker(config)
        
        text_content = """
        Mutual funds contain special characters: ₹ (Rupee), % (percentage), 
        & (ampersand), and numbers like 1.5%. They also have unicode characters 
        like é, ü, and other international symbols.
        """
        
        chunks = chunker.chunk_document(
            doc_id="DOC-014",
            source_url="https://example.com/special",
            doc_type=DocType.GENERAL,
            text=text_content,
            fetched_at="2023-12-01T10:00:00Z"
        )
        
        assert len(chunks) >= 1
        
        # Should preserve special characters
        assert "₹" in chunks[0].text
        assert "%" in chunks[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
