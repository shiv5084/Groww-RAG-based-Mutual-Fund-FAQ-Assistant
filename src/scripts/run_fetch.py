#!/usr/bin/env python3
"""
Phase 1.1-1.5 CLI entrypoint for full corpus pull.

This script orchestrates the complete ingestion pipeline:
- Phase 1.1: Registry validation and scope filtering
- Phase 1.2: Fetch engine and raw artifact capture
- Phase 1.3: Parsing and normalization (future)
- Phase 1.4: Manifest and provenance build (future)
- Phase 1.5: Quality gate and handoff (future)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase1_ingest.registry import build_phase_1_1_artifact
from phase1_ingest.fetch import build_phase_1_2_artifact
try:
    from phase1_ingest.normalize import build_phase_1_3_artifact
    from phase1_ingest.manifest import build_phase_1_4_artifact
    # quality_gate module removed - Phase 1.5 functionality disabled
except ImportError as e:
    print(f"Error importing normalize or manifest module: {e}")
    print("Make sure normalize.py and manifest.py exist in src/phase1_ingest/")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_directories(base_dir: Path) -> dict[str, Path]:
    """Create and return directory structure for the ingestion pipeline."""
    dirs = {
        "base": base_dir,
        "data": base_dir / "data",
        "raw": base_dir / "data" / "raw",
        "processed": base_dir / "data" / "processed",
        "text": base_dir / "data" / "processed" / "text",
        "logs": base_dir / "logs",
        "artifacts": base_dir / "data" / "artifacts"
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {dir_path}")
    
    return dirs


def run_phase_1_1(registry_path: Path, output_path: Path) -> dict[str, any]:
    """Run Phase 1.1: Registry validation and scope filtering."""
    logger.info("=" * 60)
    logger.info("Starting Phase 1.1: Registry validation and scope filtering")
    logger.info("=" * 60)
    
    try:
        artifact = build_phase_1_1_artifact(registry_path, output_path)
        
        logger.info(f"Phase 1.1 complete:")
        logger.info(f"  - Total URLs in registry: {artifact['total_registry_urls']}")
        logger.info(f"  - URLs in scope: {artifact['in_scope_urls']}")
        logger.info(f"  - Excluded doc types: {', '.join(artifact['excluded_doc_types'])}")
        logger.info(f"  - Artifact saved to: {output_path}")
        
        return artifact
        
    except Exception as e:
        logger.error(f"Phase 1.1 failed: {e}")
        raise


def run_phase_1_2(fetch_list: list[dict], raw_dir: Path, output_path: Path) -> dict[str, any]:
    """Run Phase 1.2: Fetch engine and raw artifact capture."""
    logger.info("=" * 60)
    logger.info("Starting Phase 1.2: Fetch engine and raw artifact capture")
    logger.info("=" * 60)
    
    try:
        artifact = build_phase_1_2_artifact(fetch_list, raw_dir, output_path)
        
        logger.info(f"Phase 1.2 complete:")
        logger.info(f"  - Total URLs attempted: {artifact['total_urls']}")
        logger.info(f"  - Successful fetches: {artifact['successful_fetches']}")
        logger.info(f"  - Failed fetches: {artifact['failed_fetches']}")
        logger.info(f"  - Total fetch time: {artifact['total_fetch_time']:.2f}s")
        logger.info(f"  - Raw artifacts in: {artifact['raw_dir']}")
        logger.info(f"  - Artifact saved to: {output_path}")
        
        return artifact
        
    except Exception as e:
        logger.error(f"Phase 1.2 failed: {e}")
        raise


def run_phase_1_3(fetch_artifact: dict[str, any], raw_dir: Path, text_dir: Path, output_path: Path) -> dict[str, any]:
    """Run Phase 1.3: Parsing and normalization."""
    logger.info("=" * 60)
    logger.info("Starting Phase 1.3: Parsing and normalization")
    logger.info("=" * 60)
    
    try:
        artifact = build_phase_1_3_artifact(fetch_artifact, raw_dir, text_dir, output_path)
        
        logger.info(f"Phase 1.3 complete:")
        logger.info(f"  - Total files processed: {artifact['total_files']}")
        logger.info(f"  - Successful normalizations: {artifact['successful_normalizations']}")
        logger.info(f"  - Failed normalizations: {artifact['failed_normalizations']}")
        logger.info(f"  - Total characters extracted: {artifact['total_characters_extracted']:,}")
        logger.info(f"  - Text output in: {artifact['text_dir']}")
        logger.info(f"  - Artifact saved to: {output_path}")
        
        # Show content type statistics
        if artifact.get('content_type_stats'):
            logger.info("Content types processed:")
            for ct, count in artifact['content_type_stats'].items():
                logger.info(f"  - {ct}: {count} files")
        
        return artifact
        
    except Exception as e:
        logger.error(f"Phase 1.3 failed: {e}")
        raise


def run_phase_1_4(phase_1_1_path: Path, phase_1_2_path: Path, phase_1_3_path: Path, output_path: Path) -> dict[str, any]:
    """Run Phase 1.4: Manifest and provenance build."""
    logger.info("=" * 60)
    logger.info("Starting Phase 1.4: Manifest and provenance build")
    logger.info("=" * 60)
    
    try:
        artifact = build_phase_1_4_artifact(
            phase_1_1_path=phase_1_1_path,
            phase_1_2_path=phase_1_2_path,
            phase_1_3_path=phase_1_3_path,
            output_path=output_path
        )
        
        logger.info(f"Phase 1.4 complete:")
        logger.info(f"  - Total documents: {artifact['corpus_summary']['total_documents']}")
        logger.info(f"  - Successful fetches: {artifact['corpus_summary']['successful_fetches']}")
        logger.info(f"  - Successful normalizations: {artifact['corpus_summary']['successful_normalizations']}")
        logger.info(f"  - Failed documents: {artifact['corpus_summary']['failed_documents']}")
        logger.info(f"  - Fetch success rate: {artifact['corpus_summary']['fetch_success_rate']:.1f}%")
        logger.info(f"  - Normalization success rate: {artifact['corpus_summary']['normalization_success_rate']:.1f}%")
        logger.info(f"  - Manifest saved to: {artifact['output_manifest']}")
        logger.info(f"  - Artifact saved to: data/artifacts/phase_1_4_manifest.json")
        
        # Show corpus statistics
        corpus_stats = artifact.get('corpus_stats', {})
        if 'document_types' in corpus_stats:
            logger.info("Document types:")
            for dt, count in corpus_stats['document_types'].items():
                logger.info(f"  - {dt}: {count} documents")
        
        if 'processing_statuses' in corpus_stats:
            logger.info("Processing statuses:")
            for status, count in corpus_stats['processing_statuses'].items():
                logger.info(f"  - {status}: {count} documents")
        
        return artifact
        
    except Exception as e:
        logger.error(f"Phase 1.4 failed: {e}")
        raise


def run_phase_1_5(manifest_path: Path, text_dir: Path, artifacts_dir: Path, output_path: Path) -> dict[str, any]:
    """Phase 1.5: Quality gate and handoff to Phase 2 - DISABLED."""
    logger.info("=" * 60)
    logger.info("Phase 1.5: Quality gate and handoff to Phase 2 - DISABLED")
    logger.info("=" * 60)
    logger.info("Quality gate functionality has been removed.")
    logger.info("Phase 1.4 (Manifest) is now the final phase before Phase 2.")
    
    # Return a simple artifact indicating Phase 1.5 is disabled
    artifact = {
        "phase": "1.5",
        "status": "disabled",
        "message": "Quality gate functionality has been removed",
        "ready_for_phase_2": True,  # Assume ready since quality gate is disabled
        "generated_at": "N/A"
    }
    
    return artifact


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Run GROW-RAG-MutualFundFAQAssistant ingestion pipeline"
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("config/url_registry.yaml"),
        help="Path to URL registry YAML file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/artifacts"),
        help="Output directory for artifacts"
    )
    parser.add_argument(
        "--phase",
        choices=["1.1", "1.2", "1.3", "1.4", "all"],
        default="all",
        help="Which phase to run (default: all)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate registry file exists
    if not args.registry.exists():
        logger.error(f"Registry file not found: {args.registry}")
        sys.exit(1)
    
    # Setup directories
    dirs = setup_directories(Path.cwd())
    
    # Define artifact paths
    phase_1_1_path = dirs["artifacts"] / "phase_1_1_registry.json"
    phase_1_2_path = dirs["artifacts"] / "phase_1_2_fetch.json"
    phase_1_3_path = dirs["artifacts"] / "phase_1_3_normalize.json"
    phase_1_4_manifest_path = dirs["processed"] / "manifest.json"
    phase_1_5_quality_gate_path = dirs["artifacts"] / "phase_1_5_quality_gate.json"
    
    try:
        # Phase 1.1: Registry validation and scope filtering
        if args.phase in ["1.1", "all"]:
            phase_1_1_artifact = run_phase_1_1(args.registry, phase_1_1_path)
            fetch_list = phase_1_1_artifact["fetch_list"]
        else:
            # Load existing Phase 1.1 artifact
            if not phase_1_1_path.exists():
                logger.error(f"Phase 1.1 artifact not found: {phase_1_1_path}")
                logger.error("Run with --phase 1.1 first or --phase all")
                sys.exit(1)
            
            with open(phase_1_1_path, "r") as f:
                phase_1_1_artifact = json.load(f)
            fetch_list = phase_1_1_artifact["fetch_list"]
        
        # Phase 1.2: Fetch engine and raw artifact capture
        if args.phase in ["1.2", "all"]:
            phase_1_2_artifact = run_phase_1_2(
                fetch_list=fetch_list,
                raw_dir=dirs["raw"],
                output_path=phase_1_2_path
            )
        
        # Phase 1.3: Parsing and normalization
        if args.phase in ["1.3", "all"]:
            # Load Phase 1.2 artifact if needed
            if args.phase == "1.3":
                if not phase_1_2_path.exists():
                    logger.error(f"Phase 1.2 artifact not found: {phase_1_2_path}")
                    logger.error("Run with --phase 1.2 first or --phase all")
                    sys.exit(1)
                
                with open(phase_1_2_path, "r") as f:
                    phase_1_2_artifact = json.load(f)
            
            if 'phase_1_2_artifact' not in locals():
                logger.error("Phase 1.2 artifact not available")
                sys.exit(1)
            
            phase_1_3_artifact = run_phase_1_3(
                fetch_artifact=phase_1_2_artifact,
                raw_dir=dirs["raw"],
                text_dir=dirs["text"],
                output_path=phase_1_3_path
            )
        
        # Phase 1.4: Manifest and provenance build
        if args.phase in ["1.4", "all"]:
            # Load previous phase artifacts if needed
            if args.phase == "1.4":
                # Load Phase 1.1 artifact
                if not phase_1_1_path.exists():
                    logger.error(f"Phase 1.1 artifact not found: {phase_1_1_path}")
                    logger.error("Run with --phase 1.1 first or --phase all")
                    sys.exit(1)
                
                with open(phase_1_1_path, "r") as f:
                    phase_1_1_artifact = json.load(f)
                
                # Load Phase 1.2 artifact
                if not phase_1_2_path.exists():
                    logger.error(f"Phase 1.2 artifact not found: {phase_1_2_path}")
                    logger.error("Run with --phase 1.2 first or --phase all")
                    sys.exit(1)
                
                with open(phase_1_2_path, "r") as f:
                    phase_1_2_artifact = json.load(f)
                
                # Load Phase 1.3 artifact
                if not phase_1_3_path.exists():
                    logger.error(f"Phase 1.3 artifact not found: {phase_1_3_path}")
                    logger.error("Run with --phase 1.3 first or --phase all")
                    sys.exit(1)
                
                with open(phase_1_3_path, "r") as f:
                    phase_1_3_artifact = json.load(f)
            
            # Verify all required artifacts are available
            if 'phase_1_1_artifact' not in locals():
                logger.error("Phase 1.1 artifact not available")
                sys.exit(1)
            if 'phase_1_2_artifact' not in locals():
                logger.error("Phase 1.2 artifact not available")
                sys.exit(1)
            if 'phase_1_3_artifact' not in locals():
                logger.error("Phase 1.3 artifact not available")
                sys.exit(1)
            
            phase_1_4_artifact = run_phase_1_4(
                phase_1_1_path=phase_1_1_path,
                phase_1_2_path=phase_1_2_path,
                phase_1_3_path=phase_1_3_path,
                output_path=phase_1_4_manifest_path
            )
        
        # Phase 1.5: Quality gate and handoff to Phase 2 - DISABLED
        # Quality gate functionality has been removed
        logger.info("Phase 1.5 (Quality Gate) has been disabled")
        logger.info("Phase 1.4 (Manifest) is now the final phase before Phase 2")
        
        logger.info("=" * 60)
        logger.info("Ingestion pipeline complete!")
        logger.info("=" * 60)
        
        if args.phase == "all":
            logger.info("Phases completed: 1.1, 1.2, 1.3, 1.4")
            logger.info("Phase 1 complete - Ready for Phase 2 (chunking/indexing)")
            logger.info("Note: Phase 1.5 (Quality Gate) has been disabled")
        else:
            logger.info(f"Phase {args.phase} completed successfully")
        
        # Show summary
        if args.phase in ["1.2", "all"] and 'phase_1_2_artifact' in locals():
            success_rate = (phase_1_2_artifact['successful_fetches'] / 
                          phase_1_2_artifact['total_urls'] * 100)
            logger.info(f"Fetch success rate: {success_rate:.1f}%")
            
            if phase_1_2_artifact['failed_fetches'] > 0:
                logger.warning(f"Failed fetches: {phase_1_2_artifact['failed_fetches']}")
                logger.info("Check the artifact file for detailed error information")
        
        if args.phase in ["1.3", "all"] and 'phase_1_3_artifact' in locals():
            success_rate = (phase_1_3_artifact['successful_normalizations'] / 
                          phase_1_3_artifact['total_files'] * 100)
            logger.info(f"Normalization success rate: {success_rate:.1f}%")
            
            if phase_1_3_artifact['failed_normalizations'] > 0:
                logger.warning(f"Failed normalizations: {phase_1_3_artifact['failed_normalizations']}")
                logger.info("Check the artifact file for detailed error information")
        
        if args.phase in ["1.4", "all"] and 'phase_1_4_artifact' in locals():
            corpus_summary = phase_1_4_artifact['corpus_summary']
            logger.info(f"Corpus summary:")
            logger.info(f"  - Total documents: {corpus_summary['total_documents']}")
            logger.info(f"  - Completed documents: {corpus_summary['successful_normalizations']}")
            logger.info(f"  - Failed documents: {corpus_summary['failed_documents']}")
            
            if corpus_summary['failed_documents'] > 0:
                logger.warning(f"Failed documents: {corpus_summary['failed_documents']}")
                logger.info("Check the manifest file for detailed error information")
        
        # Phase 1.5 (Quality Gate) has been disabled
        logger.info("Phase 1.5 (Quality Gate) functionality has been removed")
        logger.info("Proceeding directly to Phase 2 (chunking/indexing) after Phase 1.4")
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
