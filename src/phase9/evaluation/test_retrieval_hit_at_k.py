"""
Phase 9: Retrieval Hit@K Testing

Tests retrieval accuracy by checking if expected URLs appear
in top-k results from the golden Q&A file.
"""

import json
import logging
from pathlib import Path
import sys

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase4_retrieval import IntentRouter, RetrievalEngine, RouteLabel
from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever
from phase5_generation.generation.generator import AnswerGenerator
from phase4_retrieval.context_packer import ContextPacker

logger = logging.getLogger(__name__)


class RetrievalHitTester:
    """Test retrieval accuracy against golden Q&A file."""
    
    def __init__(self, config_path: str):
        """Initialize tester with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.golden_qa = self._load_golden_qa()
        
        # Initialize components
        self._init_components()
    
    def _load_config(self) -> dict:
        """Load evaluation configuration."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                import yaml
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _load_golden_qa(self) -> list:
        """Load golden Q&A from sample file."""
        try:
            with open("doc/sample_qa.md", 'r', encoding='utf-8') as f:
                content = f.read()
                # Parse the markdown file to extract Q&A
                qa_items = []
                current_item = {}
                
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('**Query:**'):
                        if current_item:
                            qa_items.append(current_item)
                        current_item = {"query": line.replace('**Query:**', '').strip()}
                    elif line.startswith('**Expected Answer:**'):
                        if "query" in current_item:
                            current_item["expected_answer"] = line.replace('**Expected Answer:**', '').strip()
                    elif line.startswith('**Citation:**'):
                        if "expected_answer" in current_item:
                            citation = line.replace('**Citation:**', '').strip()
                            current_item["expected_url"] = citation
                    elif line.startswith('---') and current_item:
                        qa_items.append(current_item)
                        current_item = {}
                
                return qa_items
        except Exception as e:
            logger.error(f"Failed to load golden Q&A: {e}")
            return []
    
    def _init_components(self):
        """Initialize Phase 3, 4, and 5 components."""
        try:
            # Load retrieval configuration
            retrieval_config_path = Path("config/retrieval.yaml")
            if retrieval_config_path.exists():
                with open(retrieval_config_path, 'r', encoding='utf-8') as f:
                    import yaml
                    retrieval_config = yaml.safe_load(f)
            else:
                logger.error("Retrieval config not found")
                return
            
            # Initialize Phase 3 components
            embedding_config = retrieval_config.get('phase3_integration', {})
            self.embedding_engine = EmbeddingEngine(
                model_name=embedding_config.get('embedding_model', 'BAAI/bge-small-en-v1.5'),
                device=embedding_config.get('embedding_device', 'cpu')
            )
            
            vector_store_config = embedding_config.get('vector_store', {})
            self.vector_store = VectorStore(
                persist_directory=Path(vector_store_config.get('vector_store_path', 'data/index/chroma')),
                collection_name=vector_store_config.get('vector_store_collection', 'mf_faq_chunks')
            )
            
            from phase3_indexing.hybrid import BM25Index
            bm25_index_path = Path(embedding_config.get('bm25_index_path', 'data/bm25'))
            bm25_index = BM25Index(bm25_index_path)
            self.bm25_index = HybridRetriever(
                embedding_engine=self.embedding_engine,
                vector_store=self.vector_store,
                bm25_index=bm25_index,
                alpha=0.5
            )
            
            # Initialize Phase 4 components
            router_config = retrieval_config.get('router', {})
            self.intent_router = IntentRouter(router_config)
            
            ret_engine_config = retrieval_config.get('retrieval', {})
            self.retrieval_engine = RetrievalEngine(
                embedding_engine=self.embedding_engine,
                vector_store=self.vector_store,
                hybrid_retriever=self.bm25_index,
                config=ret_engine_config
            )
            
            logger.info("Components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
    
    def test_hit_at_k(self, top_k: int = 5) -> dict:
        """
        Test retrieval accuracy for hit@k metrics.
        
        Args:
            top_k: Number of top results to check
            
        Returns:
            Test results dictionary
        """
        results = {
            "total_queries": len(self.golden_qa),
            "hit_at_1": 0,
            "hit_at_3": 0,
            "hit_at_5": 0,
            "failed_queries": [],
            "detailed_results": []
        }
        
        for item in self.golden_qa:
            if "expected_url" not in item:
                logger.warning(f"Skipping item without expected URL: {item.get('query', 'Unknown')}")
                continue
            
            query = item["query"]
            expected_url = item["expected_url"]
            
            try:
                # Route the query
                route_label = self.intent_router.classify(query)
                
                # Retrieve results
                retrieval_results = self.retrieval_engine.retrieve(query, route_label)
                
                # Check if expected URL appears in top-k results
                hit_at_k = False
                rank = None
                
                for i, result in enumerate(retrieval_results[:top_k]):
                    if result.source_url == expected_url:
                        hit_at_k = True
                        rank = i + 1
                        break
                
                # Determine which hit metric to update
                if hit_at_k:
                    if rank <= 1:
                        results["hit_at_1"] += 1
                    if rank <= 3:
                        results["hit_at_3"] += 1
                    if rank <= 5:
                        results["hit_at_5"] += 1
                
                detailed_result = {
                    "query": query,
                    "expected_url": expected_url,
                    "actual_rank": rank,
                    "hit_at_k": hit_at_k,
                    "retrieved_count": len(retrieval_results)
                }
                
                results["detailed_results"].append(detailed_result)
                logger.info(f"Query: {query} - Expected URL found at rank: {rank}")
                
            except Exception as e:
                logger.error(f"Failed to test query '{query}': {e}")
                results["failed_queries"].append({
                    "query": query,
                    "error": str(e)
                })
        
        return results
    
    def run_tests(self, top_k_values: list = [1, 3, 5]) -> dict:
        """
        Run hit@k tests for multiple top_k values.
        
        Args:
            top_k_values: List of top_k values to test
            
        Returns:
            Complete test results
        """
        logger.info(f"Running hit@k tests for top_k values: {top_k_values}")
        
        all_results = {}
        
        for top_k in top_k_values:
            logger.info(f"Testing with top_k={top_k}")
            result = self.test_hit_at_k(top_k)
            all_results[f"top_k_{top_k}"] = result
        
        return all_results


if __name__ == "__main__":
    # Run tests with default top_k values
    tester = RetrievalHitTester("config/evaluation.yaml")
    test_results = tester.run_tests([1, 3, 5])
    
    # Print results
    print("\n=== Retrieval Hit@K Test Results ===")
    for top_k, results in test_results.items():
        print(f"\nTop-K {top_k}:")
        print(f"  Total Queries: {results['total_queries']}")
        print(f"  Hit@1: {results['hit_at_1']}")
        print(f"  Hit@3: {results['hit_at_3']}")
        print(f"  Hit@5: {results['hit_at_5']}")
        print(f"  Success Rate: {results['hit_at_5'] / results['total_queries']:.1%}")
        
        # Save detailed results
        output_path = Path("evaluations/retrieval_hit_at_k_results.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        print(f"\nDetailed results saved to: {output_path}")
