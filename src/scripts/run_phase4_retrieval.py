#!/usr/bin/env python3
"""
Phase 4 CLI script - Query routing and RAG retrieval.

Comprehensive CLI covering all Phase 4 functionality:
- Intent routing (advisory/performance/factual classification)
- Hybrid retrieval with chunk selection
- Context packing for LLM generation
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase4_retrieval import IntentRouter, RetrievalEngine, ContextPacker
from phase4_retrieval.types import RouteLabel, ContextBundle
from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever
import yaml


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}


def initialize_phase3_components(config: dict) -> tuple:
    """Initialize Phase 3 components."""
    logger.info("Initializing Phase 3 components...")
    
    # Embedding engine
    embedding_config = config.get('phase3_integration', {})
    embedding_engine = EmbeddingEngine(
        model_name=embedding_config.get('embedding_model', 'BAAI/bge-small-en-v1.5'),
        device=embedding_config.get('embedding_device', 'cpu')
    )
    logger.info("Embedding engine initialized")
    
    # Vector store
    vector_store_config = embedding_config.get('vector_store', {})
    vector_store = VectorStore(
        persist_directory=Path(vector_store_config.get('vector_store_path', 'data/index/chroma')),
        collection_name=vector_store_config.get('vector_store_collection', 'mf_faq_chunks')
    )
    logger.info("Vector store initialized")
    
    # Hybrid retriever
    hybrid_config = embedding_config.get('hybrid_retrieval', {})
    bm25_index_path = Path(embedding_config.get('bm25_index_path', 'data/bm25'))
    
    # Create BM25 index if it doesn't exist
    from phase3_indexing.hybrid import BM25Index
    bm25_index = BM25Index(bm25_index_path)
    
    hybrid_retriever = HybridRetriever(
        embedding_engine=embedding_engine,
        vector_store=vector_store,
        bm25_index=bm25_index,
        alpha=hybrid_config.get('hybrid_alpha', 0.5)
    )
    logger.info("Hybrid retriever initialized")
    
    return embedding_engine, vector_store, hybrid_retriever


def initialize_phase4_components(config: dict, phase3_components: tuple) -> tuple:
    """Initialize Phase 4 components."""
    logger.info("Initializing Phase 4 components...")
    
    embedding_engine, vector_store, hybrid_retriever = phase3_components
    
    # Intent router
    router_config = config.get('router', {})
    router = IntentRouter(router_config)
    logger.info("Intent router initialized")
    
    # Retrieval engine
    retrieval_config = config.get('retrieval', {})
    retrieval_engine = RetrievalEngine(
        embedding_engine=embedding_engine,
        vector_store=vector_store,
        hybrid_retriever=hybrid_retriever,
        config=retrieval_config
    )
    logger.info("Retrieval engine initialized")
    
    # Context packer
    context_config = config.get('context_packer', {})
    # Include system prompts from main retrieval config
    if 'system_prompts' in config:
        context_config['system_prompts'] = config['system_prompts']
    context_packer = ContextPacker(context_config)
    logger.info("Context packer initialized")
    
    return router, retrieval_engine, context_packer


def process_query(query: str, router: IntentRouter, retrieval_engine: RetrievalEngine, 
                  context_packer: ContextPacker) -> ContextBundle:
    """Process a single query through the complete Phase 4 pipeline."""
    logger.info(f"Processing query: {query}")
    
    # Step 1: Intent routing
    logger.info("Step 1: Intent routing...")
    route_label = router.classify(query)
    logger.info(f"Route: {route_label.value}")
    
    # Step 2: Retrieval
    logger.info("Step 2: Retrieval...")
    retrieval_results = retrieval_engine.retrieve(query, route_label)
    logger.info(f"Retrieved {len(retrieval_results)} chunks")
    
    # Step 3: Context packing
    logger.info("Step 3: Context packing...")
    if route_label == RouteLabel.ADVISORY and not retrieval_results:
        # Use refusal response
        context_bundle = context_packer.build_refusal_response(query)
    elif route_label == RouteLabel.PERFORMANCE and retrieval_results:
        # Use performance response
        factsheet_url = retrieval_results[0].source_url
        context_bundle = context_packer.build_performance_response(query, factsheet_url)
    else:
        # Use standard context building
        context_bundle = context_packer.build_context(query, route_label, retrieval_results)
    
    logger.info("Context bundle built")
    return context_bundle


def interactive_mode(router: IntentRouter, retrieval_engine: RetrievalEngine, 
                    context_packer: ContextPacker):
    """Run interactive query processing."""
    print("\nPhase 4 Interactive Query Processing")
    print("Type 'quit' or 'exit' to stop")
    print("Type 'stats' to see retrieval statistics")
    print("Type 'help' for commands")
    print("-" * 50)
    
    while True:
        try:
            query = input("\nEnter your query: ").strip()
            
            if query.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break
            
            if query.lower() == 'help':
                print("\nAvailable commands:")
                print("  quit/exit - Exit the program")
                print("  stats - Show retrieval statistics")
                print("  help - Show this help message")
                print("  Any other text - Process as query")
                continue
            
            if query.lower() == 'stats':
                stats = retrieval_engine.get_stats()
                print("\nRetrieval Statistics:")
                print(f"  Total queries: {stats['total_queries']}")
                print(f"  Advisory queries: {stats['advisory_queries']}")
                print(f"  Performance queries: {stats['performance_queries']}")
                print(f"  Factual queries: {stats['factual_queries']}")
                print(f"  Avg retrieval time: {stats['avg_retrieval_time']:.3f}s")
                print(f"  Avg chunks retrieved: {stats['avg_chunks_retrieved']:.1f}")
                continue
            
            if not query:
                print("Please enter a query")
                continue
            
            # Process the query
            start_time = time.time()
            context_bundle = process_query(query, router, retrieval_engine, context_packer)
            processing_time = time.time() - start_time
            
            # Display results
            print(f"\nRoute: {context_bundle.route_label.value}")
            print(f"Processing time: {processing_time:.3f}s")
            
            if context_bundle.primary_chunk:
                print(f"Primary chunk: {context_bundle.primary_chunk.chunk_id}")
                print(f"Source: {context_bundle.primary_chunk.source_url}")
                print(f"Score: {context_bundle.primary_chunk.score:.3f}")
            
            if context_bundle.secondary_chunks:
                print(f"Secondary chunks: {len(context_bundle.secondary_chunks)}")
                for i, chunk in enumerate(context_bundle.secondary_chunks, 1):
                    print(f"   {i}. {chunk.chunk_id} (score: {chunk.score:.3f})")
            
            if context_bundle.citation_url:
                print(f"Citation: {context_bundle.citation_url}")
            
            # Show a preview of the context
            print(f"\nContext preview:")
            context_preview = context_bundle.user_context[:200] + "..." if len(context_bundle.user_context) > 200 else context_bundle.user_context
            print(f"   {context_preview}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            print(f"Error: {e}")


def batch_mode(queries: list, router: IntentRouter, retrieval_engine: RetrievalEngine, 
               context_packer: ContextPacker, output_file: Path = None):
    """Process multiple queries in batch mode."""
    logger.info(f"Processing {len(queries)} queries in batch mode")
    
    results = []
    
    for i, query in enumerate(queries, 1):
        logger.info(f"Processing query {i}/{len(queries)}: {query}")
        
        try:
            context_bundle = process_query(query, router, retrieval_engine, context_packer)
            
            # Convert to serializable format
            result = {
                "query": query,
                "route": context_bundle.route_label.value,
                "processing_time": (context_bundle.created_at - context_bundle.created_at).total_seconds(),  # Will be updated
                "primary_chunk": {
                    "chunk_id": context_bundle.primary_chunk.chunk_id,
                    "source_url": context_bundle.primary_chunk.source_url,
                    "score": context_bundle.primary_chunk.score,
                    "doc_type": context_bundle.primary_chunk.doc_type
                } if context_bundle.primary_chunk else None,
                "secondary_chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "source_url": chunk.source_url,
                        "score": chunk.score,
                        "doc_type": chunk.doc_type
                    }
                    for chunk in context_bundle.secondary_chunks
                ],
                "citation_url": context_bundle.citation_url,
                "context_length": len(context_bundle.user_context)
            }
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            results.append({
                "query": query,
                "error": str(e)
            })
    
    # Save results if output file specified
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")
    
    # Print summary
    print(f"\nBatch Processing Summary:")
    print(f"  Total queries: {len(queries)}")
    print(f"  Successful: {len([r for r in results if 'error' not in r])}")
    print(f"  Failed: {len([r for r in results if 'error' in r])}")
    
    if output_file:
        print(f"  Results saved to: {output_file}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Phase 4 - Query routing and RAG retrieval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python run_phase4_retrieval.py
  
  # Single query
  python run_phase4_retrieval.py --query "What is ELSS?"
  
  # Batch processing
  python run_phase4_retrieval.py --batch queries.txt --output results.json
  
  # Test router
  python run_phase4_retrieval.py --test-router
        """
    )
    
    parser.add_argument("--config", type=Path, default="config/retrieval.yaml",
                       help="Configuration file path")
    
    parser.add_argument("--query", type=str,
                       help="Single query to process")
    
    parser.add_argument("--batch", type=Path,
                       help="File containing queries (one per line)")
    
    parser.add_argument("--output", type=Path,
                       help="Output file for batch results")
    
    parser.add_argument("--test-router", action="store_true",
                       help="Test router with sample queries")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        sys.exit(1)
    
    # Initialize components
    try:
        phase3_components = initialize_phase3_components(config)
        router, retrieval_engine, context_packer = initialize_phase4_components(config, phase3_components)
        logger.info("All components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        sys.exit(1)
    
    # Route to appropriate mode
    if args.test_router:
        # Test router with sample queries
        test_queries = [
            "Which mutual fund is best for investment?",
            "What are the returns of HDFC Top 100 Fund?",
            "How do I open a mutual fund account?",
            "Compare ELSS vs PPF performance",
            "What is the exit load for Axis Bluechip Fund?",
            "Should I invest in equity or debt funds?",
            "Explain the KYC process for mutual funds"
        ]
        
        print("\nRouter Testing")
        print("-" * 50)
        
        for query in test_queries:
            details = router.get_classification_details(query)
            print(f"\nQuery: {query}")
            print(f"Route: {details['route_label']}")
            print(f"Confidence: {details['confidence']:.3f}")
            print(f"Scores: {details['all_scores']}")
        
        return
    
    elif args.query:
        # Single query mode
        context_bundle = process_query(args.query, router, retrieval_engine, context_packer)
        
        print(f"\nQuery: {context_bundle.query}")
        print(f"Route: {context_bundle.route_label.value}")
        print(f"Primary chunk: {context_bundle.primary_chunk.chunk_id if context_bundle.primary_chunk else 'None'}")
        print(f"Citation: {context_bundle.citation_url or 'None'}")
        print(f"\nUser Context:")
        print(context_bundle.user_context)
        
    elif args.batch:
        # Batch mode
        if not args.batch.exists():
            logger.error(f"Batch file not found: {args.batch}")
            sys.exit(1)
        
        queries = args.batch.read_text().strip().split('\n')
        queries = [q.strip() for q in queries if q.strip()]
        
        batch_mode(queries, router, retrieval_engine, context_packer, args.output)
        
    else:
        # Interactive mode
        interactive_mode(router, retrieval_engine, context_packer)


if __name__ == "__main__":
    main()
