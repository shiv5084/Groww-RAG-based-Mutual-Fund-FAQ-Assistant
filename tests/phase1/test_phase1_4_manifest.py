"""Test cases for Phase 1.4 - Manifest and provenance building."""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from phase1_ingest.manifest import (
    DocumentManifest,
    CorpusManifest,
    ManifestBuilder,
    build_phase_1_4_artifact
)


class TestDocumentManifest:
    """Test DocumentManifest dataclass."""
    
    def test_document_manifest_creation(self):
        """Test DocumentManifest creation with all fields."""
        manifest = DocumentManifest(
            doc_id="URL-001",
            source_url="https://example.com",
            doc_type="webpage",
            scheme=None,
            source_owner="Example",
            verification_status="verified",
            fetched_at="2023-01-01T00:00:00Z",
            fetch_success=True,
            fetch_status_code=200,
            fetch_error=None,
            content_hash="abc123",
            raw_file_path=Path("raw/URL-001"),
            normalized=True,
            normalized_at="2023-01-01T00:01:00Z",
            text_file_path=Path("text/URL-001.txt"),
            text_length=1000,
            normalization_error=None,
            processing_status="completed"
        )
        
        assert manifest.doc_id == "URL-001"
        assert manifest.source_url == "https://example.com"
        assert manifest.doc_type == "webpage"
        assert manifest.scheme is None
        assert manifest.source_owner == "Example"
        assert manifest.verification_status == "verified"
        assert manifest.fetch_success is True
        assert manifest.fetch_status_code == 200
        assert manifest.fetch_error is None
        assert manifest.content_hash == "abc123"
        assert manifest.normalized is True
        assert manifest.text_length == 1000
        assert manifest.processing_status == "completed"
    
    def test_document_manifest_failure_case(self):
        """Test DocumentManifest creation for failed case."""
        manifest = DocumentManifest(
            doc_id="URL-002",
            source_url="https://example.com/fail",
            doc_type="webpage",
            scheme=None,
            source_owner="Example",
            verification_status="verified",
            fetched_at=None,
            fetch_success=False,
            fetch_status_code=None,
            fetch_error="Connection failed",
            content_hash=None,
            raw_file_path=None,
            normalized=False,
            normalized_at=None,
            text_file_path=None,
            text_length=None,
            normalization_error="No content to normalize",
            processing_status="fetch_failed"
        )
        
        assert manifest.success is False
        assert manifest.fetch_error == "Connection failed"
        assert manifest.processing_status == "fetch_failed"
        assert manifest.normalized is False


class TestCorpusManifest:
    """Test CorpusManifest dataclass."""
    
    def test_corpus_manifest_creation(self):
        """Test CorpusManifest creation."""
        documents = [
            DocumentManifest(
                doc_id="URL-001",
                source_url="https://example.com",
                doc_type="webpage",
                scheme=None,
                source_owner="Example",
                verification_status="verified",
                fetched_at="2023-01-01T00:00:00Z",
                fetch_success=True,
                fetch_status_code=200,
                fetch_error=None,
                content_hash="abc123",
                raw_file_path=Path("raw/URL-001"),
                normalized=True,
                normalized_at="2023-01-01T00:01:00Z",
                text_file_path=Path("text/URL-001.txt"),
                text_length=1000,
                normalization_error=None,
                processing_status="completed"
            )
        ]
        
        corpus_manifest = CorpusManifest(
            phase="1.4",
            generated_at="2023-01-01T00:02:00Z",
            documents=documents
        )
        
        assert corpus_manifest.phase == "1.4"
        assert corpus_manifest.generated_at == "2023-01-01T00:02:00Z"
        assert len(corpus_manifest.documents) == 1
        assert corpus_manifest.total_documents == 1
        assert corpus_manifest.successful_fetches == 1
        assert corpus_manifest.successful_normalizations == 1
        assert corpus_manifest.failed_documents == 0


class TestManifestBuilder:
    """Test ManifestBuilder functionality."""
    
    def test_manifest_builder_initialization(self):
        """Test ManifestBuilder initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            assert builder.output_path == output_path
    
    def test_merge_document_data_success(self):
        """Test successful document data merging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            # Phase 1.1 data
            phase_1_1_data = {"URL-001": {"source_owner": "AMC", "verification_status": "verified"}}
            
            # Phase 1.2 data
            phase_1_2_data = {
                "URL-001": {
                    "success": True,
                    "status_code": 200,
                    "content_hash": "abc123",
                    "file_path": Path(temp_dir) / "URL-001",
                    "fetch_time": 1.5,
                    "error_message": None
                }
            }
            
            # Phase 1.3 data
            phase_1_3_data = {
                "URL-001": {
                    "success": True,
                    "text_file": Path(temp_dir) / "URL-001.txt",
                    "text_length": 1000,
                    "error_message": None
                }
            }
            
            # Create the files
            Path(temp_dir / "URL-001").write_text("raw content")
            Path(temp_dir / "URL-001.txt").write_text("normalized content")
            
            merged = builder._merge_document_data(
                phase_1_1_data, phase_1_2_data, phase_1_3_data
            )
            
            assert "URL-001" in merged
            doc_data = merged["URL-001"]
            assert doc_data["source_owner"] == "AMC"
            assert doc_data["fetch_success"] is True
            assert doc_data["normalized"] is True
            assert doc_data["processing_status"] == "completed"
    
    def test_merge_document_data_fetch_failed(self):
        """Test document data merging when fetch failed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            # Phase 1.1 data
            phase_1_1_data = {"URL-001": {"source_owner": "AMC", "verification_status": "verified"}}
            
            # Phase 1.2 data (failed fetch)
            phase_1_2_data = {
                "URL-001": {
                    "success": False,
                    "status_code": None,
                    "content_hash": None,
                    "file_path": None,
                    "fetch_time": 0.5,
                    "error_message": "Connection failed"
                }
            }
            
            # Phase 1.3 data (should not exist for failed fetch)
            phase_1_3_data = {}
            
            merged = builder._merge_document_data(
                phase_1_1_data, phase_1_2_data, phase_1_3_data
            )
            
            doc_data = merged["URL-001"]
            assert doc_data["fetch_success"] is False
            assert doc_data["processing_status"] == "fetch_failed"
            assert doc_data["normalized"] is False
    
    def test_merge_document_data_normalization_failed(self):
        """Test document data merging when normalization failed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            # Phase 1.1 data
            phase_1_1_data = {"URL-001": {"source_owner": "AMC", "verification_status": "verified"}}
            
            # Phase 1.2 data (successful fetch)
            phase_1_2_data = {
                "URL-001": {
                    "success": True,
                    "status_code": 200,
                    "content_hash": "abc123",
                    "file_path": Path(temp_dir) / "URL-001",
                    "fetch_time": 1.5,
                    "error_message": None
                }
            }
            
            # Phase 1.3 data (failed normalization)
            phase_1_3_data = {
                "URL-001": {
                    "success": False,
                    "text_file": None,
                    "text_length": None,
                    "error_message": "Content too short"
                }
            }
            
            # Create the raw file
            Path(temp_dir / "URL-001").write_text("raw content")
            
            merged = builder._merge_document_data(
                phase_1_1_data, phase_1_2_data, phase_1_3_data
            )
            
            doc_data = merged["URL-001"]
            assert doc_data["fetch_success"] is True
            assert doc_data["normalized"] is False
            assert doc_data["processing_status"] == "normalization_failed"
            assert doc_data["normalization_error"] == "Content too short"
    
    def test_create_document_manifests(self):
        """Test creation of DocumentManifest objects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            merged_data = {
                "URL-001": {
                    "source_url": "https://example.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "AMC",
                    "verification_status": "verified",
                    "fetched_at": "2023-01-01T00:00:00Z",
                    "fetch_success": True,
                    "fetch_status_code": 200,
                    "fetch_error": None,
                    "content_hash": "abc123",
                    "raw_file_path": Path(temp_dir) / "URL-001",
                    "normalized": True,
                    "normalized_at": "2023-01-01T00:01:00Z",
                    "text_file_path": Path(temp_dir) / "URL-001.txt",
                    "text_length": 1000,
                    "normalization_error": None,
                    "processing_status": "completed"
                }
            }
            
            # Create the files
            Path(temp_dir / "URL-001").write_text("raw content")
            Path(temp_dir / "URL-001.txt").write_text("normalized content")
            
            manifests = builder._create_document_manifests(merged_data)
            
            assert len(manifests) == 1
            manifest = manifests[0]
            assert isinstance(manifest, DocumentManifest)
            assert manifest.doc_id == "URL-001"
            assert manifest.source_url == "https://example.com"
            assert manifest.processing_status == "completed"
    
    def test_calculate_corpus_statistics(self):
        """Test corpus statistics calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            documents = [
                DocumentManifest(
                    doc_id="URL-001",
                    source_url="https://example1.com",
                    doc_type="webpage",
                    scheme=None,
                    source_owner="AMC",
                    verification_status="verified",
                    fetched_at="2023-01-01T00:00:00Z",
                    fetch_success=True,
                    fetch_status_code=200,
                    fetch_error=None,
                    content_hash="abc123",
                    raw_file_path=Path(temp_dir) / "URL-001",
                    normalized=True,
                    normalized_at="2023-01-01T00:01:00Z",
                    text_file_path=Path(temp_dir) / "URL-001.txt",
                    text_length=1000,
                    normalization_error=None,
                    processing_status="completed"
                ),
                DocumentManifest(
                    doc_id="URL-002",
                    source_url="https://example2.com",
                    doc_type="pdf",
                    scheme=None,
                    source_owner="SEBI",
                    verification_status="verified",
                    fetched_at="2023-01-01T00:00:00Z",
                    fetch_success=True,
                    fetch_status_code=200,
                    fetch_error=None,
                    content_hash="def456",
                    raw_file_path=Path(temp_dir) / "URL-002.pdf",
                    normalized=False,
                    normalized_at=None,
                    text_file_path=None,
                    text_length=None,
                    normalization_error="PDF parsing failed",
                    processing_status="normalization_failed"
                )
            ]
            
            stats = builder._calculate_corpus_statistics(documents)
            
            assert stats["total_documents"] == 2
            assert stats["successful_fetches"] == 2
            assert stats["successful_normalizations"] == 1
            assert stats["failed_documents"] == 1
            assert stats["fetch_success_rate"] == 1.0
            assert stats["normalization_success_rate"] == 0.5
            
            # Check document types
            assert stats["document_types"]["webpage"] == 1
            assert stats["document_types"]["pdf"] == 1
            
            # Check source owners
            assert stats["source_owners"]["AMC"] == 1
            assert stats["source_owners"]["SEBI"] == 1
            
            # Check processing statuses
            assert stats["processing_statuses"]["completed"] == 1
            assert stats["processing_statuses"]["normalization_failed"] == 1
    
    def test_build_manifest_success(self):
        """Test successful manifest building."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            # Mock phase artifacts
            phase_1_1_artifact = {
                "fetch_list": [
                    {"id": "URL-001", "source_owner": "AMC", "verification_status": "verified"},
                    {"id": "URL-002", "source_owner": "SEBI", "verification_status": "verified"}
                ]
            }
            
            phase_1_2_artifact = {
                "results": [
                    {
                        "url_id": "URL-001",
                        "success": True,
                        "status_code": 200,
                        "content_hash": "abc123",
                        "file_path": Path(temp_dir) / "URL-001",
                        "fetch_time": 1.5,
                        "error_message": None
                    },
                    {
                        "url_id": "URL-002",
                        "success": True,
                        "status_code": 200,
                        "content_hash": "def456",
                        "file_path": Path(temp_dir) / "URL-002.pdf",
                        "fetch_time": 2.0,
                        "error_message": None
                    }
                ]
            }
            
            phase_1_3_artifact = {
                "results": [
                    {
                        "url_id": "URL-001",
                        "success": True,
                        "text_file": Path(temp_dir) / "URL-001.txt",
                        "text_length": 1000,
                        "error_message": None
                    },
                    {
                        "url_id": "URL-002",
                        "success": False,
                        "text_file": None,
                        "text_length": None,
                        "error_message": "PDF parsing failed"
                    }
                ]
            }
            
            # Create the files
            Path(temp_dir / "URL-001").write_text("raw content 1")
            Path(temp_dir / "URL-002.pdf").write_bytes(b"pdf content")
            Path(temp_dir / "URL-001.txt").write_text("normalized content 1")
            
            manifest = builder.build_manifest(
                phase_1_1_artifact, phase_1_2_artifact, phase_1_3_artifact
            )
            
            assert isinstance(manifest, CorpusManifest)
            assert manifest.phase == "1.4"
            assert len(manifest.documents) == 2
            assert manifest.total_documents == 2
            assert manifest.successful_fetches == 2
            assert manifest.successful_normalizations == 1
            assert manifest.failed_documents == 1
    
    def test_save_manifest(self):
        """Test manifest saving to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "manifest.json"
            builder = ManifestBuilder(output_path)
            
            # Create a simple manifest
            documents = [
                DocumentManifest(
                    doc_id="URL-001",
                    source_url="https://example.com",
                    doc_type="webpage",
                    scheme=None,
                    source_owner="AMC",
                    verification_status="verified",
                    fetched_at="2023-01-01T00:00:00Z",
                    fetch_success=True,
                    fetch_status_code=200,
                    fetch_error=None,
                    content_hash="abc123",
                    raw_file_path=Path(temp_dir) / "URL-001",
                    normalized=True,
                    normalized_at="2023-01-01T00:01:00Z",
                    text_file_path=Path(temp_dir) / "URL-001.txt",
                    text_length=1000,
                    normalization_error=None,
                    processing_status="completed"
                )
            ]
            
            manifest = CorpusManifest(
                phase="1.4",
                generated_at="2023-01-01T00:02:00Z",
                documents=documents
            )
            
            builder.save_manifest(manifest)
            
            # Verify file was created
            assert output_path.exists()
            
            # Verify file content
            with open(output_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["phase"] == "1.4"
            assert len(saved_data["documents"]) == 1
            assert saved_data["documents"][0]["doc_id"] == "URL-001"


class TestPhase14Artifact:
    """Test Phase 1.4 artifact building."""
    
    def test_build_phase_1_4_artifact_success(self):
        """Test successful Phase 1.4 artifact building."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create phase artifact files
            phase_1_1_path = Path(temp_dir) / "phase_1_1.json"
            phase_1_2_path = Path(temp_dir) / "phase_1_2.json"
            phase_1_3_path = Path(temp_dir) / "phase_1_3.json"
            output_path = Path(temp_dir) / "manifest.json"
            
            # Phase 1.1 artifact
            phase_1_1_data = {
                "fetch_list": [
                    {"id": "URL-001", "source_owner": "AMC", "verification_status": "verified"}
                ]
            }
            phase_1_1_path.write_text(json.dumps(phase_1_1_data))
            
            # Phase 1.2 artifact
            phase_1_2_data = {
                "results": [
                    {
                        "url_id": "URL-001",
                        "success": True,
                        "status_code": 200,
                        "content_hash": "abc123",
                        "file_path": str(Path(temp_dir) / "URL-001"),
                        "fetch_time": 1.5,
                        "error_message": None
                    }
                ]
            }
            phase_1_2_path.write_text(json.dumps(phase_1_2_data))
            
            # Phase 1.3 artifact
            phase_1_3_data = {
                "results": [
                    {
                        "url_id": "URL-001",
                        "success": True,
                        "text_file": str(Path(temp_dir) / "URL-001.txt"),
                        "text_length": 1000,
                        "error_message": None
                    }
                ]
            }
            phase_1_3_path.write_text(json.dumps(phase_1_3_data))
            
            # Create the files
            Path(temp_dir / "URL-001").write_text("raw content")
            Path(temp_dir / "URL-001.txt").write_text("normalized content")
            
            artifact = build_phase_1_4_artifact(
                phase_1_1_path, phase_1_2_path, phase_1_3_path, output_path
            )
            
            # Verify artifact structure
            assert artifact["phase"] == "1.4"
            assert "generated_at" in artifact
            assert "input_artifacts" in artifact
            assert "output_manifest" in artifact
            assert "corpus_summary" in artifact
            assert "corpus_stats" in artifact
            
            # Verify corpus summary
            summary = artifact["corpus_summary"]
            assert summary["total_documents"] == 1
            assert summary["successful_fetches"] == 1
            assert summary["successful_normalizations"] == 1
            assert summary["failed_documents"] == 0
            
            # Verify output file was created
            assert output_path.exists()
    
    def test_build_phase_1_4_artifact_missing_files(self):
        """Test Phase 1.4 artifact building with missing input files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            phase_1_1_path = Path(temp_dir) / "nonexistent_1_1.json"
            phase_1_2_path = Path(temp_dir) / "nonexistent_1_2.json"
            phase_1_3_path = Path(temp_dir) / "nonexistent_1_3.json"
            output_path = Path(temp_dir) / "manifest.json"
            
            with pytest.raises(FileNotFoundError):
                build_phase_1_4_artifact(
                    phase_1_1_path, phase_1_2_path, phase_1_3_path, output_path
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
