"""
Phase 7 API Tests.

Comprehensive tests for the REST API endpoints, including thread management,
message exchange, error handling, and integration with Phase 6 and Phase 5.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastapi.testclient import TestClient
from phase7_api.main import app
from phase6_sessions.models import Thread, Message, MessageRole as SessionMessageRole
from phase6_sessions.sqlite_store import SQLiteSessionStore


class TestPhase7API:
    """Test suite for Phase 7 API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    async def temp_session_store(self):
        """Create temporary session store for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        store = SQLiteSessionStore(db_path)
        yield store
        
        await store.close()
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Mutual Fund FAQ Assistant API"
        assert data["version"] == "1.0.0"
        assert "docs_url" in data
        assert "health_url" in data
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert "uptime_seconds" in data
        
        # Check components
        components = data["components"]
        assert "session_store" in components
        assert "generation_pipeline" in components
    
    def test_create_thread(self, client):
        """Test thread creation."""
        # Test without metadata
        response = client.post("/api/v1/threads")
        assert response.status_code == 201
        
        data = response.json()
        assert "thread_id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["message_count"] == 0
        assert data["metadata"] is None
        
        thread_id = data["thread_id"]
        
        # Test with metadata
        metadata = {"user": "test_user", "session": "test_session"}
        response = client.post("/api/v1/threads", json=metadata)
        assert response.status_code == 201
        
        data = response.json()
        assert data["metadata"] == metadata
    
    def test_get_thread(self, client):
        """Test getting thread information."""
        # Create a thread first
        create_response = client.post("/api/v1/threads")
        assert create_response.status_code == 201
        thread_id = create_response.json()["thread_id"]
        
        # Get the thread
        response = client.get(f"/api/v1/threads/{thread_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["thread_id"] == thread_id
        assert "created_at" in data
        assert "updated_at" in data
        assert "message_count" in data
        
        # Test non-existent thread
        response = client.get("/api/v1/threads/non-existent-thread")
        assert response.status_code == 404
        assert "Thread not found" in response.json()["detail"]
    
    def test_send_message(self, client):
        """Test sending a message and getting assistant response."""
        # Create a thread first
        create_response = client.post("/api/v1/threads")
        assert create_response.status_code == 201
        thread_id = create_response.json()["thread_id"]
        
        # Send a message
        message_data = {"user_message": "What is HDFC Equity Fund?"}
        response = client.post(f"/api/v1/threads/{thread_id}/messages", json=message_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "assistant_message" in data
        assert "last_updated" in data
        assert data["thread_id"] == thread_id
        assert "message_id" in data
        assert "processing_time_ms" in data
        
        # Verify the assistant message is not empty
        assert len(data["assistant_message"]) > 0
    
    def test_get_thread_messages(self, client):
        """Test getting thread message history."""
        # Create a thread and send a message
        create_response = client.post("/api/v1/threads")
        thread_id = create_response.json()["thread_id"]
        
        message_data = {"user_message": "Test message"}
        client.post(f"/api/v1/threads/{thread_id}/messages", json=message_data)
        
        # Get messages
        response = client.get(f"/api/v1/threads/{thread_id}/messages")
        assert response.status_code == 200
        
        data = response.json()
        assert "messages" in data
        assert "total_count" in data
        assert "has_more" in data
        
        messages = data["messages"]
        assert len(messages) >= 2  # User message + assistant response
        
        # Check message structure
        for message in messages:
            assert "id" in message
            assert "thread_id" in message
            assert "role" in message
            assert "content" in message
            assert "timestamp" in message
    
    def test_list_threads(self, client):
        """Test listing threads."""
        # Create multiple threads
        thread_ids = []
        for i in range(3):
            response = client.post("/api/v1/threads")
            assert response.status_code == 201
            thread_ids.append(response.json()["thread_id"])
        
        # List threads
        response = client.get("/api/v1/threads")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        
        # Check thread structure
        for thread in data:
            assert "thread_id" in thread
            assert "created_at" in thread
            assert "updated_at" in thread
            assert "message_count" in thread
    
    def test_delete_thread(self, client):
        """Test thread deletion."""
        # Create a thread
        create_response = client.post("/api/v1/threads")
        thread_id = create_response.json()["thread_id"]
        
        # Delete the thread
        response = client.delete(f"/api/v1/threads/{thread_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"]
        
        # Verify thread is deleted
        response = client.get(f"/api/v1/threads/{thread_id}")
        assert response.status_code == 404
        
        # Test deleting non-existent thread
        response = client.delete("/api/v1/threads/non-existent-thread")
        assert response.status_code == 404
    
    def test_message_validation(self, client):
        """Test message validation."""
        # Create a thread
        create_response = client.post("/api/v1/threads")
        thread_id = create_response.json()["thread_id"]
        
        # Test empty message
        response = client.post(f"/api/v1/threads/{thread_id}/messages", json={"user_message": ""})
        assert response.status_code == 422
        
        data = response.json()
        assert data["error"] == "validation_error"
        assert "validation_errors" in data
        
        # Test message too long
        long_message = "a" * 10001  # Exceeds 10000 character limit
        response = client.post(f"/api/v1/threads/{thread_id}/messages", json={"user_message": long_message})
        assert response.status_code == 422
    
    def test_thread_not_found_errors(self, client):
        """Test 404 errors for non-existent threads."""
        non_existent_id = "non-existent-thread-id"
        
        # Test get thread
        response = client.get(f"/api/v1/threads/{non_existent_id}")
        assert response.status_code == 404
        
        # Test get messages
        response = client.get(f"/api/v1/threads/{non_existent_id}/messages")
        assert response.status_code == 404
        
        # Test send message
        response = client.post(f"/api/v1/threads/{non_existent_id}/messages", 
                             json={"user_message": "Test"})
        assert response.status_code == 404
        
        # Test delete thread
        response = client.delete(f"/api/v1/threads/{non_existent_id}")
        assert response.status_code == 404
    
    def test_pagination(self, client):
        """Test pagination functionality."""
        # Create a thread
        create_response = client.post("/api/v1/threads")
        thread_id = create_response.json()["thread_id"]
        
        # Send multiple messages
        for i in range(5):
            message_data = {"user_message": f"Test message {i+1}"}
            client.post(f"/api/v1/threads/{thread_id}/messages", json=message_data)
        
        # Test pagination with limit
        response = client.get(f"/api/v1/threads/{thread_id}/messages?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 3
        assert data["total_count"] >= 10  # 5 user + 5 assistant messages
        assert data["has_more"] is True
        
        # Test pagination with offset
        response = client.get(f"/api/v1/threads/{thread_id}/messages?limit=3&offset=3")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["messages"]) == 3
        assert data["has_more"] is True
    
    def test_stats_endpoint(self, client):
        """Test statistics endpoint."""
        # Create some activity
        for i in range(2):
            client.post("/api/v1/threads")
        
        # Get stats
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_threads" in data
        assert "active_threads" in data
        assert "total_messages" in data
        assert "average_messages_per_thread" in data
        assert "uptime_seconds" in data
        
        # Verify data types
        assert isinstance(data["total_threads"], int)
        assert isinstance(data["active_threads"], int)
        assert isinstance(data["total_messages"], int)
        assert isinstance(data["average_messages_per_thread"], (int, float))
        assert isinstance(data["uptime_seconds"], (int, float))
    
    def test_error_handling(self, client):
        """Test error handling and response format."""
        # Test malformed JSON
        response = client.post("/api/v1/threads", data="invalid json")
        assert response.status_code == 422
        
        # Test missing required field
        response = client.post("/api/v1/threads/any-id/messages", json={})
        assert response.status_code == 422
        
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/v1/threads")
        assert response.status_code == 200
        
        # Check for CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers
    
    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        import threading
        import time
        
        results = []
        
        def create_thread():
            response = client.post("/api/v1/threads")
            results.append(response.status_code)
        
        # Create multiple threads concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 201 for status in results)
        assert len(results) == 5
    
    def test_thread_isolation_via_api(self, client):
        """Test thread isolation through API endpoints."""
        # Create two threads
        thread1_response = client.post("/api/v1/threads")
        thread2_response = client.post("/api/v1/threads")
        
        thread1_id = thread1_response.json()["thread_id"]
        thread2_id = thread2_response.json()["thread_id"]
        
        # Send different messages to each thread
        client.post(f"/api/v1/threads/{thread1_id}/messages", 
                  json={"user_message": "What is HDFC Equity Fund?"})
        client.post(f"/api/v1/threads/{thread2_id}/messages", 
                  json={"user_message": "What are the returns of Axis Bluechip Fund?"})
        
        # Get messages for each thread
        thread1_messages = client.get(f"/api/v1/threads/{thread1_id}/messages").json()
        thread2_messages = client.get(f"/api/v1/threads/{thread2_id}/messages").json()
        
        # Verify isolation
        thread1_contents = [msg["content"] for msg in thread1_messages["messages"]]
        thread2_contents = [msg["content"] for msg in thread2_messages["messages"]]
        
        # Thread 1 should contain HDFC content
        hdfc_found = any("HDFC" in content for content in thread1_contents)
        assert hdfc_found, "Thread 1 should contain HDFC content"
        
        # Thread 2 should contain Axis content
        axis_found = any("Axis" in content for content in thread2_contents)
        assert axis_found, "Thread 2 should contain Axis content"
        
        # Thread 1 should not contain Axis content
        axis_in_thread1 = any("Axis" in content for content in thread1_contents)
        assert not axis_in_thread1, "Thread 1 should not contain Axis content"
        
        # Thread 2 should not contain HDFC content
        hdfc_in_thread2 = any("HDFC" in content for content in thread2_contents)
        assert not hdfc_in_thread2, "Thread 2 should not contain HDFC content"
    
    def test_message_flow_consistency(self, client):
        """Test that message flow is consistent and properly ordered."""
        # Create a thread
        create_response = client.post("/api/v1/threads")
        thread_id = create_response.json()["thread_id"]
        
        # Send multiple messages in sequence
        messages = [
            "First question about mutual funds",
            "Second question about SIP",
            "Third question about taxation"
        ]
        
        for i, message in enumerate(messages):
            response = client.post(f"/api/v1/threads/{thread_id}/messages", 
                                  json={"user_message": message})
            assert response.status_code == 200
            
            # Get all messages and verify order
            messages_response = client.get(f"/api/v1/threads/{thread_id}/messages")
            all_messages = messages_response.json()["messages"]
            
            # Should have pairs of user/assistant messages
            expected_count = (i + 1) * 2
            assert len(all_messages) == expected_count
            
            # Verify the latest user message is present
            user_messages = [msg for msg in all_messages if msg["role"] == "user"]
            assert user_messages[-1]["content"] == message
    
    def test_api_documentation_endpoints(self, client):
        """Test API documentation endpoints."""
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "redoc" in response.text.lower()
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema


class TestAPIIntegration:
    """Integration tests for API with real components."""
    
    def test_full_conversation_flow(self, client):
        """Test a complete conversation flow."""
        # 1. Create a thread
        create_response = client.post("/api/v1/threads")
        assert create_response.status_code == 201
        thread_id = create_response.json()["thread_id"]
        
        # 2. Send first message
        message1 = {"user_message": "What is HDFC Equity Fund?"}
        response1 = client.post(f"/api/v1/threads/{thread_id}/messages", json=message1)
        assert response1.status_code == 200
        
        # 3. Send follow-up message
        message2 = {"user_message": "What about its tax benefits?"}
        response2 = client.post(f"/api/v1/threads/{thread_id}/messages", json=message2)
        assert response2.status_code == 200
        
        # 4. Get complete conversation
        conversation = client.get(f"/api/v1/threads/{thread_id}/messages")
        assert conversation.status_code == 200
        
        data = conversation.json()
        messages = data["messages"]
        
        # Should have 6 messages (3 user + 3 assistant)
        assert len(messages) == 6
        
        # Verify message roles alternate correctly
        roles = [msg["role"] for msg in messages]
        expected_roles = ["user", "assistant", "user", "assistant", "user", "assistant"]
        assert roles == expected_roles
        
        # 5. Check thread info
        thread_info = client.get(f"/api/v1/threads/{thread_id}")
        assert thread_info.status_code == 200
        
        thread_data = thread_info.json()
        assert thread_data["message_count"] == 6
        
        # 6. Clean up
        delete_response = client.delete(f"/api/v1/threads/{thread_id}")
        assert delete_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
