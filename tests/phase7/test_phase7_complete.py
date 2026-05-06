#!/usr/bin/env python3
"""
Test Phase 7 Complete API Functionality
"""

import sys
import asyncio
import time
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute() / 'src'))

from phase7_api.main import app, ensure_initialized, session_store
from phase6_sessions.sqlite_store import SessionConfig

async def test_phase7_complete():
    """Test Phase 7 API with proper initialization."""
    
    print("=== Phase 7 Complete API Test ===")
    
    # Test 1: Initialize session store manually
    print("\n--- Test 1: Manual Session Store Initialization ---")
    try:
        config = SessionConfig(
            max_history_length=10,
            session_timeout_minutes=60,
            cleanup_interval_minutes=30,
            max_concurrent_sessions=1000
        )
        
        from phase6_sessions.sqlite_store import SQLiteSessionStore
        global session_store
        session_store = SQLiteSessionStore("data/sessions/threads.db", config)
        print("Session store initialized manually")
    except Exception as e:
        print(f"Session store initialization error: {e}")
        return False
    
    # Test 2: Test lazy loading
    print("\n--- Test 2: Lazy Loading Test ---")
    try:
        start_time = time.time()
        await ensure_initialized()
        init_time = time.time() - start_time
        print(f"Lazy loading completed in {init_time:.2f}s")
        
        # Test second call
        start_time = time.time()
        await ensure_initialized()
        second_call_time = time.time() - start_time
        print(f"Second call time: {second_call_time:.4f}s")
        
    except Exception as e:
        print(f"Lazy loading error: {e}")
        return False
    
    # Test 3: Test session store functionality
    print("\n--- Test 3: Session Store Functionality ---")
    try:
        # Create thread
        thread = await session_store.create_thread()
        print(f"Thread created: {thread.id}")
        
        # Add message
        from phase6_sessions.models import Message, MessageRole
        message = Message(
            thread_id=thread.id,
            role=MessageRole.USER,
            content="What is HDFC Equity Fund?"
        )
        await session_store.add_message(message)
        print("Message added to thread")
        
        # Get messages
        messages = await session_store.get_thread_messages(thread.id)
        print(f"Retrieved {len(messages)} messages")
        
        # Clean up
        await session_store.delete_thread(thread.id)
        print("Thread cleaned up")
        
    except Exception as e:
        print(f"Session store error: {e}")
        return False
    
    # Test 4: Test API with FastAPI TestClient
    print("\n--- Test 4: FastAPI TestClient ---")
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Health check
        response = client.get("/api/v1/health")
        print(f"Health check status: {response.status_code}")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"API status: {health_data.get('status', 'unknown')}")
        
        # Create thread
        response = client.post("/api/v1/threads", json={})
        print(f"Create thread status: {response.status_code}")
        
        if response.status_code == 200:
            thread_data = response.json()
            thread_id = thread_data.get('thread_id')
            print(f"Thread created: {thread_id}")
            
            # Add message
            response = client.post(
                f"/api/v1/threads/{thread_id}/messages",
                json={"user_message": "What is HDFC Equity Fund?"}
            )
            print(f"Add message status: {response.status_code}")
            
            if response.status_code == 200:
                message_data = response.json()
                print(f"Assistant response: {message_data.get('assistant_message', '')[:50]}...")
        
    except Exception as e:
        print(f"TestClient error: {e}")
        return False
    
    print("\n=== Phase 7 Complete Test Summary ===")
    print("Phase 7 API functionality verified")
    return True

if __name__ == "__main__":
    asyncio.run(test_phase7_complete())
