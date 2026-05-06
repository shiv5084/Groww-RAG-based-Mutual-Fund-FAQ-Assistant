#!/usr/bin/env python3
"""
Phase 5 - Complete RAG Pipeline Script.

Combines Phase 5.1 (Generation) and Phase 5.2 (Formatting) functionality
into a single unified script for the complete RAG pipeline.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    print("Environment variables will not be loaded from .env file")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase5_generation.generation.generator import AnswerGenerator
from phase5_generation.formatting import (
    AnswerGuards, AnswerRenderer, OutputValidator,
    create_default_guards, create_default_renderer, create_default_validator
)
from phase4_retrieval.types import ContextBundle, RouteLabel


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_environment():
    """Validate environment configuration."""
    print("Validating environment configuration...")
    
    # Check Groq configuration
    try:
        from phase5_generation.generation.llm_client import LLMClient
        client = LLMClient()
        groq_valid = client.validate_config()
        print(f"Groq configured: {'OK' if groq_valid else 'MISSING'}")
    except Exception as e:
        print(f"X Error validating Groq: {e}")
        return False
    
    # Check prompt files
    prompts_dir = Path(__file__).parent.parent / "src" / "phase5_generation" / "prompts"
    prompt_files = ["system.md", "user_wrap.md", "refusal.md"]
    
    for prompt_file in prompt_files:
        prompt_path = prompts_dir / prompt_file
        exists = prompt_path.exists()
        print(f"Prompt {prompt_file}: {'OK' if exists else 'MISSING'}")
    
    # Check environment variables
    env_vars = ["GROQ_API_KEY", "LLM_MODEL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS"]
    for var in env_vars:
        value = os.getenv(var)
        print(f"Env var {var}: {'OK' if value else 'MISSING'}")
    
    return True


def test_groq():
    """Test Groq LLM client functionality."""
    print("Testing Groq Client...")
    
    try:
        from phase5_generation.generation.llm_client import LLMClient
        client = LLMClient()
        
        config = client.get_config_info()
        print(f"Provider: {config['provider']}")
        print(f"Model: {config['model']}")
        print(f"Configured: {config['configured']}")
        
        if not config['configured']:
            print("X Groq client not properly configured")
            return False
        
        # Test basic generation
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, I am working correctly!'"}
        ]
        
        response = client.generate(test_messages)
        print(f"Test response: {response}")
        print("OK Groq client test passed")
        return True
    
    except Exception as e:
        print(f"X Groq client test failed: {e}")
        return False


def test_generator():
    """Test answer generator with sample queries."""
    print("Testing Answer Generator...")
    
    try:
        generator = AnswerGenerator()
        
        def create_sample_context_bundle(query: str, route: str) -> ContextBundle:
            """Create sample context bundle for testing."""
            from phase4_retrieval.types import RetrievalResult
            
            if route == "factual":
                chunk = RetrievalResult(
                    chunk_id="test_chunk",
                    text="HDFC Equity Fund is a large-cap equity scheme that invests in large-cap companies.",
                    score=0.95,
                    metadata={"scheme": "HDFC Equity Fund"},
                    source_url="https://www.hdfcfund.com",
                    doc_type="factsheet"
                )
                return ContextBundle(
                    query=query,
                    route_label=RouteLabel.FACTUAL,
                    primary_chunk=chunk,
                    citation_url="https://www.hdfcfund.com"
                )
            else:
                return ContextBundle(query=query, route_label=RouteLabel.ADVISORY if route == "advisory" else RouteLabel.PERFORMANCE)
        
        test_queries = [
            ("What is HDFC Equity Fund?", "factual"),
            ("Which fund is better for investment?", "advisory"),
            ("What are the returns of HDFC Equity Fund?", "performance")
        ]
        
        for query, route in test_queries:
            print(f"\nTesting: {query} (route: {route})")
            
            context_bundle = create_sample_context_bundle(query, route)
            result = generator.generate_answer(context_bundle)
            
            try:
                print(f"Answer: {result['answer']}")
            except UnicodeEncodeError:
                print(f"Answer: [Unicode content - generation successful]")
            print(f"Citation: {result['citation_url']}")
            print(f"Refusal: {result['refusal']}")
            print(f"Generation time: {result['generation_time']:.3f}s")
        
        print("\nOK Answer generator test passed")
        return True
    
    except Exception as e:
        print(f"X Answer generator test failed: {e}")
        return False


def test_guards():
    """Test answer guards functionality."""
    print("Testing Answer Guards...")
    
    try:
        guards = create_default_guards()
        config = guards.get_guard_config()
        
        print(f"Guard configuration:")
        print(f"  Max sentences: {config['max_sentences']}")
        print(f"  Max URLs: {config['max_urls']}")
        print(f"  URL allowlist entries: {len(config['url_allowlist'])}")
        print(f"  Forbidden patterns: {len(config['forbidden_patterns'])}")
        
        # Test with sample text
        test_texts = [
            "This is a simple answer with one sentence.",
            "This is the first sentence. This is the second sentence. This is the third sentence. This is the fourth sentence.",
            "Check https://www.amfiindia.com for more information.",
            "Check https://www.badsite.com for more information.",
            "I recommend investing in this fund as it's the best option."
        ]
        
        for i, text in enumerate(test_texts, 1):
            print(f"\nTest {i}: {text[:50]}...")
            result = guards.apply_all_guards(text)
            print(f"  Valid: {result['is_valid']}")
            if result['errors']:
                print(f"  Errors: {result['errors']}")
            if result['warnings']:
                print(f"  Warnings: {result['warnings']}")
        
        print("\nOK Guards test completed")
        return True
        
    except Exception as e:
        print(f"X Guards test failed: {e}")
        return False


def test_renderer():
    """Test answer renderer functionality."""
    print("Testing Answer Renderer...")
    
    try:
        renderer = create_default_renderer()
        config = renderer.get_renderer_config()
        
        print(f"Renderer configuration:")
        print(f"  Include citation: {config['include_citation']}")
        print(f"  Citation format: {config['citation_format']}")
        print(f"  Include timestamp: {config['include_timestamp']}")
        print(f"  Max answer length: {config['max_answer_length']}")
        
        # Test with sample JSON outputs
        test_cases = [
            {
                "name": "Simple JSON",
                "json_output": {"answer": "HDFC Equity Fund is a large-cap equity scheme."},
                "citation_url": "https://www.hdfcfund.com"
            },
            {
                "name": "Complex JSON",
                "json_output": {
                    "response": {
                        "text": "This fund has minimum SIP of 500 and offers good returns."
                    }
                },
                "citation_url": "https://www.hdfcfund.com/factsheet"
            },
            {
                "name": "String JSON",
                "json_output": '{"answer": "This is a test answer with multiple sentences. It should be truncated if too long."}',
                "citation_url": None
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTest: {test_case['name']}")
            result = renderer.render_from_json(
                test_case["json_output"], 
                test_case["citation_url"]
            )
            
            if result["success"]:
                print(f"  Success: True")
                print(f"  Rendered answer: {result['rendered_answer'][:100]}...")
                print(f"  Truncated: {result['truncated']}")
                print(f"  Citation: {result['citation']}")
            else:
                print(f"  Success: False")
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print("\nOK Renderer test completed")
        return True
        
    except Exception as e:
        print(f"X Renderer test failed: {e}")
        return False


def test_validator():
    """Test output validator functionality."""
    print("Testing Output Validator...")
    
    try:
        validator = create_default_validator()
        config = validator.get_validator_config()
        
        print(f"Validator configuration:")
        print(f"  Strict mode: {config['strict_mode']}")
        print(f"  Validate URLs: {config['validate_urls']}")
        print(f"  Validate sentence count: {config['validate_sentence_count']}")
        
        # Test with sample outputs
        test_cases = [
            {
                "name": "Valid JSON output",
                "json_output": {"answer": "HDFC Equity Fund is a large-cap scheme."},
                "citation_url": "https://www.hdfcfund.com"
            },
            {
                "name": "Invalid JSON",
                "json_output": '{"answer": "This is invalid json"',
                "citation_url": "https://www.hdfcfund.com"
            },
            {
                "name": "Too many sentences",
                "json_output": {"answer": "First. Second. Third. Fourth."},
                "citation_url": "https://www.hdfcfund.com"
            },
            {
                "name": "Forbidden content",
                "json_output": {"answer": "I recommend investing in this fund."},
                "citation_url": "https://www.hdfcfund.com"
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTest: {test_case['name']}")
            result = validator.validate_complete_flow(
                test_case["json_output"],
                test_case["citation_url"]
            )
            
            print(f"  Valid: {result['valid']}")
            if result['errors']:
                print(f"  Errors: {result['errors'][:2]}")
            if result['warnings']:
                print(f"  Warnings: {result['warnings'][:2]}")
            
            # Show summary
            summary = validator.get_validation_summary(result)
            print(f"  Summary: {summary}")
        
        print("\nOK Validator test completed")
        return True
        
    except Exception as e:
        print(f"X Validator test failed: {e}")
        return False


def process_formatting_file(args):
    """Process JSONL file with formatting and validation."""
    print(f"Processing file: {args.input_file}")
    
    try:
        validator = create_default_validator()
        renderer = create_default_renderer()
        
        # Read input file
        with open(args.input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        results = []
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
                citation_url = data.get('citation_url')
                json_output = data.get('json_output', data)
                
                # Validate and render
                validation_result = validator.validate_complete_flow(json_output, citation_url)
                
                if validation_result['valid']:
                    render_result = renderer.render_from_json(json_output, citation_url)
                    final_answer = render_result.get('rendered_answer', '')
                else:
                    final_answer = f"VALIDATION FAILED: {'; '.join(validation_result['errors'][:2])}"
                
                result = {
                    "line_number": i,
                    "original_data": data,
                    "validation": validation_result,
                    "rendered_answer": final_answer,
                    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                results.append(result)
                
                if args.verbose:
                    print(f"Line {i}: Valid={validation_result['valid']}, "
                          f"Errors={len(validation_result['errors'])}, "
                          f"Warnings={len(validation_result['warnings'])}")
                
            except json.JSONDecodeError as e:
                print(f"Line {i}: Invalid JSON - {e}")
                continue
        
        # Save results to data/artifacts directory
        artifacts_dir = "data/artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)
        
        if args.output:
            # If user specified output path, use it as-is
            output_file = args.output
        else:
            # Default to artifacts directory
            output_file = os.path.join(artifacts_dir, f"phase5_formatting_results_{int(time.time())}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"OK Processed {len(results)} entries")
        print(f"Results saved to: {output_file}")
        
        # Show summary
        valid_count = sum(1 for r in results if r['validation']['valid'])
        print(f"Summary: {valid_count}/{len(results)} entries passed validation")
        
        return True
        
    except Exception as e:
        print(f"X File processing failed: {e}")
        return False


def run_batch_generation(args):
    """Run batch generation on context bundles."""
    print(f"Running batch generation on: {args.input_file}")
    
    try:
        generator = AnswerGenerator()
        bundles = load_context_bundles_from_file(args.input_file)
        
        if not bundles:
            print("X No valid context bundles found")
            return
        
        results = generator.batch_generate(bundles)
        
        # Save results to data/artifacts directory
        artifacts_dir = "data/artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)
        
        if args.output:
            # If user specified output path, use it as-is
            output_file = args.output
        else:
            # Default to artifacts directory
            output_file = os.path.join(artifacts_dir, f"phase5_results_{int(time.time())}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"OK Processed {len(bundles)} queries")
        print(f"Results saved to: {output_file}")
        
        # Show summary
        refusal_count = sum(1 for r in results if r['refusal'])
        print(f"Summary: {len(results) - refusal_count} factual answers, {refusal_count} refusals")
    
    except Exception as e:
        print(f"X Batch processing failed: {e}")


def run_complete_pipeline(args):
    """Run complete Phase 5 pipeline: generation + formatting."""
    print(f"Running complete Phase 5 pipeline on: {args.input_file}")
    
    try:
        # Step 1: Generation
        print("\n=== Phase 5.1 - Generation ===")
        generator = AnswerGenerator()
        bundles = load_context_bundles_from_file(args.input_file)
        
        if not bundles:
            print("X No valid context bundles found")
            return
        
        generation_results = generator.batch_generate(bundles)
        
        # Step 2: Formatting and Validation
        print("\n=== Phase 5.2 - Formatting & Validation ===")
        validator = create_default_validator()
        renderer = create_default_renderer()
        
        formatted_results = []
        for i, gen_result in enumerate(generation_results):
            # Get corresponding context bundle for query info
            bundle = bundles[i] if i < len(bundles) else None
            
            # Create JSON output for validation
            json_output = {"answer": gen_result['answer']}
            citation_url = gen_result['citation_url']
            
            # Validate and render
            validation_result = validator.validate_complete_flow(json_output, citation_url)
            
            if validation_result['valid']:
                render_result = renderer.render_from_json(json_output, citation_url)
                final_answer = render_result.get('rendered_answer', '')
            else:
                final_answer = f"VALIDATION FAILED: {'; '.join(validation_result['errors'][:2])}"
            
            result = {
                "query": bundle.query if bundle else "Unknown query",
                "route": gen_result['route'],
                "generation": gen_result,
                "validation": validation_result,
                "rendered_answer": final_answer,
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            formatted_results.append(result)
        
        # Save results to data/artifacts directory
        artifacts_dir = "data/artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)
        
        if args.output:
            # If user specified output path, use it as-is
            output_file = args.output
        else:
            # Default to artifacts directory
            output_file = os.path.join(artifacts_dir, f"phase5_complete_pipeline_{int(time.time())}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_results, f, indent=2, ensure_ascii=False)
        
        print(f"\nOK Complete pipeline processed {len(bundles)} queries")
        print(f"Results saved to: {output_file}")
        
        # Show summary
        valid_count = sum(1 for r in formatted_results if r['validation']['valid'])
        refusal_count = sum(1 for r in formatted_results if r['generation']['refusal'])
        print(f"Summary: {valid_count}/{len(bundles)} passed validation, {refusal_count} refusals")
        
    except Exception as e:
        print(f"X Complete pipeline failed: {e}")


def load_context_bundles_from_file(file_path: str) -> List[ContextBundle]:
    """Load context bundles from JSONL file."""
    bundles = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # Convert to ContextBundle
                    if 'query' in data and 'route' in data:
                        route_label = RouteLabel[data['route'].upper()]
                        
                        bundle = ContextBundle(
                            query=data['query'],
                            route_label=route_label
                        )
                        
                        # Add citation URL if present
                        if 'citation_url' in data:
                            bundle.citation_url = data['citation_url']
                        
                        # Add primary_chunk if present
                        if 'primary_chunk' in data:
                            from phase4_retrieval.types import RetrievalResult
                            chunk_data = data['primary_chunk']
                            bundle.primary_chunk = RetrievalResult(
                                chunk_id=chunk_data.get('chunk_id', ''),
                                text=chunk_data.get('text', ''),
                                score=chunk_data.get('score', 0.0),
                                metadata=chunk_data.get('metadata', {}),
                                source_url=chunk_data.get('source_url', ''),
                                doc_type=chunk_data.get('doc_type', '')
                            )
                        
                        bundles.append(bundle)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Line {line_num}: Invalid context bundle format - {e}")
                    continue
    
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    
    return bundles


def run_interactive_mode(args):
    """Run interactive Phase 5 mode."""
    print("Phase 5 Interactive Mode")
    print("Commands: 'generate <query>', 'format <json>', 'quit'")
    print("Example: generate What is HDFC Equity Fund?")
    print("Example: format {'answer': 'Test answer'} https://example.com")
    
    try:
        generator = AnswerGenerator()
        validator = create_default_validator()
        renderer = create_default_renderer()
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Exiting interactive mode...")
                    break
                
                if user_input.startswith('generate '):
                    # Parse generation command
                    query = user_input[9:].strip()
                    if not query:
                        print("Please provide a query after 'generate'")
                        continue
                    
                    # Create simple context bundle
                    bundle = ContextBundle(query=query, route_label=RouteLabel.FACTUAL)
                    
                    # Generate answer
                    result = generator.generate_answer(bundle)
                    print(f"Generated: {result['answer']}")
                    print(f"Route: {result['route']}")
                    print(f"Refusal: {result['refusal']}")
                    print(f"Generation time: {result['generation_time']:.3f}s")
                
                elif user_input.startswith('format '):
                    # Parse format command
                    parts = user_input[7:].split(' ', 1)
                    json_str = parts[0].strip()
                    citation_url = parts[1].strip() if len(parts) > 1 else None
                    
                    try:
                        json_data = json.loads(json_str)
                        validation_result = validator.validate_complete_flow(json_data, citation_url)
                        
                        if validation_result['valid']:
                            render_result = renderer.render_from_json(json_data, citation_url)
                            print(f"Formatted: {render_result.get('rendered_answer', 'Error')}")
                        else:
                            print(f"Validation failed: {validation_result['errors']}")
                    except json.JSONDecodeError:
                        print("Invalid JSON format")
                
                else:
                    print("Unknown command. Use 'generate <query>' or 'format <json> [citation_url]'")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"X Interactive mode failed: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Phase 5 - Complete RAG Pipeline")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validation and testing commands
    subparsers.add_parser("validate", help="Validate environment configuration")
    subparsers.add_parser("test-groq", help="Test Groq LLM client")
    subparsers.add_parser("test-generator", help="Test answer generator")
    subparsers.add_parser("test-guards", help="Test answer guards")
    subparsers.add_parser("test-renderer", help="Test answer renderer")
    subparsers.add_parser("test-validator", help="Test output validator")
    
    # Processing commands
    parser_format = subparsers.add_parser("format", help="Format and validate JSONL file")
    parser_format.add_argument("input_file", help="Input JSONL file path")
    parser_format.add_argument("--output", help="Output JSON file path")
    parser_format.add_argument("--verbose", action="store_true", help="Verbose output")
    
    parser_generate = subparsers.add_parser("generate", help="Generate answers from context bundles")
    parser_generate.add_argument("input_file", help="Input JSONL file with context bundles")
    parser_generate.add_argument("--output", help="Output JSON file path")
    
    parser_pipeline = subparsers.add_parser("pipeline", help="Run complete Phase 5 pipeline")
    parser_pipeline.add_argument("input_file", help="Input JSONL file with context bundles")
    parser_pipeline.add_argument("--output", help="Output JSON file path")
    
    # Interactive mode
    subparsers.add_parser("interactive", help="Interactive Phase 5 mode")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == "validate":
        validate_environment()
    elif args.command == "test-groq":
        test_groq()
    elif args.command == "test-generator":
        test_generator()
    elif args.command == "test-guards":
        test_guards()
    elif args.command == "test-renderer":
        test_renderer()
    elif args.command == "test-validator":
        test_validator()
    elif args.command == "format":
        process_formatting_file(args)
    elif args.command == "generate":
        run_batch_generation(args)
    elif args.command == "pipeline":
        run_complete_pipeline(args)
    elif args.command == "interactive":
        run_interactive_mode(args)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()
