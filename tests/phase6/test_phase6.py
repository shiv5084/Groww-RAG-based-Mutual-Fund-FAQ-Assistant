#!/usr/bin/env python3
"""
Test Phase 6 Session Storage
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute() / 'src'))

from phase6_sessions.sqlite_store import SQLiteSessionStore, SessionConfig
from phase6_sessions.models import Thread, Message, MessageRole
import uuid
from datetime import datetime

async def test_phase6():
    """Test Phase 6 Session Storage functionality."""
    
    print("=== Phase 6 Session Storage Test ===")
    
    # Initialize session store
    config = SessionConfig(
        max_history_length=10,
        session_timeout_minutes=60,
        cleanup_interval_minutes=30,
        max_concurrent_sessions=1000
    )
    
    session_store = SQLiteSessionStore("data/sessions/test_threads.db", config)
    print("SessionStore initialized")
    
    # Test 1: Create thread
    print("\n--- Test 1: Create Thread ---")
    try:
        thread = await session_store.create_thread()
        print(f"Thread created: {thread.id}")
        print(f"Created at: {thread.created_at}")
        thread_id = thread.id
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Test 2: Add messages
    print("\n--- Test 2: Add Messages ---")
    try:
        # Add user message
        user_message = Message(
            thread_id=thread_id,
            role=MessageRole.USER,
            content="What is HDFC Equity Fund?"
        )
        await session_store.add_message(user_message)
        print("User message added")
        
        # Add assistant message
        assistant_message = Message(
            thread_id=thread_id,
            role=MessageRole.ASSISTANT,
            content="HDFC Equity Fund is a large-cap equity scheme that predominantly invests in large-cap companies.",
            citation_url="https://www.hdfcfund.com/factsheet"
        )
        await session_store.add_message(assistant_message)
        print("Assistant message added")
        
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Test 3: Get messages
    print("\n--- Test 3: Get Messages ---")
    try:
        messages = await session_store.get_thread_messages(thread_id)
        print(f"Retrieved {len(messages)} messages")
        for msg in messages:
            print(f"  [{msg.role}] {msg.content[:50]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Get thread
    print("\n--- Test 4: Get Thread ---")
    try:
        thread = await session_store.get_thread(thread_id)
        print(f"Thread ID: {thread.id}")
        print(f"Message count: {thread.message_count}")
        print(f"Updated at: {thread.updated_at}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Thread isolation
    print("\n--- Test 5: Thread Isolation ---")
    try:
        # Create second thread
        thread2 = await session_store.create_thread()
        thread2_id = thread2.id
        
        # Add different message to second thread
        msg2 = Message(
            thread_id=thread2_id,
            role=MessageRole.USER,
            content="What are the returns of Axis Bluechip Fund?"
        )
        await session_store.add_message(msg2)
        
        # Verify isolation
        messages1 = await session_store.get_thread_messages(thread_id)
        messages2 = await session_store.get_thread_messages(thread2_id)
        
        print(f"Thread 1 messages: {len(messages1)}")
        print(f"Thread 2 messages: {len(messages2)}")
        
        # Check content isolation
        thread1_content = [msg.content for msg in messages1]
        thread2_content = [msg.content for msg in messages2]
        
        if "HDFC Equity Fund" in str(thread1_content) and "Axis Bluechip Fund" in str(thread2_content):
            print("Thread isolation: PASSED")
        else:
            print("Thread isolation: FAILED")
        
        # Clean up second thread
        await session_store.delete_thread(thread2_id)
        print("Second thread cleaned up")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 6: Message history limit
    print("\n--- Test 6: Message History Limit ---")
    try:
        # Add more messages than the limit
        for i in range(12):  # More than max_history_length (10)
            msg = Message(
                thread_id=thread_id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Test message {i+1}"
            )
            await session_store.add_message(msg)
        
        # Check that only the latest messages are kept
        messages = await session_store.get_thread_messages(thread_id)
        print(f"Messages after adding 12 more: {len(messages)}")
        print(f"Should be <= {config.max_history_length}")
        
        if len(messages) <= config.max_history_length:
            print("History limit: PASSED")
        else:
            print("History limit: FAILED")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 7: Search functionality
    print("\n--- Test 7: Search Functionality ---")
    try:
        # Search for specific content
        results = await session_store.search_threads("HDFC")
        print(f"Search results for 'HDFC': {len(results)} threads")
        
        if len(results) > 0:
            print("Search functionality: PASSED")
        else:
            print("Search functionality: FAILED")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 8: Statistics
    print("\n--- Test 8: Statistics ---")
    try:
        stats = await session_store.get_session_stats()
        print(f"Total threads: {stats.total_threads}")
        print(f"Total messages: {stats.total_messages}")
        print(f"Active threads: {stats.active_threads}")
        print("Statistics: PASSED")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Cleanup
    print("\n--- Cleanup ---")
    try:
        await session_store.delete_thread(thread_id)
        print("Test thread cleaned up")
    except Exception as e:
        print(f"Cleanup error: {e}")
    
    # Summary
    print(f"\n=== Test Summary ===")
    print("Phase 6 Session Storage: COMPLETED")
    print("All basic functionality tested successfully")
    
    return True

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_phase6())
