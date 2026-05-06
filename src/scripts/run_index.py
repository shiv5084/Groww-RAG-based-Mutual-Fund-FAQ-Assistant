#!/usr/bin/env python3
"""
Phase 3 Indexing CLI Script

This script handles the complete Phase 3 pipeline:
1. Load chunks from Phase 2
2. Generate embeddings using sentence-transformers
3. Store vectors in ChromaDB
4. Build BM25 index for hybrid retrieval
5. Save embedding metadata

Usage:
    python scripts/run_index.py --chunks data/chunks/chunks.jsonl --output data/index
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever
from phase3_indexing.hybrid import BM25Index
try:
    from whoosh import index
    HAS_WHOOSH = True
except ImportError:
    HAS_WHOOSH = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    try:
        import yaml
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except ImportError:
        logger.warning("PyYAML not found, using default config")
        return {}
    except FileNotFoundError:
        logger.warning(f"Config file {config_path} not found, using defaults")
        return {}


def load_chunks(chunks_path: Path) -> list:
    """Load chunks from JSONL file."""
    chunks = []
    
    if not chunks_path.exists():
        logger.error(f"Chunks file not found: {chunks_path}")
        sys.exit(1)
    
    with open(chunks_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chunk = json.loads(line.strip())
                chunks.append(chunk)
    
    logger.info(f"Loaded {len(chunks)} chunks from {chunks_path}")
    return chunks


def main():
    """Main indexing pipeline."""
    parser = argparse.ArgumentParser(description="Phase 3: Embeddings and vector store indexing")
    parser.add_argument(
        "--chunks", 
        type=Path, 
        default=Path("data/chunks/chunks.jsonl"),
        help="Path to chunks JSONL file from Phase 2"
    )
    parser.add_argument(
        "--output", 
        type=Path, 
        default=Path("data/index"),
        help="Output directory for indexed data"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Configuration directory"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="BAAI/bge-small-en-v1.5",
        help="Embedding model name"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for embeddings (cpu/cuda)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding"
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="mf_faq_chunks",
        help="ChromaDB collection name"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Hybrid search weight for semantic search (0-1)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset existing collections/indexes"
    )
    
    args = parser.parse_args()
    
    # Create output directories
    output_dir = args.output
    index_dir = output_dir / "chroma"
    bm25_dir = output_dir.parent / "bm25"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    bm25_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting Phase 3 indexing pipeline")
    logger.info(f"Input chunks: {args.chunks}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Embedding model: {args.model}")
    logger.info(f"Device: {args.device}")
    
    try:
        # Load configuration
        embedding_config = load_config(args.config_dir / "embedding.yaml")
        vector_config = load_config(args.config_dir / "vector_store.yaml")
        
        # Override with command line arguments
        model_name = args.model or embedding_config.get("model_name", "BAAI/bge-small-en-v1.5")
        device = args.device or embedding_config.get("device", "cpu")
        batch_size = args.batch_size or embedding_config.get("batch_size", 32)
        collection_name = args.collection_name or vector_config.get("collection_name", "mf_faq_chunks")
        
        # Step 1: Load chunks from Phase 2
        logger.info("Step 1: Loading chunks from Phase 2")
        chunks = load_chunks(args.chunks)
        
        if not chunks:
            logger.error("No chunks found. Please run Phase 2 first.")
            sys.exit(1)
        
        # Step 2: Initialize embedding engine
        logger.info("Step 2: Initializing embedding engine")
        embed_engine = EmbeddingEngine(model_name=model_name, device=device)
        
        # Step 3: Generate embeddings
        logger.info("Step 3: Generating embeddings")
        embedded_chunks = embed_engine.embed_chunks(chunks, batch_size=batch_size)
        
        # Step 4: Save embeddings metadata
        logger.info("Step 4: Saving embeddings metadata")
        embeddings_file = output_dir / "embedding.jsonl"
        embed_engine.save_embeddings(embedded_chunks, embeddings_file)
        
        # Step 5: Initialize vector store
        logger.info("Step 5: Initializing vector store")
        vector_store = VectorStore(
            persist_directory=index_dir,
            collection_name=collection_name
        )
        
        # Reset if requested
        if args.reset:
            logger.info("Resetting vector store collection")
            vector_store.reset_collection()
        
        # Step 6: Add embeddings to vector store
        logger.info("Step 6: Adding embeddings to vector store")
        vector_store.add_chunks(embedded_chunks)
        
        # Step 7: Build BM25 index
        logger.info("Step 7: Building BM25 index")
        bm25_index = BM25Index(bm25_dir)
        
        # Reset BM25 if requested
        if args.reset:
            logger.info("Resetting BM25 index")
            bm25_index.index = index.create_in(bm25_dir, bm25_index.index.schema)
        
        bm25_index.add_documents(chunks)
        
        # Step 8: Initialize hybrid retriever
        logger.info("Step 8: Initializing hybrid retriever")
        hybrid_retriever = HybridRetriever(
            embedding_engine=embed_engine,
            vector_store=vector_store,
            bm25_index=bm25_index,
            alpha=args.alpha
        )
        
        # Step 9: Test retrieval
        logger.info("Step 9: Testing hybrid retrieval")
        test_query = "mutual fund exit load"
        test_results = hybrid_retriever.search(test_query, top_k=3)
        
        logger.info(f"Test query: '{test_query}'")
        logger.info(f"Found {len(test_results)} results")
        for i, result in enumerate(test_results, 1):
            logger.info(f"  {i}. Score: {result['hybrid_score']:.3f}, Chunk: {result['chunk_id']}")
        
        # Step 10: Generate statistics
        logger.info("Step 10: Generating indexing statistics")
        stats = hybrid_retriever.get_stats()
        
        stats_file = output_dir / "index_stats.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info("Indexing statistics:")
        logger.info(f"  Vector store documents: {stats['vector_store_count']}")
        logger.info(f"  BM25 documents: {stats['bm25_count']}")
        logger.info(f"  Hybrid alpha: {stats['alpha']}")
        
        logger.info("Phase 3 indexing completed successfully!")
        logger.info(f"Outputs:")
        logger.info(f"  - Embeddings: {embeddings_file}")
        logger.info(f"  - Vector store: {index_dir}")
        logger.info(f"  - BM25 index: {bm25_dir}")
        logger.info(f"  - Statistics: {stats_file}")
        
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
