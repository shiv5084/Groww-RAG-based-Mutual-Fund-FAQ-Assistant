"""
Phase 6 Session Tests.

Tests for thread isolation, session management, and multi-threaded conversation
functionality. Ensures that different threads do not interfere with each other.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phase6_sessions.models import Thread, Message, MessageRole, SessionConfig
from phase6_sessions.sqlite_store import SQLiteSessionStore
from phase6_sessions.store import ThreadNotFoundError, MessageNotFoundError


class TestPhase6Sessions:
    """Test suite for Phase 6 session management."""
    
    @pytest.fixture
    async def temp_store(self):
        """Create a temporary SQLite store for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        store = SQLiteSessionStore(db_path)
        yield store
        
        await store.close()
        # Clean up temp file
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def session_config(self):
        """Create test session configuration."""
        return SessionConfig(
            max_history_length=5,
            session_timeout_minutes=30,
            cleanup_interval_minutes=15,
            max_concurrent_sessions=100
        )
    
    @pytest.mark.asyncio
    async def test_create_thread(self, temp_store):
        """Test thread creation."""
        metadata = {"test": "creation", "user": "test_user"}
        thread = await temp_store.create_thread(metadata)
        
        assert thread.id is not None
        assert isinstance(thread.created_at, datetime)
        assert isinstance(thread.updated_at, datetime)
        assert thread.message_count == 0
        assert thread.metadata == metadata
    
    @pytest.mark.asyncio
    async def test_get_thread(self, temp_store):
        """Test thread retrieval."""
        # Create thread
        created_thread = await temp_store.create_thread({"test": "retrieval"})
        
        # Retrieve thread
        retrieved_thread = await temp_store.get_thread(created_thread.id)
        
        assert retrieved_thread is not None
        assert retrieved_thread.id == created_thread.id
        assert retrieved_thread.created_at == created_thread.created_at
        assert retrieved_thread.metadata == created_thread.metadata
        
        # Test non-existent thread
        non_existent = await temp_store.get_thread("non-existent-id")
        assert non_existent is None
    
    @pytest.mark.asyncio
    async def test_update_thread(self, temp_store):
        """Test thread update."""
        thread = await temp_store.create_thread({"initial": "metadata"})
        
        # Update thread
        thread.metadata = {"updated": "metadata", "version": 2}
        thread.update_timestamp()
        
        success = await temp_store.update_thread(thread)
        assert success is True
        
        # Verify update
        updated_thread = await temp_store.get_thread(thread.id)
        assert updated_thread.metadata == {"updated": "metadata", "version": 2}
        assert updated_thread.updated_at > thread.created_at
    
    @pytest.mark.asyncio
    async def test_delete_thread(self, temp_store):
        """Test thread deletion."""
        thread = await temp_store.create_thread()
        
        # Add a message first
        message = Message(
            thread_id=thread.id,
            role=MessageRole.USER,
            content="Test message"
        )
        await temp_store.add_message(message)
        
        # Delete thread
        success = await temp_store.delete_thread(thread.id)
        assert success is True
        
        # Verify deletion
        deleted_thread = await temp_store.get_thread(thread.id)
        assert deleted_thread is None
        
        # Messages should also be deleted
        deleted_message = await temp_store.get_message(message.id)
        assert deleted_message is None
    
    @pytest.mark.asyncio
    async def test_add_message(self, temp_store):
        """Test message addition."""
        thread = await temp_store.create_thread()
        
        message = Message(
            thread_id=thread.id,
            role=MessageRole.USER,
            content="What is HDFC Equity Fund?",
            citation_url="https://www.hdfcfund.com"
        )
        
        success = await temp_store.add_message(message)
        assert success is True
        
        # Verify message was added
        retrieved_message = await temp_store.get_message(message.id)
        assert retrieved_message is not None
        assert retrieved_message.thread_id == thread.id
        assert retrieved_message.role == MessageRole.USER
        assert retrieved_message.content == message.content
        assert retrieved_message.citation_url == message.citation_url
        
        # Verify thread was updated
        updated_thread = await temp_store.get_thread(thread.id)
        assert updated_thread.message_count == 1
    
    @pytest.mark.asyncio
    async def test_get_thread_messages(self, temp_store):
        """Test retrieving thread messages."""
        thread = await temp_store.create_thread()
        
        # Add multiple messages
        messages = [
            Message(thread_id=thread.id, role=MessageRole.USER, content="Question 1"),
            Message(thread_id=thread.id, role=MessageRole.ASSISTANT, content="Answer 1"),
            Message(thread_id=thread.id, role=MessageRole.USER, content="Question 2"),
        ]
        
        for msg in messages:
            await temp_store.add_message(msg)
        
        # Get all messages
        retrieved_messages = await temp_store.get_thread_messages(thread.id)
        assert len(retrieved_messages) == 3
        
        # Verify order (chronological)
        for i, msg in enumerate(retrieved_messages):
            assert msg.content == messages[i].content
            assert msg.role == messages[i].role
    
    @pytest.mark.asyncio
    async def test_thread_history_window(self, temp_store):
        """Test thread history window functionality."""
        thread = await temp_store.create_thread()
        
        # Add more messages than the history window
        for i in range(10):
            message = Message(
                thread_id=thread.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i+1}"
            )
            await temp_store.add_message(message)
        
        # Get history with default window (should be limited)
        history = await temp_store.get_thread_history(thread.id, max_messages=5)
        assert len(history) == 5
        
        # Should get the most recent 5 messages
        for i, msg in enumerate(history):
            assert msg.content == f"Message {6+i}"  # Messages 6-10
    
    @pytest.mark.asyncio
    async def test_thread_isolation(self, temp_store):
        """Test that threads are isolated from each other."""
        # Create two threads
        thread1 = await temp_store.create_thread({"session": "1"})
        thread2 = await temp_store.create_thread({"session": "2"})
        
        # Add messages to thread1
        await temp_store.add_message(
            Message(thread_id=thread1.id, role=MessageRole.USER, content="Thread 1 question")
        )
        await temp_store.add_message(
            Message(thread_id=thread1.id, role=MessageRole.ASSISTANT, content="Thread 1 answer")
        )
        
        # Add messages to thread2
        await temp_store.add_message(
            Message(thread_id=thread2.id, role=MessageRole.USER, content="Thread 2 question")
        )
        await temp_store.add_message(
            Message(thread_id=thread2.id, role=MessageRole.ASSISTANT, content="Thread 2 answer")
        )
        
        # Get messages for each thread
        thread1_messages = await temp_store.get_thread_messages(thread1.id)
        thread2_messages = await temp_store.get_thread_messages(thread2.id)
        
        # Verify isolation
        assert len(thread1_messages) == 2
        assert len(thread2_messages) == 2
        
        # Thread 1 should only contain its own messages
        thread1_contents = [msg.content for msg in thread1_messages]
        assert "Thread 1 question" in thread1_contents
        assert "Thread 1 answer" in thread1_contents
        assert "Thread 2 question" not in thread1_contents
        assert "Thread 2 answer" not in thread1_contents
        
        # Thread 2 should only contain its own messages
        thread2_contents = [msg.content for msg in thread2_messages]
        assert "Thread 2 question" in thread2_contents
        assert "Thread 2 answer" in thread2_contents
        assert "Thread 1 question" not in thread2_contents
        assert "Thread 1 answer" not in thread2_contents
    
    @pytest.mark.asyncio
    async def test_cross_thread_search_isolation(self, temp_store):
        """Test that searches are properly isolated by thread."""
        # Create two threads with different content
        thread1 = await temp_store.create_thread()
        thread2 = await temp_store.create_thread()
        
        # Add specific content to each thread
        await temp_store.add_message(
            Message(thread_id=thread1.id, role=MessageRole.USER, content="HDFC Equity Fund query")
        )
        await temp_store.add_message(
            Message(thread_id=thread2.id, role=MessageRole.USER, content="Axis Bluechip Fund query")
        )
        
        # Search within thread1
        thread1_results = await temp_store.search_messages(thread1.id, "HDFC")
        assert len(thread1_results) == 1
        assert "HDFC Equity Fund query" in thread1_results[0].content
        
        # Search within thread2
        thread2_results = await temp_store.search_messages(thread2.id, "HDFC")
        assert len(thread2_results) == 0  # Should not find HDFC content in thread2
        
        # Search for Axis in thread2
        axis_results = await temp_store.search_messages(thread2.id, "Axis")
        assert len(axis_results) == 1
        assert "Axis Bluechip Fund query" in axis_results[0].content
    
    @pytest.mark.asyncio
    async def test_list_threads(self, temp_store):
        """Test listing threads."""
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = await temp_store.create_thread({"index": i})
            threads.append(thread)
            
            # Add messages to some threads
            if i % 2 == 0:
                await temp_store.add_message(
                    Message(thread_id=thread.id, role=MessageRole.USER, content=f"Message {i}")
                )
        
        # List all threads
        all_threads = await temp_store.list_threads()
        assert len(all_threads) == 5
        
        # Test limit
        limited_threads = await temp_store.list_threads(limit=3)
        assert len(limited_threads) == 3
        
        # Verify threads are ordered by updated_at (most recent first)
        # Threads with messages should be more recent
        for i, thread in enumerate(limited_threads):
            if i < 3:  # First 3 should be the threads with messages
                assert thread.message_count > 0
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_threads(self, temp_store):
        """Test cleanup of expired threads."""
        # Create a thread
        thread = await temp_store.create_thread()
        
        # Manually update the thread's timestamp to make it appear old
        old_time = datetime.utcnow() - timedelta(hours=25)  # 25 hours ago
        thread.updated_at = old_time
        await temp_store.update_thread(thread)
        
        # Cleanup threads older than 24 hours
        deleted_count = await temp_store.cleanup_expired_threads(max_age_hours=24)
        assert deleted_count == 1
        
        # Verify thread was deleted
        deleted_thread = await temp_store.get_thread(thread.id)
        assert deleted_thread is None
    
    @pytest.mark.asyncio
    async def test_session_stats(self, temp_store):
        """Test session statistics."""
        # Create threads and messages
        for i in range(3):
            thread = await temp_store.create_thread({"index": i})
            # Add varying number of messages
            for j in range(i + 1):
                await temp_store.add_message(
                    Message(thread_id=thread.id, role=MessageRole.USER, content=f"Message {j}")
                )
        
        # Get stats
        stats = await temp_store.get_session_stats()
        
        assert stats.total_threads == 3
        assert stats.total_messages == 6  # 1 + 2 + 3 = 6
        assert stats.average_messages_per_thread == 2.0  # 6 / 3 = 2
        assert stats.oldest_thread_age_hours >= 0
        assert stats.newest_thread_age_hours >= 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, temp_store):
        """Test health check functionality."""
        health = await temp_store.health_check()
        
        assert health["status"] == "healthy"
        assert "database_path" in health
        assert "thread_count" in health
        assert "message_count" in health
        assert health["connection_test"] == "passed"
    
    @pytest.mark.asyncio
    async def test_concurrent_thread_operations(self, temp_store):
        """Test concurrent operations on different threads."""
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = await temp_store.create_thread({"concurrent": i})
            threads.append(thread)
        
        # Add messages to all threads concurrently
        async def add_messages_to_thread(thread, count):
            for i in range(count):
                await temp_store.add_message(
                    Message(
                        thread_id=thread.id,
                        role=MessageRole.USER,
                        content=f"Concurrent message {i}"
                    )
                )
        
        # Run concurrent operations
        tasks = [
            add_messages_to_thread(thread, 3) for thread in threads
        ]
        await asyncio.gather(*tasks)
        
        # Verify all messages were added correctly
        for thread in threads:
            messages = await temp_store.get_thread_messages(thread.id)
            assert len(messages) == 3
            
            # Verify message content
            for i, msg in enumerate(messages):
                assert msg.content == f"Concurrent message {i}"
    
    @pytest.mark.asyncio
    async def test_message_deletion(self, temp_store):
        """Test message deletion and thread count updates."""
        thread = await temp_store.create_thread()
        
        # Add multiple messages
        messages = []
        for i in range(3):
            message = Message(
                thread_id=thread.id,
                role=MessageRole.USER,
                content=f"Message {i}"
            )
            await temp_store.add_message(message)
            messages.append(message)
        
        # Verify initial count
        initial_thread = await temp_store.get_thread(thread.id)
        assert initial_thread.message_count == 3
        
        # Delete one message
        success = await temp_store.delete_message(messages[1].id)
        assert success is True
        
        # Verify message was deleted
        deleted_message = await temp_store.get_message(messages[1].id)
        assert deleted_message is None
        
        # Verify thread count was updated
        updated_thread = await temp_store.get_thread(thread.id)
        assert updated_thread.message_count == 2
        
        # Verify remaining messages are still there
        remaining_messages = await temp_store.get_thread_messages(thread.id)
        assert len(remaining_messages) == 2
        assert remaining_messages[0].content == "Message 0"
        assert remaining_messages[1].content == "Message 2"
    
    @pytest.mark.asyncio
    async def test_search_threads(self, temp_store):
        """Test thread search functionality."""
        # Create threads with searchable content
        thread1 = await temp_store.create_thread({"topic": "mutual_funds", "category": "equity"})
        thread2 = await temp_store.create_thread({"topic": "fixed_deposits", "category": "debt"})
        thread3 = await temp_store.create_thread({"topic": "mutual_funds", "category": "debt"})
        
        # Add messages to threads
        await temp_store.add_message(
            Message(thread_id=thread1.id, role=MessageRole.USER, content="What about HDFC Equity Fund?")
        )
        await temp_store.add_message(
            Message(thread_id=thread2.id, role=MessageRole.USER, content="Tell me about fixed deposits")
        )
        await temp_store.add_message(
            Message(thread_id=thread3.id, role=MessageRole.USER, content="Information about debt mutual funds")
        )
        
        # Search for "mutual_funds"
        mutual_fund_results = await temp_store.search_threads("mutual_funds")
        assert len(mutual_fund_results) == 2  # thread1 and thread3
        
        # Search for "equity"
        equity_results = await temp_store.search_threads("equity")
        assert len(equity_results) == 1  # only thread1
        
        # Search for "fixed"
        fixed_results = await temp_store.search_threads("fixed")
        assert len(fixed_results) == 1  # only thread2
    
    @pytest.mark.asyncio
    async def test_error_handling(self, temp_store):
        """Test error handling for invalid operations."""
        # Test getting non-existent thread
        non_existent_thread = await temp_store.get_thread("invalid-id")
        assert non_existent_thread is None
        
        # Test getting non-existent message
        non_existent_message = await temp_store.get_message("invalid-id")
        assert non_existent_message is None
        
        # Test deleting non-existent thread
        delete_result = await temp_store.delete_thread("invalid-id")
        assert delete_result is False
        
        # Test deleting non-existent message
        delete_msg_result = await temp_store.delete_message("invalid-id")
        assert delete_msg_result is False
        
        # Test adding message to non-existent thread (should fail gracefully)
        invalid_message = Message(
            thread_id="invalid-id",
            role=MessageRole.USER,
            content="Test message"
        )
        
        # This should raise an exception due to foreign key constraint
        with pytest.raises(Exception):  # Should be sqlite3.IntegrityError or similar
            await temp_store.add_message(invalid_message)


if __name__ == "__main__":
    pytest.main([__file__])
