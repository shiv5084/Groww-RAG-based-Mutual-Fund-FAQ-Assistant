#!/usr/bin/env python3
"""
Test Phase 5.2 Answer Rendering
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute() / 'src'))

from phase5_generation.formatting.render_answer import AnswerRenderer

def test_phase5_2():
    """Test Phase 5.2 Answer Rendering functionality."""
    
    print("=== Phase 5.2 Answer Rendering Test ===")
    
    # Initialize renderer
    renderer = AnswerRenderer()
    print("AnswerRenderer initialized")
    
    # Test cases
    test_cases = [
        {
            "name": "Simple JSON Answer",
            "json_input": {
                "answer": "HDFC Equity Fund is a large-cap equity scheme that invests in large-cap companies.",
                "citation_url": "https://www.hdfcfund.com/factsheet"
            },
            "citation_url": "https://www.hdfcfund.com/factsheet"
        },
        {
            "name": "Complex JSON with metadata",
            "json_input": {
                "answer": "This fund has minimum SIP of 500 and offers good returns over long term. The fund follows growth-oriented investment style.",
                "citation_url": "https://www.hdfcfund.com/factsheet/hdfc-equity-fund",
                "confidence": 0.85,
                "source_type": "factsheet"
            },
            "citation_url": "https://www.hdfcfund.com/factsheet/hdfc-equity-fund"
        },
        {
            "name": "String JSON input",
            "json_input": '{"answer": "This is a test answer with multiple sentences. It should be truncated if too long.", "citation_url": null}',
            "citation_url": None
        },
        {
            "name": "Long answer (test truncation)",
            "json_input": {
                "answer": "This is a very long answer that should be truncated. " * 20,  # Repeat 20 times
                "citation_url": "https://www.hdfcfund.com/factsheet"
            },
            "citation_url": "https://www.hdfcfund.com/factsheet"
        },
        {
            "name": "No citation",
            "json_input": {
                "answer": "This is an answer without any citation."
            },
            "citation_url": None
        },
        {
            "name": "Empty answer",
            "json_input": {
                "answer": ""
            },
            "citation_url": "https://www.hdfcfund.com/factsheet"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        
        try:
            # Test rendering
            rendered_result = renderer.render_from_json(
                test_case["json_input"], 
                test_case["citation_url"]
            )
            
            print("Rendering completed")
            
            # Extract key information
            rendered_answer = rendered_result.get('rendered_answer', '')
            is_truncated = rendered_result.get('truncated', False)
            citation = rendered_result.get('citation', '')
            timestamp = rendered_result.get('timestamp', '')
            
            print(f"Answer length: {len(rendered_answer)} characters")
            print(f"Truncated: {is_truncated}")
            print(f"Citation: {citation[:50]}..." if citation else "No citation")
            print(f"Timestamp: {timestamp[:20]}..." if timestamp else "No timestamp")
            print(f"Answer preview: {rendered_answer[:100]}...")
            
            results.append({
                "test_name": test_case["name"],
                "rendering_success": True,
                "answer_length": len(rendered_answer),
                "truncated": is_truncated,
                "has_citation": bool(citation),
                "has_timestamp": bool(timestamp),
                "rendered_answer": rendered_answer
            })
            
        except Exception as e:
            print(f"Error: {e}")
            results.append({
                "test_name": test_case["name"],
                "rendering_success": False,
                "error": str(e)
            })
    
    # Test configuration
    print(f"\n--- Renderer Configuration Test ---")
    config = renderer.get_renderer_config()
    print(f"Include citation: {config.get('include_citation', False)}")
    print(f"Citation format: {config.get('citation_format', '')}")
    print(f"Include timestamp: {config.get('include_timestamp', False)}")
    print(f"Max answer length: {config.get('max_answer_length', 0)}")
    
    # Test custom configuration
    print(f"\n--- Custom Configuration Test ---")
    custom_config = {
        "include_citation": True,
        "citation_format": "Reference: {url}",
        "include_timestamp": False,
        "max_answer_length": 200
    }
    
    custom_renderer = AnswerRenderer(custom_config)
    custom_result = custom_renderer.render_from_json(
        "This is a test answer for custom configuration.",
        "https://example.com"
    )
    
    print(f"Custom citation format: {custom_result.get('citation', '')}")
    print(f"Custom timestamp: {custom_result.get('timestamp', 'No timestamp')}")
    
    # Summary
    print(f"\n=== Test Summary ===")
    total_tests = len(results)
    successful_renders = sum(1 for r in results if r.get('rendering_success', False))
    
    print(f"Total tests: {total_tests}")
    print(f"Successful renders: {successful_renders}/{total_tests}")
    
    # Check specific functionality
    truncation_tested = any(r.get('truncated', False) for r in results)
    citation_tested = any(r.get('has_citation', False) for r in results)
    timestamp_tested = any(r.get('has_timestamp', False) for r in results)
    
    print(f"Truncation tested: {'Yes' if truncation_tested else 'No'}")
    print(f"Citation tested: {'Yes' if citation_tested else 'No'}")
    print(f"Timestamp tested: {'Yes' if timestamp_tested else 'No'}")
    
    if successful_renders == total_tests:
        print("Phase 5.2 Answer Rendering: PASSED")
    else:
        print("Phase 5.2 Answer Rendering: FAILED")
    
    return results

if __name__ == "__main__":
    test_phase5_2()
