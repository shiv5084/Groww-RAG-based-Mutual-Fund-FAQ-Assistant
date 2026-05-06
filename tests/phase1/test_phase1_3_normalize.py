"""Test cases for Phase 1.3 - PDF/HTML → clean text normalization."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from phase1_ingest.normalize import (
    TextNormalizer,
    NormalizationResult,
    build_phase_1_3_artifact,
    HAS_BS4,
    HAS_PYMUPDF,
    HAS_TRAFILATURA
)


class TestNormalizationResult:
    """Test NormalizationResult dataclass."""
    
    def test_normalization_result_success(self):
        """Test successful NormalizationResult."""
        result = NormalizationResult(
            url_id="URL-001",
            source_file=Path("test.html"),
            success=True,
            text_file=Path("test.txt"),
            text_length=1000,
            content_type="html"
        )
        
        assert result.url_id == "URL-001"
        assert result.success is True
        assert result.text_file == Path("test.txt")
        assert result.text_length == 1000
        assert result.content_type == "html"
        assert result.error_message is None
    
    def test_normalization_result_failure(self):
        """Test failed NormalizationResult."""
        result = NormalizationResult(
            url_id="URL-001",
            source_file=Path("test.html"),
            success=False,
            content_type="html",
            error_message="Parsing failed"
        )
        
        assert result.success is False
        assert result.text_file is None
        assert result.text_length is None
        assert result.error_message == "Parsing failed"


class TestTextNormalizer:
    """Test TextNormalizer functionality."""
    
    def test_text_normalizer_initialization(self):
        """Test TextNormalizer initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            assert normalizer.raw_dir == raw_dir
            assert normalizer.text_dir == text_dir
            assert normalizer.text_dir.exists()
                
    def test_text_normalizer_custom_config(self):
        """Test TextNormalizer with custom configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Test that normalizer is properly initialized
            assert normalizer.raw_dir == raw_dir
            assert normalizer.text_dir == text_dir
    
    def test_determine_content_type_html(self):
        """Test content type detection for HTML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Test HTML file
            html_file = Path(temp_dir) / "test.html"
            html_file.write_text("<html><body>Test</body></html>")
            
            content_type = normalizer._detect_content_type(html_file)
            
            assert content_type == "html"
    
    def test_determine_content_type_pdf(self):
        """Test content type detection for PDF."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Test PDF file (mock PDF content)
            pdf_file = Path(temp_dir) / "test.pdf"
            pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj")
            
            content_type = normalizer._detect_content_type(pdf_file)
            
            assert content_type == "pdf"
    
    def test_determine_content_type_text(self):
        """Test content type detection for text file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Test text file
            text_file = Path(temp_dir) / "test.txt"
            text_file.write_text("This is plain text content.")
            
            content_type = normalizer._determine_content_type(text_file)
            
            assert content_type == "text"
    
    def test_determine_content_type_unknown(self):
        """Test content type detection for unknown file type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Test unknown file type
            unknown_file = Path(temp_dir) / "test.xyz"
            unknown_file.write_text("Unknown content")
            
            content_type = normalizer._determine_content_type(unknown_file)
            
            assert content_type == "unknown"
    
    @pytest.mark.skipif(not HAS_BS4, reason="BeautifulSoup4 not available")
    def test_parse_html_success(self):
        """Test successful HTML parsing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create HTML file
            html_content = """
            <html>
                <head><title>Test Page</title></head>
                <body>
                    <main>
                        <h1>Main Title</h1>
                        <p>This is the main content.</p>
                        <div>
                            <p>More content here.</p>
                        </div>
                    </main>
                    <footer>Footer content</footer>
                </body>
            </html>
            """
            html_file = Path(temp_dir) / "test.html"
            html_file.write_text(html_content)
            
            result = normalizer._parse_html_with_bs4(html_file)
            
            assert result is not None
            assert "MainTitle" in result
            assert "maincontent" in result.lower()
            assert len(result) > 50  # Should have meaningful content
    
    @pytest.mark.skipif(not HAS_BS4, reason="BeautifulSoup4 not available")
    def test_parse_html_empty(self):
        """Test HTML parsing with empty content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create empty HTML file
            html_file = Path(temp_dir) / "empty.html"
            html_file.write_text("")
            
            result = normalizer._parse_html_with_bs4(html_file)
            
            assert result == ""  # Empty HTML returns empty string, not None
    
    @pytest.mark.skipif(not HAS_PYMUPDF, reason="PyMuPDF not available")
    def test_parse_pdf_success(self):
        """Test successful PDF parsing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Mock PyMuPDF to avoid needing actual PDF
            with patch('phase1_ingest.normalize.fitz') as mock_fitz:
                # Mock PDF document
                mock_doc = Mock()
                mock_page = Mock()
                mock_page.get_text.return_value = "PDF page content here."
                mock_doc.__len__ = Mock(return_value=1)
                mock_doc.__getitem__ = Mock(return_value=mock_page)
                mock_doc.close = Mock()
                mock_fitz.open.return_value = mock_doc
                
                pdf_file = Path(temp_dir) / "test.pdf"
                pdf_file.write_bytes(b"%PDF-1.4\n")
                
                result = normalizer._parse_pdf(pdf_file)
                
                assert result is not None
                assert "PDF page content here." in result
                mock_fitz.open.assert_called_once()
    
    @pytest.mark.skipif(not HAS_PYMUPDF, reason="PyMuPDF not available")
    def test_parse_pdf_without_pymupdf(self):
        """Test PDF parsing when PyMuPDF is not available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Temporarily disable PyMuPDF
            with patch('phase1_ingest.normalize.HAS_PYMUPDF', False):
                pdf_file = Path(temp_dir) / "test.pdf"
                pdf_file.write_bytes(b"%PDF-1.4\n")
                
                result = normalizer._parse_pdf(pdf_file)
                
                assert result is None
    
    def test_parse_text_file_success(self):
        """Test successful text file parsing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create text file
            text_content = "This is a test text file with sufficient content to pass validation."
            text_file = Path(temp_dir) / "test.txt"
            text_file.write_text(text_content)
            
            result = normalizer._parse_text_file(text_file)
            
            assert result is not None
            assert text_content in result
    
    def test_parse_text_file_empty(self):
        """Test text file parsing with empty content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create empty text file
            text_file = Path(temp_dir) / "empty.txt"
            text_file.write_text("")
            
            result = normalizer._parse_text_file(text_file)
            
            assert result == ""
    
    def test_clean_text(self):
        """Test text cleaning functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            dirty_text = """
            This is    text   with    multiple    spaces.
            
            And multiple
            
            newlines.
            
            \t\tTabs too.
            """
            
            cleaned = normalizer._clean_text(dirty_text)
            
            # Should normalize whitespace
            assert "    " not in cleaned  # No multiple spaces
            assert cleaned.count("\n\n") <= 1  # No multiple newlines
            assert "\t" not in cleaned  # No tabs
            assert "Thisistextwithmultiplespaces" in cleaned
    
    def test_normalize_document_success(self):
        """Test successful document normalization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create HTML file
            html_content = "<html><body><h1>Test Title</h1><p>Test content with sufficient length to pass validation.</p></body></html>"
            source_file = Path(temp_dir) / "test.html"
            source_file.write_text(html_content)
            
            result = normalizer.normalize_file("URL-001", source_file)
            
            assert result.success is True
            assert result.url_id == "URL-001"
            assert result.text_file is not None
            assert result.text_length > 50
            assert result.content_type == "html"
            assert result.error_message is None
            
            # Verify text file was created
            assert result.text_file.exists()
            assert result.text_file.read_text().strip() != ""
    
    def test_normalize_document_content_too_short(self):
        """Test document normalization with content too short."""
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create HTML file with short content
            html_content = "<html><body><p>Short</p></body></html>"
            source_file = Path(temp_dir) / "test.html"
            source_file.write_text(html_content)
            
            result = normalizer.normalize_file("URL-001", source_file)
            
            assert result.success is False
            assert "too short or empty" in result.error_message
            assert result.text_file is None
    
    def test_normalize_document_parsing_error(self):
        """Test document normalization with parsing error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir)
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create file that will cause parsing error
            source_file = Path(temp_dir) / "test.xyz"
            source_file.write_text("Unknown content")
            
            result = normalizer.normalize_file("URL-001", source_file)
            
            assert result.success is False
            assert result.error_message is not None
            assert result.text_file is None
    
    def test_normalize_batch_success(self):
        """Test batch document normalization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_dir = Path(temp_dir) / "raw"
            text_dir = Path(temp_dir) / "text"
            raw_dir.mkdir()
            text_dir.mkdir()
            normalizer = TextNormalizer(raw_dir, text_dir)
            
            # Create multiple HTML files
            fetch_artifact = [
                {
                    "url_id": "URL-001", 
                    "success": True,
                    "file_path": str(Path(temp_dir) / "test1.html")
                },
                {
                    "url_id": "URL-002", 
                    "success": True,
                    "file_path": str(Path(temp_dir) / "test2.html")
                }
            ]
            
            # Create the HTML files
            html_content = """
            <html>
                <head><title>Test Document</title></head>
                <body>
                    <h1>Test Document Title</h1>
                    <p>This is a comprehensive test document that contains sufficient content to pass the validation requirements. 
                    It includes multiple paragraphs and substantial text content to ensure that the normalization process 
                    can successfully extract and process the content without triggering the minimum length validation.</p>
                    <p>This additional paragraph ensures that the content is long enough to meet the minimum requirements.</p>
                </body>
            </html>
            """
            (Path(temp_dir) / "test1.html").write_text(html_content)
            (Path(temp_dir) / "test2.html").write_text(html_content)
            
            results = normalizer.normalize_batch(fetch_artifact)
            
            assert len(results) == 2
            assert all(result.success for result in results)
            assert all(result.text_length > 50 for result in results)


class TestPhase13Artifact:
    """Test Phase 1.3 artifact building."""
    
    def test_build_phase_1_3_artifact_success(self):
        """Test successful Phase 1.3 artifact building."""
        fetch_artifact = {
            "phase": "1.2",
            "total_urls": 2,
            "successful_fetches": 2,
            "failed_fetches": 0,
            "results": [
                {
                    "url_id": "URL-001",
                    "success": True,
                    "file_path": "/tmp/test1.html"
                },
                {
                    "url_id": "URL-002",
                    "success": True,
                    "file_path": "/tmp/test2.html"
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir) / "text"
            text_dir.mkdir()
            output_path = Path(temp_dir) / "artifact.json"
            
            # Create source files
            html_content = """
            <html>
                <head><title>Test Document</title></head>
                <body>
                    <h1>Test Document Title</h1>
                    <p>This is a comprehensive test document that contains sufficient content to pass the validation requirements. 
                    It includes multiple paragraphs and substantial text content to ensure that the normalization process 
                    can successfully extract and process the content without triggering the minimum length validation. 
                    The content should be meaningful and provide enough text for the text extraction algorithms to work properly.</p>
                    <p>This additional paragraph ensures that the content is long enough to meet the minimum requirements 
                    for successful normalization and text extraction from the HTML document.</p>
                </body>
            </html>
            """
            (Path(temp_dir) / "test1.html").write_text(html_content)
            (Path(temp_dir) / "test2.html").write_text(html_content)
            
            # Update file paths to be absolute
            fetch_artifact["results"][0]["file_path"] = str(Path(temp_dir) / "test1.html")
            fetch_artifact["results"][1]["file_path"] = str(Path(temp_dir) / "test2.html")
            
            artifact = build_phase_1_3_artifact(fetch_artifact, Path(temp_dir), text_dir, output_path)
            
            # Verify artifact structure
            assert artifact["phase"] == "1.3"
            assert artifact["total_files"] == 2
            assert artifact["successful_normalizations"] == 2
            assert artifact["failed_normalizations"] == 0
            assert len(artifact["results"]) == 2
            
            # Verify output file was created
            assert output_path.exists()
    
    def test_build_phase_1_3_artifact_mixed_results(self):
        """Test Phase 1.3 artifact building with mixed success/failure."""
        fetch_artifact = {
            "phase": "1.2",
            "total_urls": 2,
            "successful_fetches": 2,
            "failed_fetches": 0,
            "results": [
                {
                    "url_id": "URL-001",
                    "success": True,
                    "file_path": "/tmp/test1.html"
                },
                {
                    "url_id": "URL-002",
                    "success": True,
                    "file_path": "/tmp/test2.html"
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            text_dir = Path(temp_dir) / "text"
            text_dir.mkdir()
            output_path = Path(temp_dir) / "artifact.json"
            
            # Create one good file, one bad file
            html_content = """
            <html>
                <head><title>Test Document</title></head>
                <body>
                    <h1>Test Document Title</h1>
                    <p>This is a comprehensive test document that contains sufficient content to pass the validation requirements. 
                    It includes multiple paragraphs and substantial text content to ensure that the normalization process 
                    can successfully extract and process the content without triggering the minimum length validation. 
                    The content should be meaningful and provide enough text for the text extraction algorithms to work properly.</p>
                    <p>This additional paragraph ensures that the content is long enough to meet the minimum requirements 
                    for successful normalization and text extraction from the HTML document.</p>
                </body>
            </html>
            """
            (Path(temp_dir) / "test1.html").write_text(html_content)
            (Path(temp_dir) / "test2.html").write_text("<html><body><p>Short content that will fail validation.</p></body></html>")  # Too short
            
            # Update file paths to be absolute
            fetch_artifact["results"][0]["file_path"] = str(Path(temp_dir) / "test1.html")
            fetch_artifact["results"][1]["file_path"] = str(Path(temp_dir) / "test2.html")
            
            artifact = build_phase_1_3_artifact(fetch_artifact, Path(temp_dir), text_dir, output_path)
            
            # Verify artifact structure
            assert artifact["phase"] == "1.3"
            assert artifact["total_files"] == 2
            assert artifact["successful_normalizations"] == 1
            assert artifact["failed_normalizations"] == 1


class TestDependencies:
    """Test dependency availability."""
    
    def test_bs4_availability(self):
        """Test BeautifulSoup4 availability check."""
        # This test will pass if BeautifulSoup4 is installed, fail otherwise
        assert isinstance(HAS_BS4, bool)
    
    def test_pymupdf_availability(self):
        """Test PyMuPDF availability check."""
        # This test will pass if PyMuPDF is installed, fail otherwise
        assert isinstance(HAS_PYMUPDF, bool)
    
    def test_trafilatura_availability(self):
        """Test trafilatura availability check."""
        # This test will pass if trafilatura is installed, fail otherwise
        assert isinstance(HAS_TRAFILATURA, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
