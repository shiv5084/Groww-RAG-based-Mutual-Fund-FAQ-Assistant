"""Integration tests for the complete Phase 1 pipeline."""

import pytest
import tempfile
import json
import yaml
import logging
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import requests
from requests.exceptions import RequestException

from phase1_ingest.registry import build_phase_1_1_artifact
from phase1_ingest.fetch import build_phase_1_2_artifact
from phase1_ingest.normalize import build_phase_1_3_artifact
from phase1_ingest.manifest import build_phase_1_4_artifact
# quality_gate module removed - Phase 1.5 functionality disabled


class TestPhase1Integration:
    """Integration tests for the complete Phase 1 pipeline."""
    
    def test_full_phase1_pipeline_success(self):
        """Test complete Phase 1 pipeline with successful execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup directory structure
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            data_dir = base_dir / "data"
            raw_dir = data_dir / "raw"
            processed_dir = data_dir / "processed"
            text_dir = processed_dir / "text"
            artifacts_dir = data_dir / "artifacts"
            
            for dir_path in [config_dir, data_dir, raw_dir, processed_dir, text_dir, artifacts_dir]:
                dir_path.mkdir(parents=True)
            
            # Create test URL registry
            registry_content = {
                "current_iteration_scope": {
                    "exclude_doc_types": ["pdf"]
                },
                "urls": [
                    {
                        "id": "URL-001",
                        "url": "https://example.com/fund1",
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    },
                    {
                        "id": "URL-002",
                        "url": "https://example.com/fund2",
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    }
                ]
            }
            
            registry_path = config_dir / "url_registry.yaml"
            with open(registry_path, 'w') as f:
                yaml.dump(registry_content, f)
            
            # Mock HTTP requests
            with patch('phase1_ingest.fetch.requests.Session.get') as mock_get:
                # Mock successful responses
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.content = b"""
                <html>
                    <head><title>HDFC Mutual Fund</title></head>
                    <body>
                        <main>
                            <h1>HDFC Large Cap Fund</h1>
                            <p>This is a comprehensive mutual fund scheme that invests in large-cap companies 
                            for long-term growth. The fund follows a systematic investment approach with 
                            regular NAV updates and professional fund management.</p>
                            <div>
                                <h2>Key Features</h2>
                                <p>Investment objective: Long-term capital appreciation through large-cap equity investments.</p>
                                <p>Suitable for investors with moderate risk tolerance.</p>
                            </div>
                        </main>
                    </body>
                </html>
                """
                mock_response.headers = {"content-type": "text/html"}
                mock_response.url = "https://example.com/fund1"
                mock_get.return_value = mock_response
                
                # Phase 1.1: Registry validation
                phase_1_1_path = artifacts_dir / "phase_1_1_registry.json"
                phase_1_1_artifact = build_phase_1_1_artifact(registry_path, phase_1_1_path)
                
                assert phase_1_1_artifact["phase"] == "1.1"
                assert phase_1_1_artifact["total_registry_urls"] == 2
                assert phase_1_1_artifact["in_scope_urls"] == 2
                assert len(phase_1_1_artifact["fetch_list"]) == 2
                
                # Phase 1.2: Fetch
                phase_1_2_path = artifacts_dir / "phase_1_2_fetch.json"
                phase_1_2_artifact = build_phase_1_2_artifact(
                    phase_1_1_artifact["fetch_list"], raw_dir, phase_1_2_path
                )
                
                assert phase_1_2_artifact["phase"] == "1.2"
                assert phase_1_2_artifact["total_urls"] == 2
                assert phase_1_2_artifact["successful_fetches"] == 2
                assert phase_1_2_artifact["failed_fetches"] == 0
                assert len(phase_1_2_artifact["results"]) == 2
                
                # Verify raw files were created
                assert (raw_dir / "URL-001").exists()
                assert (raw_dir / "URL-002").exists()
                
                # Phase 1.3: Normalization
                phase_1_3_path = artifacts_dir / "phase_1_3_normalize.json"
                phase_1_3_artifact = build_phase_1_3_artifact(
                    phase_1_2_artifact, text_dir, phase_1_3_path
                )
                
                assert phase_1_3_artifact["phase"] == "1.3"
                assert phase_1_3_artifact["total_files"] == 2
                assert phase_1_3_artifact["successful_normalizations"] == 2
                assert phase_1_3_artifact["failed_normalizations"] == 0
                assert len(phase_1_3_artifact["results"]) == 2
                
                # Verify text files were created
                assert (text_dir / "URL-001.txt").exists()
                assert (text_dir / "URL-002.txt").exists()
                
                # Phase 1.4: Manifest
                manifest_path = processed_dir / "manifest.json"
                phase_1_4_path = artifacts_dir / "phase_1_4_manifest.json"
                phase_1_4_artifact = build_phase_1_4_artifact(
                    phase_1_1_path, phase_1_2_path, phase_1_3_path, manifest_path
                )
                
                assert phase_1_4_artifact["phase"] == "1.4"
                assert phase_1_4_artifact["corpus_summary"]["total_documents"] == 2
                assert phase_1_4_artifact["corpus_summary"]["successful_fetches"] == 2
                assert phase_1_4_artifact["corpus_summary"]["successful_normalizations"] == 2
                assert phase_1_4_artifact["corpus_summary"]["failed_documents"] == 0
                
                # Verify manifest was created
                assert manifest_path.exists()
                
                # Phase 1.5: Quality Gate - DISABLED
                # Quality gate functionality has been removed
                logger.info("Phase 1.5 (Quality Gate) has been disabled")
                
                # Verify all artifacts exist (excluding Phase 1.5)
                expected_artifacts = [
                    "phase_1_1_registry.json",
                    "phase_1_2_fetch.json", 
                    "phase_1_3_normalize.json",
                    "phase_1_4_manifest.json"
                ]
                
                for artifact_name in expected_artifacts:
                    assert (artifacts_dir / artifact_name).exists()
    
    def test_full_phase1_pipeline_with_failures(self):
        """Test Phase 1 pipeline with some failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup directory structure
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            data_dir = base_dir / "data"
            raw_dir = data_dir / "raw"
            processed_dir = data_dir / "processed"
            text_dir = processed_dir / "text"
            artifacts_dir = data_dir / "artifacts"
            
            for dir_path in [config_dir, data_dir, raw_dir, processed_dir, text_dir, artifacts_dir]:
                dir_path.mkdir(parents=True)
            
            # Create test URL registry
            registry_content = {
                "urls": [
                    {
                        "id": "URL-001",
                        "url": "https://example.com/success",
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    },
                    {
                        "id": "URL-002",
                        "url": "https://example.com/fail",
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    }
                ]
            }
            
            registry_path = config_dir / "url_registry.yaml"
            with open(registry_path, 'w') as f:
                yaml.dump(registry_content, f)
            
            # Mock HTTP requests - one success, one failure
            with patch('phase1_ingest.fetch.requests.Session.get') as mock_get:
                def side_effect(*args, **kwargs):
                    if "success" in args[0]:
                        # Successful response
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.content = b"""
                        <html>
                            <body>
                                <main>
                                    <h1>Successful Fund</h1>
                                    <p>This is comprehensive mutual fund content with sufficient length 
                                    and relevant terminology for quality assessment.</p>
                                </main>
                            </body>
                        </html>
                        """
                        mock_response.headers = {"content-type": "text/html"}
                        mock_response.url = "https://example.com/success"
                        return mock_response
                    else:
                        # Failed response
                        raise RequestException("Connection failed")
                
                mock_get.side_effect = side_effect
                
                # Phase 1.1: Registry validation
                phase_1_1_path = artifacts_dir / "phase_1_1_registry.json"
                phase_1_1_artifact = build_phase_1_1_artifact(registry_path, phase_1_1_path)
                
                # Phase 1.2: Fetch (with failures)
                phase_1_2_path = artifacts_dir / "phase_1_2_fetch.json"
                phase_1_2_artifact = build_phase_1_2_artifact(
                    phase_1_1_artifact["fetch_list"], raw_dir, phase_1_2_path
                )
                
                assert phase_1_2_artifact["successful_fetches"] == 1
                assert phase_1_2_artifact["failed_fetches"] == 1
                
                # Phase 1.3: Normalization (only successful fetch)
                phase_1_3_path = artifacts_dir / "phase_1_3_normalize.json"
                phase_1_3_artifact = build_phase_1_3_artifact(
                    phase_1_2_artifact, text_dir, phase_1_3_path
                )
                
                assert phase_1_3_artifact["successful_normalizations"] == 1
                assert phase_1_3_artifact["failed_normalizations"] == 0
                
                # Phase 1.4: Manifest
                manifest_path = processed_dir / "manifest.json"
                phase_1_4_path = artifacts_dir / "phase_1_4_manifest.json"
                phase_1_4_artifact = build_phase_1_4_artifact(
                    phase_1_1_path, phase_1_2_path, phase_1_3_path, manifest_path
                )
                
                assert phase_1_4_artifact["corpus_summary"]["failed_documents"] == 1
                
                # Phase 1.5: Quality Gate - DISABLED
                # Quality gate functionality has been removed
                logger.info("Phase 1.5 (Quality Gate) has been disabled")
                # Pipeline proceeds directly to Phase 2 after Phase 1.4
    
    def test_pipeline_artifact_chain(self):
        """Test that artifacts are properly chained between phases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup minimal structure
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            data_dir = base_dir / "data"
            raw_dir = data_dir / "raw"
            processed_dir = data_dir / "processed"
            text_dir = processed_dir / "text"
            artifacts_dir = data_dir / "artifacts"
            
            for dir_path in [config_dir, data_dir, raw_dir, processed_dir, text_dir, artifacts_dir]:
                dir_path.mkdir(parents=True)
            
            # Create minimal registry
            registry_content = {
                "urls": [
                    {
                        "id": "URL-001",
                        "url": "https://example.com",
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    }
                ]
            }
            
            registry_path = config_dir / "url_registry.yaml"
            with open(registry_path, 'w') as f:
                yaml.dump(registry_content, f)
            
            # Mock successful response
            with patch('phase1_ingest.fetch.requests.Session.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.content = b"<html><body><h1>Test</h1><p>Content</p></body></html>"
                mock_response.headers = {"content-type": "text/html"}
                mock_response.url = "https://example.com"
                mock_get.return_value = mock_response
                
                # Run all phases
                phase_1_1_path = artifacts_dir / "phase_1_1_registry.json"
                phase_1_1_artifact = build_phase_1_1_artifact(registry_path, phase_1_1_path)
                
                phase_1_2_path = artifacts_dir / "phase_1_2_fetch.json"
                phase_1_2_artifact = build_phase_1_2_artifact(
                    phase_1_1_artifact["fetch_list"], raw_dir, phase_1_2_path
                )
                
                phase_1_3_path = artifacts_dir / "phase_1_3_normalize.json"
                phase_1_3_artifact = build_phase_1_3_artifact(
                    phase_1_2_artifact, text_dir, phase_1_3_path
                )
                
                manifest_path = processed_dir / "manifest.json"
                phase_1_4_path = artifacts_dir / "phase_1_4_manifest.json"
                phase_1_4_artifact = build_phase_1_4_artifact(
                    phase_1_1_path, phase_1_2_path, phase_1_3_path, manifest_path
                )
                
                # Phase 1.5: Quality Gate - DISABLED
                # Quality gate functionality has been removed
                logger.info("Phase 1.5 (Quality Gate) has been disabled")
                
                # Verify artifact chain (excluding Phase 1.5)
                assert phase_1_1_artifact["phase"] == "1.1"
                assert phase_1_2_artifact["phase"] == "1.2"
                assert phase_1_3_artifact["phase"] == "1.3"
                assert phase_1_4_artifact["phase"] == "1.4"
                
                # Verify data flow
                assert len(phase_1_1_artifact["fetch_list"]) == 1
                assert phase_1_2_artifact["total_urls"] == 1
                assert phase_1_3_artifact["total_files"] == 1
                assert phase_1_4_artifact["corpus_summary"]["total_documents"] == 1
                
                # Verify file dependencies (excluding Phase 1.5)
                assert phase_1_1_path.exists()
                assert phase_1_2_path.exists()
                assert phase_1_3_path.exists()
                assert phase_1_4_path.exists()
                assert manifest_path.exists()
    
    def test_pipeline_error_handling(self):
        """Test pipeline error handling and recovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup structure
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            artifacts_dir = base_dir / "data" / "artifacts"
            
            config_dir.mkdir(parents=True)
            artifacts_dir.mkdir(parents=True)
            
            # Create invalid registry
            invalid_registry_content = {
                "urls": [
                    {
                        "id": "URL-001",
                        "url": "invalid-url",  # Invalid URL format
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    }
                ]
            }
            
            registry_path = config_dir / "url_registry.yaml"
            with open(registry_path, 'w') as f:
                yaml.dump(invalid_registry_content, f)
            
            phase_1_1_path = artifacts_dir / "phase_1_1_registry.json"
            
            # Should raise validation error
            with pytest.raises(ValueError, match="url must start with http:// or https://"):
                build_phase_1_1_artifact(registry_path, phase_1_1_path)
    
    def test_pipeline_file_dependencies(self):
        """Test that pipeline properly handles file dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup structure
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            data_dir = base_dir / "data"
            artifacts_dir = data_dir / "artifacts"
            
            config_dir.mkdir(parents=True)
            artifacts_dir.mkdir(parents=True)
            
            # Create registry
            registry_content = {
                "urls": [
                    {
                        "id": "URL-001",
                        "url": "https://example.com",
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    }
                ]
            }
            
            registry_path = config_dir / "url_registry.yaml"
            with open(registry_path, 'w') as f:
                yaml.dump(registry_content, f)
            
            # Phase 1.1 should work
            phase_1_1_path = artifacts_dir / "phase_1_1_registry.json"
            phase_1_1_artifact = build_phase_1_1_artifact(registry_path, phase_1_1_path)
            
            # Phase 1.2 should fail if Phase 1.1 artifact is missing
            missing_phase_1_1_path = artifacts_dir / "missing.json"
            phase_1_2_path = artifacts_dir / "phase_1_2_fetch.json"
            
            with pytest.raises(FileNotFoundError):
                build_phase_1_2_artifact(
                    phase_1_1_artifact["fetch_list"], 
                    Path(temp_dir) / "raw", 
                    phase_1_2_path
                )


class TestPipelinePerformance:
    """Performance and scalability tests for Phase 1 pipeline."""
    
    def test_pipeline_with_multiple_documents(self):
        """Test pipeline performance with multiple documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup structure
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            data_dir = base_dir / "data"
            raw_dir = data_dir / "raw"
            processed_dir = data_dir / "processed"
            text_dir = processed_dir / "text"
            artifacts_dir = data_dir / "artifacts"
            
            for dir_path in [config_dir, data_dir, raw_dir, processed_dir, text_dir, artifacts_dir]:
                dir_path.mkdir(parents=True)
            
            # Create registry with multiple URLs
            registry_content = {
                "urls": [
                    {
                        "id": f"URL-{i:03d}",
                        "url": f"https://example.com/fund{i}",
                        "doc_type": "scheme_page",
                        "scheme": None,
                        "source_owner": "AMC",
                        "verification_status": "verified"
                    }
                    for i in range(1, 6)  # 5 documents
                ]
            }
            
            registry_path = config_dir / "url_registry.yaml"
            with open(registry_path, 'w') as f:
                yaml.dump(registry_content, f)
            
            # Mock HTTP requests
            with patch('phase1_ingest.fetch.requests.Session.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.content = b"""
                <html>
                    <body>
                        <main>
                            <h1>Mutual Fund Scheme</h1>
                            <p>This is comprehensive mutual fund content with sufficient length 
                            and relevant terminology for quality assessment.</p>
                        </main>
                    </body>
                </html>
                """
                mock_response.headers = {"content-type": "text/html"}
                mock_response.url = "https://example.com/fund1"
                mock_get.return_value = mock_response
                
                # Run Phase 1.1
                phase_1_1_path = artifacts_dir / "phase_1_1_registry.json"
                phase_1_1_artifact = build_phase_1_1_artifact(registry_path, phase_1_1_path)
                
                assert phase_1_1_artifact["total_registry_urls"] == 5
                assert phase_1_1_artifact["in_scope_urls"] == 5
                assert len(phase_1_1_artifact["fetch_list"]) == 5
                
                # Run Phase 1.2
                phase_1_2_path = artifacts_dir / "phase_1_2_fetch.json"
                phase_1_2_artifact = build_phase_1_2_artifact(
                    phase_1_1_artifact["fetch_list"], raw_dir, phase_1_2_path
                )
                
                assert phase_1_2_artifact["successful_fetches"] == 5
                assert phase_1_2_artifact["failed_fetches"] == 0
                
                # Verify all raw files were created
                for i in range(1, 6):
                    assert (raw_dir / f"URL-{i:03d}").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
