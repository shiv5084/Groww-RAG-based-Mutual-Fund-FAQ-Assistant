"""Test cases for Phase 1.1 - URL registry validation and scope filtering."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from phase1_ingest.registry import (
    load_registry,
    validate_registry_schema,
    resolve_fetch_list,
    build_phase_1_1_artifact,
    ScopeFilter,
    REQUIRED_URL_FIELDS,
    ALLOWED_VERIFICATION_STATUS
)


class TestScopeFilter:
    """Test ScopeFilter functionality."""
    
    def test_from_registry_with_exclude_doc_types(self):
        """Test ScopeFilter creation with exclude_doc_types."""
        registry = {
            "current_iteration_scope": {
                "exclude_doc_types": ["pdf", "video"]
            }
        }
        
        scope_filter = ScopeFilter.from_registry(registry)
        
        assert scope_filter.exclude_doc_types == {"pdf", "video"}
    
    def test_from_registry_without_scope(self):
        """Test ScopeFilter creation without scope definition."""
        registry = {}
        
        scope_filter = ScopeFilter.from_registry(registry)
        
        assert scope_filter.exclude_doc_types == set()
    
    def test_from_registry_with_empty_exclude_list(self):
        """Test ScopeFilter creation with empty exclude list."""
        registry = {
            "current_iteration_scope": {
                "exclude_doc_types": []
            }
        }
        
        scope_filter = ScopeFilter.from_registry(registry)
        
        assert scope_filter.exclude_doc_types == set()


class TestRegistryValidation:
    """Test registry validation functionality."""
    
    def test_validate_registry_schema_success(self):
        """Test successful schema validation."""
        valid_registry = {
            "urls": [
                {
                    "id": "URL-001",
                    "url": "https://example.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                }
            ]
        }
        
        # Should not raise any exception
        validate_registry_schema(valid_registry)
    
    def test_validate_registry_schema_missing_urls_key(self):
        """Test validation failure when urls key is missing."""
        invalid_registry = {}
        
        with pytest.raises(ValueError, match="Registry missing required key: urls"):
            validate_registry_schema(invalid_registry)
    
    def test_validate_registry_schema_urls_not_list(self):
        """Test validation failure when urls is not a list."""
        invalid_registry = {
            "urls": "not_a_list"
        }
        
        with pytest.raises(ValueError, match="Registry field 'urls' must be a list"):
            validate_registry_schema(invalid_registry)
    
    def test_validate_registry_schema_missing_required_fields(self):
        """Test validation failure when required fields are missing."""
        invalid_registry = {
            "urls": [
                {
                    "id": "URL-001",
                    "url": "https://example.com"
                    # Missing other required fields
                }
            ]
        }
        
        with pytest.raises(ValueError, match="urls\\[1\\] missing fields"):
            validate_registry_schema(invalid_registry)
    
    def test_validate_registry_schema_duplicate_ids(self):
        """Test validation failure when duplicate IDs exist."""
        invalid_registry = {
            "urls": [
                {
                    "id": "URL-001",
                    "url": "https://example.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                },
                {
                    "id": "URL-001",  # Duplicate ID
                    "url": "https://example2.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                }
            ]
        }
        
        with pytest.raises(ValueError, match="Duplicate id detected: URL-001"):
            validate_registry_schema(invalid_registry)
    
    def test_validate_registry_schema_invalid_url(self):
        """Test validation failure when URL doesn't start with http."""
        invalid_registry = {
            "urls": [
                {
                    "id": "URL-001",
                    "url": "invalid-url",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                }
            ]
        }
        
        with pytest.raises(ValueError, match="url must start with http:// or https://"):
            validate_registry_schema(invalid_registry)
    
    def test_validate_registry_schema_invalid_verification_status(self):
        """Test validation failure when verification status is invalid."""
        invalid_registry = {
            "urls": [
                {
                    "id": "URL-001",
                    "url": "https://example.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "invalid_status"
                }
            ]
        }
        
        with pytest.raises(ValueError, match="verification_status must be one of"):
            validate_registry_schema(invalid_registry)


class TestFetchListResolution:
    """Test fetch list resolution functionality."""
    
    def test_resolve_fetch_list_basic(self):
        """Test basic fetch list resolution."""
        registry = {
            "current_iteration_scope": {
                "exclude_doc_types": ["pdf"]
            },
            "urls": [
                {
                    "id": "URL-001",
                    "url": "https://example.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                },
                {
                    "id": "URL-002",
                    "url": "https://example.com/pdf",
                    "doc_type": "pdf",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                }
            ]
        }
        
        fetch_list = resolve_fetch_list(registry)
        
        assert len(fetch_list) == 1
        assert fetch_list[0]["id"] == "URL-001"
        assert fetch_list[0]["doc_type"] == "webpage"
    
    def test_resolve_fetch_list_in_scope_false(self):
        """Test fetch list resolution with in_scope_current_iteration false."""
        registry = {
            "urls": [
                {
                    "id": "URL-001",
                    "url": "https://example.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified",
                    "in_scope_current_iteration": False
                },
                {
                    "id": "URL-002",
                    "url": "https://example2.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                }
            ]
        }
        
        fetch_list = resolve_fetch_list(registry)
        
        assert len(fetch_list) == 1
        assert fetch_list[0]["id"] == "URL-002"
    
    def test_resolve_fetch_list_deterministic_ordering(self):
        """Test that fetch list is deterministically ordered."""
        registry = {
            "urls": [
                {
                    "id": "URL-003",
                    "url": "https://example3.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                },
                {
                    "id": "URL-001",
                    "url": "https://example1.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                },
                {
                    "id": "URL-002",
                    "url": "https://example2.com",
                    "doc_type": "webpage",
                    "scheme": None,
                    "source_owner": "Example",
                    "verification_status": "verified"
                }
            ]
        }
        
        fetch_list = resolve_fetch_list(registry)
        
        # Should be ordered by ID
        assert fetch_list[0]["id"] == "URL-001"
        assert fetch_list[1]["id"] == "URL-002"
        assert fetch_list[2]["id"] == "URL-003"


class TestPhase11Artifact:
    """Test Phase 1.1 artifact building."""
    
    def test_build_phase_1_1_artifact_success(self):
        """Test successful Phase 1.1 artifact building."""
        registry_content = """
urls:
  - id: URL-001
    url: https://example.com
    doc_type: webpage
    scheme: null
    source_owner: Example
    verification_status: verified
  - id: URL-002
    url: https://example2.com
    doc_type: pdf
    scheme: null
    source_owner: Example
    verification_status: verified
current_iteration_scope:
  exclude_doc_types: [pdf]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(registry_content)
            registry_path = Path(f.name)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "artifact.json"
            
            try:
                artifact = build_phase_1_1_artifact(registry_path, output_path)
                
                # Verify artifact structure
                assert artifact["phase"] == "1.1"
                assert artifact["total_registry_urls"] == 2
                assert artifact["in_scope_urls"] == 1
                assert artifact["excluded_doc_types"] == ["pdf"]
                assert len(artifact["fetch_list"]) == 1
                assert artifact["fetch_list"][0]["id"] == "URL-001"
                
                # Verify output file was created
                assert output_path.exists()
                
                # Verify output file content
                with open(output_path, 'r') as f:
                    saved_artifact = json.load(f)
                assert saved_artifact == artifact
                
            finally:
                registry_path.unlink(missing_ok=True)
    
    def test_build_phase_1_1_artifact_missing_yaml(self):
        """Test Phase 1.1 artifact building when PyYAML is missing."""
        registry_path = Path("dummy.yaml")
        output_path = Path("dummy.json")
        
        # Mock the import to raise ImportError
        with patch('phase1_ingest.registry.load_registry', side_effect=ImportError("No module named 'yaml'")):
            with pytest.raises(ImportError, match="No module named 'yaml'"):
                build_phase_1_1_artifact(registry_path, output_path)


class TestConstants:
    """Test constant definitions."""
    
    def test_required_url_fields(self):
        """Test REQUIRED_URL_FIELDS constant."""
        expected_fields = {
            "id",
            "url", 
            "doc_type",
            "scheme",
            "source_owner",
            "verification_status"
        }
        
        assert REQUIRED_URL_FIELDS == expected_fields
    
    def test_allowed_verification_status(self):
        """Test ALLOWED_VERIFICATION_STATUS constant."""
        expected_statuses = {
            "verified",
            "pending_verification",
            "failed_verification"
        }
        
        assert ALLOWED_VERIFICATION_STATUS == expected_statuses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
