"""Phase 1.4: Manifest and provenance build.

Make every normalized document auditable.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentManifest:
    """Manifest entry for a single document."""
    doc_id: str
    source_url: str
    doc_type: str
    scheme: Optional[str]
    source_owner: str
    verification_status: str
    fetched_at: Optional[str] = None
    fetch_success: Optional[bool] = None
    fetch_status_code: Optional[int] = None
    fetch_error: Optional[str] = None
    content_hash: Optional[str] = None
    raw_file_path: Optional[str] = None
    normalized: Optional[bool] = None
    normalized_at: Optional[str] = None
    text_file_path: Optional[str] = None
    text_length: Optional[int] = None
    normalization_error: Optional[str] = None
    processing_status: str = "pending"  # pending, fetched, normalized, failed


@dataclass(frozen=True)
class CorpusManifest:
    """Complete corpus manifest with metadata."""
    phase: str
    generated_at: str
    total_documents: int
    successful_fetches: int
    successful_normalizations: int
    failed_documents: int
    documents: list[DocumentManifest]
    source_artifacts: dict[str, str]
    corpus_stats: dict[str, Any]


class ManifestBuilder:
    """Build comprehensive manifest with provenance tracking."""
    
    def __init__(self, output_path: Path):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None
        
        try:
            # Handle ISO format timestamps
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                # Handle Unix timestamps (if any)
                return datetime.fromtimestamp(float(timestamp_str))
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None
    
    def _get_file_hash(self, file_path: Optional[str]) -> Optional[str]:
        """Get content hash from fetch artifact if available."""
        # This would be available from the fetch artifact
        # For now, we'll return None and populate it from fetch results
        return None
    
    def _build_document_manifest(
        self,
        registry_entry: dict[str, Any],
        fetch_result: Optional[dict[str, Any]],
        normalization_result: Optional[dict[str, Any]]
    ) -> DocumentManifest:
        """Build manifest entry for a single document."""
        
        # Base information from registry
        doc_id = registry_entry["id"]
        source_url = registry_entry["url"]
        doc_type = registry_entry["doc_type"]
        scheme = registry_entry.get("scheme")
        source_owner = registry_entry["source_owner"]
        verification_status = registry_entry["verification_status"]
        
        # Fix scheme field for non-scheme documents
        if scheme is None:
            if doc_type == "amc_home":
                scheme = "AMC Home"
            elif doc_type == "factsheet_index":
                scheme = "Factsheet Index"
            elif doc_type == "investor_service_page":
                scheme = "Investor Services"
            elif doc_type == "statutory_disclosure_hub":
                scheme = "Statutory Disclosures"
            elif doc_type == "amc_contact":
                scheme = "Contact Information"
            elif doc_type == "investor_education_amc":
                scheme = "Investor Education"
            elif doc_type == "regulator_home":
                scheme = "Regulator Home"
            elif doc_type == "investor_education":
                scheme = "Investor Education"
            elif doc_type == "mutual_fund_guidance":
                scheme = "Mutual Fund Guidance"
            else:
                scheme = "General"
        
        # Fetch information
        fetch_success = None
        fetch_status_code = None
        fetch_error = None
        content_hash = None
        raw_file_path = None
        fetched_at = None
        
        if fetch_result:
            fetch_success = fetch_result.get("success")
            fetch_status_code = fetch_result.get("status_code")
            fetch_error = fetch_result.get("error_message")
            content_hash = fetch_result.get("content_hash")
            raw_file_path = fetch_result.get("file_path")
            fetch_time = fetch_result.get("fetch_time")
            
            # Convert fetch_time (float seconds) to ISO timestamp
            if fetch_time is not None:
                # Use fetch artifact generation time as base
                fetched_at = datetime.now().isoformat()
            else:
                fetched_at = None
        
        # Normalization information
        normalized = None
        normalized_at = None
        text_file_path = None
        text_length = None
        normalization_error = None
        
        if normalization_result:
            normalized = normalization_result.get("success", False)
            text_file_path = normalization_result.get("text_file")
            text_length = normalization_result.get("text_length")
            normalization_error = normalization_result.get("error_message")
            # Set normalized_at to current timestamp for successful normalization
            if normalized:
                normalized_at = datetime.now().isoformat()
            else:
                normalized_at = None
        
        # Determine processing status
        if fetch_success is False:
            processing_status = "fetch_failed"
        elif normalized is False:
            processing_status = "normalization_failed"
        elif normalized is True:
            processing_status = "completed"
        elif fetch_success is True:
            processing_status = "normalized"
        else:
            processing_status = "pending"
        
        return DocumentManifest(
            doc_id=doc_id,
            source_url=source_url,
            doc_type=doc_type,
            scheme=scheme,
            source_owner=source_owner,
            verification_status=verification_status,
            fetched_at=fetched_at,
            fetch_success=fetch_success,
            fetch_status_code=fetch_status_code,
            fetch_error=fetch_error,
            content_hash=content_hash,
            raw_file_path=raw_file_path,
            normalized=normalized,
            normalized_at=normalized_at,
            text_file_path=text_file_path,
            text_length=text_length,
            normalization_error=normalization_error,
            processing_status=processing_status
        )
    
    def _calculate_corpus_stats(self, documents: list[DocumentManifest]) -> dict[str, Any]:
        """Calculate corpus-wide statistics."""
        total_docs = len(documents)
        successful_fetches = sum(1 for d in documents if d.fetch_success is True)
        successful_normalizations = sum(1 for d in documents if d.normalized is True)
        failed_documents = sum(1 for d in documents 
                            if d.processing_status in ["fetch_failed", "normalization_failed"])
        
        # Content type statistics
        doc_types = {}
        for doc in documents:
            dt = doc.doc_type
            doc_types[dt] = doc_types.get(dt, 0) + 1
        
        # Source owner statistics
        source_owners = {}
        for doc in documents:
            so = doc.source_owner
            source_owners[so] = source_owners.get(so, 0) + 1
        
        # Processing status statistics
        processing_statuses = {}
        for doc in documents:
            ps = doc.processing_status
            processing_statuses[ps] = processing_statuses.get(ps, 0) + 1
        
        # Text length statistics
        text_lengths = [d.text_length for d in documents if d.text_length is not None]
        text_stats = {}
        if text_lengths:
            text_stats = {
                "total_characters": sum(text_lengths),
                "average_characters": sum(text_lengths) // len(text_lengths),
                "min_characters": min(text_lengths),
                "max_characters": max(text_lengths)
            }
        
        return {
            "total_documents": total_docs,
            "successful_fetches": successful_fetches,
            "successful_normalizations": successful_normalizations,
            "failed_documents": failed_documents,
            "fetch_success_rate": (successful_fetches / total_docs * 100) if total_docs > 0 else 0,
            "normalization_success_rate": (successful_normalizations / total_docs * 100) if total_docs > 0 else 0,
            "document_types": doc_types,
            "source_owners": source_owners,
            "processing_statuses": processing_statuses,
            "text_statistics": text_stats
        }
    
    def build_manifest(
        self,
        phase_1_1_artifact: dict[str, Any],
        phase_1_2_artifact: dict[str, Any],
        phase_1_3_artifact: dict[str, Any]
    ) -> CorpusManifest:
        """Build complete corpus manifest from all phase artifacts."""
        
        logger.info("Starting Phase 1.4: Manifest and provenance build")
        
        # Get fetch list from Phase 1.1
        fetch_list = phase_1_1_artifact.get("fetch_list", [])
        
        # Get fetch results from Phase 1.2
        fetch_results = {result["url_id"]: result for result in phase_1_2_artifact.get("results", [])}
        
        # Get normalization results from Phase 1.3
        normalization_results = {result["url_id"]: result for result in phase_1_3_artifact.get("results", [])}
        
        # Build document manifests
        documents = []
        for registry_entry in fetch_list:
            doc_id = registry_entry["id"]
            fetch_result = fetch_results.get(doc_id)
            normalization_result = normalization_results.get(doc_id)
            
            doc_manifest = self._build_document_manifest(
                registry_entry=registry_entry,
                fetch_result=fetch_result,
                normalization_result=normalization_result
            )
            documents.append(doc_manifest)
        
        # Calculate corpus statistics
        corpus_stats = self._calculate_corpus_stats(documents)
        
        # Create corpus manifest
        corpus_manifest = CorpusManifest(
            phase="1.4",
            generated_at=datetime.utcnow().isoformat() + "Z",
            total_documents=len(documents),
            successful_fetches=corpus_stats["successful_fetches"],
            successful_normalizations=corpus_stats["successful_normalizations"],
            failed_documents=corpus_stats["failed_documents"],
            documents=documents,
            source_artifacts={
                "phase_1_1": "data/artifacts/phase_1_1_registry.json",
                "phase_1_2": "data/artifacts/phase_1_2_fetch.json",
                "phase_1_3": "data/artifacts/phase_1_3_normalize.json"
            },
            corpus_stats=corpus_stats
        )
        
        logger.info(f"Phase 1.4 complete: {len(documents)} documents in manifest")
        logger.info(f"  - Successful fetches: {corpus_stats['successful_fetches']}")
        logger.info(f"  - Successful normalizations: {corpus_stats['successful_normalizations']}")
        logger.info(f"  - Failed documents: {corpus_stats['failed_documents']}")
        
        return corpus_manifest
    
    def save_manifest(self, manifest: CorpusManifest) -> None:
        """Save manifest to JSON file."""
        # Convert dataclasses to dictionaries
        manifest_dict = asdict(manifest)
        
        # Save to file
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(manifest_dict, f, indent=2, ensure_ascii=False)
            f.write("\n")
        
        logger.info(f"Manifest saved to: {self.output_path}")


def build_phase_1_4_artifact(
    phase_1_1_path: Path,
    phase_1_2_path: Path,
    phase_1_3_path: Path,
    output_path: Path
) -> dict[str, Any]:
    """Execute Phase 1.4 manifest and provenance build and emit artifact."""
    
    logger.info(f"Starting Phase 1.4: Manifest and provenance build")
    logger.info(f"Input artifacts:")
    logger.info(f"  - Phase 1.1: {phase_1_1_path}")
    logger.info(f"  - Phase 1.2: {phase_1_2_path}")
    logger.info(f"  - Phase 1.3: {phase_1_3_path}")
    logger.info(f"Output manifest: {output_path}")
    
    # Load input artifacts
    try:
        with open(phase_1_1_path, "r") as f:
            phase_1_1_artifact = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load Phase 1.1 artifact: {e}")
        raise
    
    try:
        with open(phase_1_2_path, "r") as f:
            phase_1_2_artifact = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load Phase 1.2 artifact: {e}")
        raise
    
    try:
        with open(phase_1_3_path, "r") as f:
            phase_1_3_artifact = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load Phase 1.3 artifact: {e}")
        raise
    
    # Build manifest
    builder = ManifestBuilder(output_path)
    manifest = builder.build_manifest(
        phase_1_1_artifact=phase_1_1_artifact,
        phase_1_2_artifact=phase_1_2_artifact,
        phase_1_3_artifact=phase_1_3_artifact
    )
    
    # Save manifest
    builder.save_manifest(manifest)
    
    # Create artifact summary
    artifact_summary = {
        "phase": "1.4",
        "generated_at": manifest.generated_at,
        "input_artifacts": {
            "phase_1_1": str(phase_1_1_path),
            "phase_1_2": str(phase_1_2_path),
            "phase_1_3": str(phase_1_3_path)
        },
        "output_manifest": str(output_path),
        "corpus_summary": {
            "total_documents": manifest.total_documents,
            "successful_fetches": manifest.successful_fetches,
            "successful_normalizations": manifest.successful_normalizations,
            "failed_documents": manifest.failed_documents,
            "fetch_success_rate": manifest.corpus_stats["fetch_success_rate"],
            "normalization_success_rate": manifest.corpus_stats["normalization_success_rate"]
        },
        "corpus_stats": manifest.corpus_stats
    }
    
    # Save artifact summary to artifacts directory
    artifact_path = Path("data/artifacts/phase_1_4_manifest.json")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as f:
        json.dump(artifact_summary, f, indent=2, ensure_ascii=False)
        f.write("\n")
    
    logger.info(f"Phase 1.4 artifact saved to: {artifact_path}")
    logger.info(f"Manifest summary:")
    logger.info(f"  - Total documents: {manifest.total_documents}")
    logger.info(f"  - Completed documents: {manifest.successful_normalizations}")
    logger.info(f"  - Failed documents: {manifest.failed_documents}")
    
    return artifact_summary


if __name__ == "__main__":
    # Example usage for testing
    import sys
    from pathlib import Path
    
    if len(sys.argv) != 5:
        print("Usage: python manifest.py <phase_1_1_json> <phase_1_2_json> <phase_1_3_json> <output_path>")
        sys.exit(1)
    
    phase_1_1_path = Path(sys.argv[1])
    phase_1_2_path = Path(sys.argv[2])
    phase_1_3_path = Path(sys.argv[3])
    output_path = Path(sys.argv[4])
    
    # Run manifest build
    artifact = build_phase_1_4_artifact(
        phase_1_1_path=phase_1_1_path,
        phase_1_2_path=phase_1_2_path,
        phase_1_3_path=phase_1_3_path,
        output_path=output_path
    )
    
    print(f"Manifest build complete:")
    print(f"  - Total documents: {artifact['corpus_summary']['total_documents']}")
    print(f"  - Completed: {artifact['corpus_summary']['successful_normalizations']}")
    print(f"  - Failed: {artifact['corpus_summary']['failed_documents']}")
