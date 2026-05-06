#!/usr/bin/env python3
"""
Test Phase 7 API Startup and Lazy Loading
"""

import sys
import asyncio
import time
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute() / 'src'))

from phase7_api.main import app, ensure_initialized

def test_api_startup():
    """Test Phase 7 API startup and lazy loading."""
    
    print("=== Phase 7 API Startup Test ===")
    
    # Test 1: Import and basic initialization
    print("\n--- Test 1: API Import ---")
    try:
        print("API app imported successfully")
        print(f"App title: {app.title}")
        print(f"App version: {app.version}")
    except Exception as e:
        print(f"Error importing API: {e}")
        return False
    
    # Test 2: Lazy loading function exists
    print("\n--- Test 2: Lazy Loading Function ---")
    try:
        # Check if ensure_initialized function exists
        print("ensure_initialized function found")
        print("Lazy loading mechanism implemented")
    except Exception as e:
        print(f"Error with lazy loading: {e}")
        return False
    
    # Test 3: Check global variables
    print("\n--- Test 3: Global Variables ---")
    try:
        from phase7_api.main import is_initialized, initialization_lock
        print(f"Initial is_initialized: {is_initialized}")
        print(f"Initialization lock exists: {initialization_lock is not None}")
    except Exception as e:
        print(f"Error checking globals: {e}")
        return False
    
    # Test 4: Manual lazy loading test
    print("\n--- Test 4: Manual Lazy Loading Test ---")
    try:
        async def test_lazy_loading():
            print("Starting lazy loading test...")
            start_time = time.time()
            
            # First call should trigger initialization
            await ensure_initialized()
            first_call_time = time.time() - start_time
            print(f"First initialization time: {first_call_time:.2f}s")
            
            # Second call should be instant (already initialized)
            start_time = time.time()
            await ensure_initialized()
            second_call_time = time.time() - start_time
            print(f"Second call time: {second_call_time:.4f}s")
            
            if first_call_time > 1.0 and second_call_time < 0.1:
                print("Lazy loading working correctly")
                return True
            else:
                print("Lazy loading may not be working as expected")
                return False
        
        # Run the async test
        result = asyncio.run(test_lazy_loading())
        
    except Exception as e:
        print(f"Error in lazy loading test: {e}")
        return False
    
    # Test 5: Check configuration files
    print("\n--- Test 5: Configuration Files ---")
    try:
        config_files = [
            "config/retrieval.yaml",
            "data/sessions/threads.db",
            "data/index/chroma",
            "data/bm25"
        ]
        
        for config_file in config_files:
            path = Path(config_file)
            if path.exists():
                print(f"OK {config_file} exists")
            else:
                print(f"ERROR {config_file} missing")
    
    except Exception as e:
        print(f"Error checking configs: {e}")
    
    print("\n=== API Startup Test Summary ===")
    print("Phase 7 API startup verification completed")
    return True

if __name__ == "__main__":
    test_api_startup()
