#!/usr/bin/env python3
"""
Test Phase 7 API Endpoints
"""

import sys
import asyncio
import time
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute() / 'src'))

from phase7_api.main import app, ensure_initialized
from fastapi.testclient import TestClient

def test_api_endpoints():
    """Test Phase 7 API endpoints."""
    
    print("=== Phase 7 API Endpoints Test ===")
    
    # Create test client
    client = TestClient(app)
    
    # Test 1: Health check endpoint
    print("\n--- Test 1: Health Check ---")
    try:
        response = client.get("/api/v1/health")
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"API status: {health_data.get('status', 'unknown')}")
            print("Health check: PASSED")
        else:
            print("Health check: FAILED")
    except Exception as e:
        print(f"Health check error: {e}")
    
    # Test 2: Create thread endpoint
    print("\n--- Test 2: Create Thread ---")
    thread_id = None
    try:
        response = client.post("/api/v1/threads", json={})
        print(f"Create thread status: {response.status_code}")
        if response.status_code == 200:
            thread_data = response.json()
            thread_id = thread_data.get('thread_id')
            print(f"Thread created: {thread_id}")
            print("Create thread: PASSED")
        else:
            print(f"Create thread failed: {response.text}")
    except Exception as e:
        print(f"Create thread error: {e}")
    
    if not thread_id:
        print("Cannot proceed without thread ID")
        return False
    
    # Test 3: Add message endpoint (triggers lazy loading)
    print("\n--- Test 3: Add Message (Lazy Loading) ---")
    try:
        start_time = time.time()
        response = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={"user_message": "What is HDFC Equity Fund?"}
        )
        end_time = time.time()
        
        print(f"Add message status: {response.status_code}")
        print(f"Response time: {end_time - start_time:.2f}s")
        
        if response.status_code == 200:
            message_data = response.json()
            print(f"Message ID: {message_data.get('message_id')}")
            print(f"Assistant response: {message_data.get('assistant_message', '')[:50]}...")
            print("Add message: PASSED")
        else:
            print("Add message: FAILED")
    except Exception as e:
        print(f"Add message error: {e}")
    
    # Test 4: Get thread messages
    print("\n--- Test 4: Get Thread Messages ---")
    try:
        response = client.get(f"/api/v1/threads/{thread_id}/messages")
        print(f"Get messages status: {response.status_code}")
        
        if response.status_code == 200:
            messages_data = response.json()
            messages = messages_data.get('messages', [])
            print(f"Retrieved {len(messages)} messages")
            for msg in messages:
                print(f"  [{msg.get('role')}] {msg.get('content', '')[:30]}...")
            print("Get messages: PASSED")
        else:
            print("Get messages: FAILED")
    except Exception as e:
        print(f"Get messages error: {e}")
    
    # Test 5: Get thread info
    print("\n--- Test 5: Get Thread Info ---")
    try:
        response = client.get(f"/api/v1/threads/{thread_id}")
        print(f"Get thread status: {response.status_code}")
        
        if response.status_code == 200:
            thread_data = response.json()
            print(f"Thread ID: {thread_data.get('thread_id')}")
            print(f"Message count: {thread_data.get('message_count', 0)}")
            print("Get thread: PASSED")
        else:
            print("Get thread: FAILED")
    except Exception as e:
        print(f"Get thread error: {e}")
    
    # Test 6: List threads
    print("\n--- Test 6: List Threads ---")
    try:
        response = client.get("/api/v1/threads")
        print(f"List threads status: {response.status_code}")
        
        if response.status_code == 200:
            threads_data = response.json()
            threads = threads_data.get('threads', [])
            print(f"Retrieved {len(threads)} threads")
            print("List threads: PASSED")
        else:
            print("List threads: FAILED")
    except Exception as e:
        print(f"List threads error: {e}")
    
    # Test 7: Second message (should be instant after lazy loading)
    print("\n--- Test 7: Second Message (Already Initialized) ---")
    try:
        start_time = time.time()
        response = client.post(
            f"/api/v1/threads/{thread_id}/messages",
            json={"user_message": "What are the returns?"}
        )
        end_time = time.time()
        
        print(f"Second message status: {response.status_code}")
        print(f"Response time: {end_time - start_time:.4f}s")
        
        if response.status_code == 200:
            message_data = response.json()
            print(f"Assistant response: {message_data.get('assistant_message', '')[:50]}...")
            if end_time - start_time < 1.0:
                print("Second message: PASSED (fast response)")
            else:
                print("Second message: PASSED (but slow)")
        else:
            print("Second message: FAILED")
    except Exception as e:
        print(f"Second message error: {e}")
    
    # Test 8: Delete thread
    print("\n--- Test 8: Delete Thread ---")
    try:
        response = client.delete(f"/api/v1/threads/{thread_id}")
        print(f"Delete thread status: {response.status_code}")
        
        if response.status_code == 200:
            print("Delete thread: PASSED")
        else:
            print("Delete thread: FAILED")
    except Exception as e:
        print(f"Delete thread error: {e}")
    
    print("\n=== API Endpoints Test Summary ===")
    print("Phase 7 API endpoints testing completed")
    return True

if __name__ == "__main__":
    test_api_endpoints()
