#!/usr/bin/env python3
"""Phase 2 CLI: Chunking, metadata, and indexing preparation.

This script orchestrates the Phase 2 chunking process, taking processed documents
from Phase 1 and creating chunked retrieval units with rich metadata.

Usage:
    python -m src.scripts.run_chunk --manifest data/processed/manifest.json --output data/chunks/chunks.jsonl
    python -m src.scripts.run_chunk --manifest data/processed/manifest.json --strategy section_aware --config config/chunking.yaml
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase2_chunking import (
    ChunkStrategy,
    ChunkingConfig,
    chunk_documents_from_manifest
)
from phase2_chunking.schema import Chunk, ChunkSchema


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_directories(output_path: Path) -> None:
    """Create necessary directories."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Also create chunks directory if not already exists
    chunks_dir = output_path.parent
    chunks_dir.mkdir(parents=True, exist_ok=True)


def validate_manifest(manifest_path: Path) -> bool:
    """Validate manifest file structure and content."""
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check required fields
        required_fields = ['phase', 'documents']
        for field in required_fields:
            if field not in manifest:
                logger.error(f"Manifest missing required field: {field}")
                return False
        
        # Check phase
        if manifest.get('phase') != '1.4':
            logger.error(f"Expected phase 1.4 manifest, got phase {manifest.get('phase')}")
            return False
        
        # Check documents
        documents = manifest.get('documents', [])
        if not documents:
            logger.error("No documents found in manifest")
            return False
        
        # Count completed documents
        completed_docs = sum(1 for doc in documents if doc.get('processing_status') == 'completed')
        if completed_docs == 0:
            logger.error("No completed documents found in manifest")
            return False
        
        logger.info(f"Manifest validation passed: {completed_docs} completed documents")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in manifest: {e}")
        return False
    except Exception as e:
        logger.error(f"Error validating manifest: {e}")
        return False


def validate_chunks(chunks: list[Chunk]) -> Dict[str, Any]:
    """Validate generated chunks and return statistics."""
    if not chunks:
        return {
            "total_chunks": 0,
            "valid_chunks": 0,
            "invalid_chunks": 0,
            "issues": ["No chunks generated"]
        }
    
    valid_chunks = 0
    invalid_chunks = 0
    all_issues = []
    
    for i, chunk in enumerate(chunks):
        issues = ChunkSchema.validate_chunk(chunk)
        if issues:
            invalid_chunks += 1
            all_issues.extend([f"Chunk {i}: {issue}" for issue in issues])
        else:
            valid_chunks += 1
    
    # Calculate statistics
    text_lengths = [len(chunk.text) for chunk in chunks]
    avg_chunk_size = sum(text_lengths) / len(text_lengths) if text_lengths else 0
    
    quality_scores = [
        chunk.metadata.content_quality_score 
        for chunk in chunks 
        if chunk.metadata.content_quality_score is not None
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    doc_types = {}
    for chunk in chunks:
        doc_type = chunk.metadata.doc_type.value
        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
    
    return {
        "total_chunks": len(chunks),
        "valid_chunks": valid_chunks,
        "invalid_chunks": invalid_chunks,
        "validation_issues": all_issues[:10],  # Limit to first 10 issues
        "statistics": {
            "average_chunk_size": avg_chunk_size,
            "min_chunk_size": min(text_lengths) if text_lengths else 0,
            "max_chunk_size": max(text_lengths) if text_lengths else 0,
            "average_quality_score": avg_quality,
            "meaningful_chunks": sum(1 for chunk in chunks if chunk.metadata.has_meaningful_content),
            "document_types": doc_types,
            "languages": list(set(chunk.metadata.language for chunk in chunks if chunk.metadata.language))
        }
    }


def sample_chunks(chunks_path: Path, num_samples: int = 3) -> None:
    """Sample and display a few chunks for verification."""
    try:
        chunks = []
        with open(chunks_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunk = Chunk.from_jsonl(line.strip())
                    chunks.append(chunk)
        
        if not chunks:
            logger.warning("No chunks found to sample")
            return
        
        logger.info(f"Sampling {min(num_samples, len(chunks))} chunks:")
        
        for i, chunk in enumerate(chunks[:num_samples]):
            logger.info(f"\n--- Sample Chunk {i+1} ---")
            logger.info(f"ID: {chunk.metadata.chunk_id}")
            logger.info(f"Source: {chunk.metadata.source_url}")
            logger.info(f"Type: {chunk.metadata.doc_type.value}")
            logger.info(f"Quality: {chunk.metadata.content_quality_score:.2f}")
            logger.info(f"Length: {len(chunk.text)} chars")
            if chunk.metadata.section_title:
                logger.info(f"Section: {chunk.metadata.section_title}")
            
            # Cross-validation
            if chunk.metadata.text_length != len(chunk.text):
                logger.info("text_length in metadata doesn't match actual text length")
            
            # Show first 200 characters of text
            text_preview = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
            logger.info(f"Text: {text_preview}")
        
    except Exception as e:
        logger.error(f"Error sampling chunks: {e}")


def run_phase_2_chunking(
    manifest_path: Path,
    output_path: Path,
    strategy: ChunkStrategy,
    config_path: Optional[Path] = None,
    validate_only: bool = False,
    sample_chunks: bool = False
) -> Dict[str, Any]:
    """Run Phase 2 chunking process."""
    
    logger.info("=" * 60)
    logger.info("Starting Phase 2: Chunking, metadata, and indexing preparation")
    logger.info("=" * 60)
    
    # Validate inputs
    if not manifest_path.exists():
        logger.error(f"Manifest file not found: {manifest_path}")
        sys.exit(1)
    
    if not validate_manifest(manifest_path):
        logger.error("Manifest validation failed")
        sys.exit(1)
    
    # Setup directories
    setup_directories(output_path)
    
    # Load configuration
    if config_path and config_path.exists():
        config = ChunkingConfig.from_yaml(config_path)
        logger.info(f"Loaded configuration from: {config_path}")
    else:
        config = ChunkingConfig()
        logger.info("Using default configuration")
    
    # Log configuration
    logger.info(f"Chunking strategy: {strategy.value}")
    logger.info(f"Window size: {config.window_size}")
    logger.info(f"Overlap size: {config.overlap_size}")
    logger.info(f"Min chunk size: {config.min_chunk_size}")
    
    if validate_only:
        logger.info("Validation mode - not processing chunks")
        return {"status": "validation_only", "manifest_valid": True}
    
    # Run chunking
    logger.info(f"Processing manifest: {manifest_path}")
    logger.info(f"Output file: {output_path}")
    
    try:
        summary = chunk_documents_from_manifest(
            manifest_path=manifest_path,
            text_dir=manifest_path.parent / "text",
            output_path=output_path,
            strategy=strategy,
            config_path=config_path
        )
        
        logger.info("Chunking completed successfully")
        
        # Validate generated chunks
        logger.info("Validating generated chunks...")
        chunks = []
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunk = Chunk.from_jsonl(line.strip())
                    chunks.append(chunk)
        
        validation_results = validate_chunks(chunks)
        
        # Log validation results
        logger.info(f"Chunk validation results:")
        logger.info(f"  Total chunks: {validation_results['total_chunks']}")
        logger.info(f"  Valid chunks: {validation_results['valid_chunks']}")
        logger.info(f"  Invalid chunks: {validation_results['invalid_chunks']}")
        
        if validation_results['validation_issues']:
            logger.warning("Validation issues found:")
            for issue in validation_results['validation_issues']:
                logger.warning(f"  - {issue}")
        
        # Log statistics
        stats = validation_results.get('statistics', {})
        if stats:
            logger.info("Chunk statistics:")
            logger.info(f"  Average chunk size: {stats['average_chunk_size']:.1f} chars")
            logger.info(f"  Size range: {stats['min_chunk_size']} - {stats['max_chunk_size']} chars")
            logger.info(f"  Average quality: {stats['average_quality_score']:.2f}")
            logger.info(f"  Meaningful chunks: {stats['meaningful_chunks']}")
            logger.info(f"  Document types: {list(stats['document_types'].keys())}")
            logger.info(f"  Languages: {stats['languages']}")
        
        # Sample chunks if requested
        if sample_chunks:
            logger.info("\n" + "=" * 40)
            sample_chunks(output_path)
        
        # Combine summary with validation results
        summary.update({
            "validation": validation_results,
            "exit_criteria_met": validation_results['invalid_chunks'] == 0
        })
        
        return summary
        
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Run Phase 2 chunking for GROW-RAG-MutualFundFAQAssistant"
    )
    
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to Phase 1.4 manifest file"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for chunks.jsonl file"
    )
    
    parser.add_argument(
        "--strategy",
        choices=["section_aware", "fixed_window", "hybrid"],
        default="hybrid",
        help="Chunking strategy to use (default: hybrid)"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to chunking configuration file"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate manifest, don't process chunks"
    )
    
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Sample and display a few chunks after processing"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert strategy to enum
    strategy = ChunkStrategy(args.strategy)
    
    try:
        # Run Phase 2 chunking
        result = run_phase_2_chunking(
            manifest_path=args.manifest,
            output_path=args.output,
            strategy=strategy,
            config_path=args.config,
            validate_only=args.validate_only,
            sample_chunks=args.sample
        )
        
        # Log final summary
        logger.info("=" * 60)
        logger.info("Phase 2 Chunking Summary")
        logger.info("=" * 60)
        
        if args.validate_only:
            logger.info("✓ Manifest validation completed successfully")
        else:
            logger.info(f"✓ Processed {result.get('processed_documents', 0)} documents")
            logger.info(f"✓ Generated {result.get('total_chunks', 0)} chunks")
            logger.info(f"✓ Average chunk size: {result.get('average_chunk_size', 0):.1f} chars")
            logger.info(f"✓ Output saved to: {args.output}")
            
            validation = result.get('validation', {})
            if validation.get('invalid_chunks', 0) == 0:
                logger.info("✓ All chunks passed validation")
            else:
                logger.warning(f"⚠ {validation.get('invalid_chunks', 0)} chunks failed validation")
            
            if result.get('exit_criteria_met', False):
                logger.info("✓ Phase 2 exit criteria met")
            else:
                logger.warning("⚠ Phase 2 exit criteria not fully met")
        
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("Chunking interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
