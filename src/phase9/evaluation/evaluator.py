"""
Phase 9: Evaluation Framework

Core evaluation components for testing RAG system performance
against golden questions and expected responses.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class Phase9Evaluator:
    """
    Main evaluator for Phase 9 testing and validation.
    
    Evaluates RAG system performance across multiple dimensions:
    - Retrieval accuracy (hit@k)
    - Response quality (vs golden answers)
    - Refusal compliance
    - Citation correctness
    """
    
    def __init__(self, golden_qa_path: str, config_path: str):
        """
        Initialize evaluator with golden Q&A file and configuration.
        
        Args:
            golden_qa_path: Path to sample Q&A file
            config_path: Path to evaluation configuration
        """
        self.golden_qa_path = Path(golden_qa_path)
        self.config_path = Path(config_path)
        self.golden_qa = self._load_golden_qa()
        self.config = self._load_config()
        self.results = []
    
    def _load_golden_qa(self) -> List[Dict[str, Any]]:
        """Load golden questions and expected answers."""
        try:
            with open(self.golden_qa_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load golden Q&A: {e}")
            return []
    
    def _load_config(self) -> Dict[str, Any]:
        """Load evaluation configuration."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def evaluate_retrieval_accuracy(self, retrieval_results: List[Dict], expected_url: str) -> Dict[str, Any]:
        """
        Evaluate retrieval accuracy by checking if expected URL appears in top-k results.
        
        Args:
            retrieval_results: List of retrieval results
            expected_url: Expected citation URL
            
        Returns:
            Evaluation metrics dictionary
        """
        if not retrieval_results:
            return {"hit_at_k": False, "rank": None}
        
        # Check if expected URL appears in top-k results
        for i, result in enumerate(retrieval_results[:5]):  # Check top-5
            if result.get('source_url') == expected_url:
                return {
                    "hit_at_k": True,
                    "rank": i + 1,  # 1-based ranking
                    "total_retrieved": len(retrieval_results)
                }
        
        return {
            "hit_at_k": False,
            "rank": None,
            "total_retrieved": len(retrieval_results)
        }
    
    def evaluate_response_quality(self, query: str, actual_response: str, expected_response: str) -> Dict[str, Any]:
        """
        Evaluate response quality against expected golden answer.
        
        Args:
            query: Original query
            actual_response: Generated response
            expected_response: Expected golden answer
            
        Returns:
            Quality metrics dictionary
        """
        # Simple text similarity (can be enhanced with semantic similarity)
        actual_words = set(actual_response.lower().split())
        expected_words = set(expected_response.lower().split())
        
        common_words = actual_words.intersection(expected_words)
        total_expected_words = len(expected_words)
        
        if total_expected_words == 0:
            word_overlap = 0.0
        else:
            word_overlap = len(common_words) / total_expected_words
        
        return {
            "word_overlap": word_overlap,
            "actual_length": len(actual_response),
            "expected_length": len(expected_response),
            "contains_citation": "citation" in actual_response.lower(),
            "is_refusal": "cannot" in actual_response.lower() or "unable" in actual_response.lower()
        }
    
    def run_evaluation(self, retrieval_engine, context_packer, answer_generator) -> Dict[str, Any]:
        """
        Run complete evaluation pipeline.
        
        Args:
            retrieval_engine: Phase 4 retrieval engine
            context_packer: Phase 4 context packer
            answer_generator: Phase 5 answer generator
            
        Returns:
            Complete evaluation results
        """
        logger.info("Starting Phase 9 evaluation...")
        
        evaluation_results = {
            "total_queries": len(self.golden_qa),
            "successful_evaluations": 0,
            "retrieval_metrics": {
                "hit_at_1": 0,
                "hit_at_3": 0,
                "hit_at_5": 0,
                "total_retrieved": 0
            },
            "response_quality": {
                "avg_word_overlap": 0.0,
                "avg_response_length": 0,
                "refusal_rate": 0.0
            },
            "failed_queries": [],
            "detailed_results": []
        }
        
        for item in self.golden_qa:
            try:
                query = item["query"]
                expected_response = item["expected_answer"]
                expected_url = item.get("citation_url")
                
                # Step 1: Retrieval
                if expected_url:
                    # Route the query
                    route_label = retrieval_engine.intent_router.classify(query)
                    retrieval_results = retrieval_engine.retrieve(query, route_label)
                    
                    # Evaluate retrieval
                    retrieval_eval = self.evaluate_retrieval_accuracy(
                        retrieval_results, expected_url
                    )
                else:
                    retrieval_eval = {"hit_at_k": None, "rank": None}
                
                # Step 2: Context Packing
                if expected_url and retrieval_eval.get("hit_at_k"):
                    context_bundle = context_packer.build_context(
                        query, route_label, retrieval_results
                    )
                else:
                    # Handle refusal or no-citation cases
                    context_bundle = context_packer.build_refusal_response(query)
                
                # Step 3: Answer Generation
                generation_result = answer_generator.generate_answer(context_bundle)
                actual_response = generation_result.get("answer", "")
                
                # Evaluate response quality
                quality_eval = self.evaluate_response_quality(
                    query, actual_response, expected_response
                )
                
                # Combine results
                detailed_result = {
                    "query": query,
                    "expected_answer": expected_response,
                    "actual_answer": actual_response,
                    "expected_url": expected_url,
                    "retrieval_evaluation": retrieval_eval,
                    "quality_evaluation": quality_eval,
                    "generation_result": generation_result
                }
                
                evaluation_results["detailed_results"].append(detailed_result)
                evaluation_results["successful_evaluations"] += 1
                
                # Update metrics
                if retrieval_eval.get("hit_at_k"):
                    if retrieval_eval["rank"] <= 1:
                        evaluation_results["retrieval_metrics"]["hit_at_1"] += 1
                    if retrieval_eval["rank"] <= 3:
                        evaluation_results["retrieval_metrics"]["hit_at_3"] += 1
                    if retrieval_eval["rank"] <= 5:
                        evaluation_results["retrieval_metrics"]["hit_at_5"] += 1
                
                # Update quality metrics
                evaluation_results["response_quality"]["avg_word_overlap"] += quality_eval["word_overlap"]
                evaluation_results["response_quality"]["avg_response_length"] += quality_eval["actual_length"]
                if quality_eval.get("is_refusal"):
                    evaluation_results["response_quality"]["refusal_rate"] += 1
                
                logger.info(f"Evaluated query: {query}")
                
            except Exception as e:
                logger.error(f"Failed to evaluate query '{query}': {e}")
                evaluation_results["failed_queries"].append({
                    "query": query,
                    "error": str(e)
                })
        
        # Calculate averages
        if evaluation_results["successful_evaluations"] > 0:
            total = evaluation_results["successful_evaluations"]
            evaluation_results["response_quality"]["avg_word_overlap"] /= total
            evaluation_results["response_quality"]["avg_response_length"] /= total
            evaluation_results["response_quality"]["refusal_rate"] /= total
        
        logger.info(f"Evaluation completed. Success rate: {evaluation_results['successful_evaluations']}/{evaluation_results['total_queries']}")
        
        return evaluation_results
    
    def save_results(self, output_path: str):
        """Save evaluation results to file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")


if __name__ == "__main__":
    # Example usage
    evaluator = Phase9Evaluator(
        golden_qa_path="doc/sample_qa.md",
        config_path="config/evaluation.yaml"
    )
    
    # This would be called from main evaluation script
    # results = evaluator.run_evaluation(retrieval_engine, context_packer, answer_generator)
    # evaluator.save_results("evaluations/results.json")
