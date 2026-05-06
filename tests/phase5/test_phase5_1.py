#!/usr/bin/env python3
"""
Test Phase 5.1 Generation Pipeline
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute() / 'src'))

from phase5_generation.generation.generator import AnswerGenerator
from phase5_generation.formatting.validator import OutputValidator
from phase5_generation.formatting.render_answer import AnswerRenderer
from phase4_retrieval.types import ContextBundle, RouteLabel, RetrievalResult

def test_phase5_1():
    """Test Phase 5.1 Generation Pipeline with proper ContextBundle objects."""
    
    print("=== Phase 5.1 Generation Pipeline Test ===")
    
    # Initialize components
    generator = AnswerGenerator()
    validator = OutputValidator()
    renderer = AnswerRenderer()
    
    print("Components initialized")
    
    # Test cases with different route labels
    test_cases = [
        {
            "name": "Factual Query",
            "query": "What is HDFC Equity Fund?",
            "route_label": RouteLabel.FACTUAL,
            "primary_chunk": RetrievalResult(
                chunk_id="hdfc_equity_1",
                text="HDFC Equity Fund is a large-cap equity scheme that predominantly invests in large-cap companies. The fund aims to provide long-term capital appreciation by investing in a diversified portfolio of equity and equity-related securities.",
                score=0.92,
                metadata={"scheme": "HDFC Equity Fund", "doc_type": "factsheet"},
                source_url="https://www.hdfcfund.com/factsheet/hdfc-equity-fund",
                doc_type="factsheet"
            ),
            "citation_url": "https://www.hdfcfund.com/factsheet/hdfc-equity-fund"
        },
        {
            "name": "Advisory Query",
            "query": "Which fund is better for investment?",
            "route_label": RouteLabel.ADVISORY,
            "primary_chunk": None,
            "citation_url": "https://www.amfiindia.com/investor-education"
        },
        {
            "name": "Performance Query",
            "query": "What are the returns of HDFC Equity Fund?",
            "route_label": RouteLabel.PERFORMANCE,
            "primary_chunk": RetrievalResult(
                chunk_id="hdfc_equity_2",
                text="HDFC Equity Fund has delivered consistent performance over the years. The fund's NAV and performance details are updated regularly in the factsheet.",
                score=0.88,
                metadata={"scheme": "HDFC Equity Fund", "doc_type": "factsheet"},
                source_url="https://www.hdfcfund.com/factsheet/hdfc-equity-fund",
                doc_type="factsheet"
            ),
            "citation_url": "https://www.hdfcfund.com/factsheet/hdfc-equity-fund"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        
        # Create ContextBundle
        context = ContextBundle(
            query=test_case["query"],
            route_label=test_case["route_label"],
            primary_chunk=test_case["primary_chunk"],
            citation_url=test_case["citation_url"]
        )
        
        print(f"Query: {context.query}")
        print(f"Route: {context.route_label}")
        
        # Generate answer
        try:
            generation_result = generator.generate_answer(context)
            print("Generation completed")
            
            # Validate result
            validation_result = validator.validate_complete_flow(generation_result)
            print(f"Validation: {'PASS' if validation_result.get('valid', False) else 'FAIL'}")
            
            # Render answer
            rendered_result = renderer.render_from_json(generation_result, generation_result.get('citation_url'))
            rendered_answer = rendered_result.get('rendered_answer', '')
            print(f"Rendered answer: {rendered_answer[:100]}...")
            
            results.append({
                "test_name": test_case["name"],
                "query": test_case["query"],
                "route": str(test_case["route_label"]),
                "generation_success": True,
                "validation_success": validation_result.get('valid', False),
                "answer": generation_result.get('answer', ''),
                "citation": generation_result.get('citation_url', ''),
                "rendered_answer": rendered_answer
            })
            
        except Exception as e:
            print(f"Error: {e}")
            results.append({
                "test_name": test_case["name"],
                "query": test_case["query"],
                "route": str(test_case["route_label"]),
                "generation_success": False,
                "validation_success": False,
                "error": str(e)
            })
    
    # Summary
    print(f"\n=== Test Summary ===")
    total_tests = len(results)
    successful_generations = sum(1 for r in results if r.get('generation_success', False))
    successful_validations = sum(1 for r in results if r.get('validation_success', False))
    
    print(f"Total tests: {total_tests}")
    print(f"Successful generations: {successful_generations}/{total_tests}")
    print(f"Successful validations: {successful_validations}/{total_tests}")
    
    if successful_generations == total_tests and successful_validations == total_tests:
        print("Phase 5.1 Generation Pipeline: PASSED")
    else:
        print("Phase 5.1 Generation Pipeline: FAILED")
    
    return results

if __name__ == "__main__":
    test_phase5_1()
