#!/usr/bin/env python3
"""
Phase 6 - Multiple Independent Chat Threads CLI Script.

Provides comprehensive session management functionality including thread creation,
message handling, isolation testing, and administrative operations.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase6_sessions.models import Thread, Message, MessageRole, SessionConfig
from phase6_sessions.sqlite_store import SQLiteSessionStore


class Phase6SessionManager:
    """Phase 6 session management interface."""
    
    def __init__(self, db_path: str = "data/sessions/threads.db", config: Optional[SessionConfig] = None):
        """
        Initialize session manager.
        
        Args:
            db_path: Path to SQLite database
            config: Session configuration
        """
        self.db_path = db_path
        self.config = config or SessionConfig()
        self.store = SQLiteSessionStore(db_path, config)
    
    async def create_thread(self, metadata: Optional[Dict[str, Any]] = None) -> Thread:
        """Create a new chat thread."""
        return await self.store.create_thread(metadata)
    
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get thread by ID."""
        return await self.store.get_thread(thread_id)
    
    async def add_message(self, thread_id: str, role: str, content: str, 
                         citation_url: Optional[str] = None) -> Message:
        """Add a message to a thread."""
        message = Message(
            thread_id=thread_id,
            role=MessageRole(role),
            content=content,
            citation_url=citation_url
        )
        await self.store.add_message(message)
        return message
    
    async def get_thread_messages(self, thread_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get messages for a thread."""
        return await self.store.get_thread_messages(thread_id, limit)
    
    async def get_thread_history(self, thread_id: str, max_messages: Optional[int] = None) -> List[Message]:
        """Get recent message history for context window."""
        return await self.store.get_thread_history(thread_id, max_messages)
    
    async def list_threads(self, limit: Optional[int] = None) -> List[Thread]:
        """List all threads."""
        return await self.store.list_threads(limit)
    
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread."""
        return await self.store.delete_thread(thread_id)
    
    async def search_threads(self, query: str, limit: Optional[int] = None) -> List[Thread]:
        """Search threads."""
        return await self.store.search_threads(query, limit)
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        stats = await self.store.get_session_stats()
        return stats.to_dict()
    
    async def cleanup_expired_threads(self, max_age_hours: Optional[int] = None) -> int:
        """Clean up expired threads."""
        return await self.store.cleanup_expired_threads(max_age_hours)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return await self.store.health_check()
    
    async def close(self):
        """Close session manager."""
        await self.store.close()


async def create_thread_command(args):
    """Create a new thread command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        metadata = {}
        if args.metadata:
            metadata = json.loads(args.metadata)
        
        thread = await manager.create_thread(metadata)
        
        print(f"OK Created thread: {thread.id}")
        print(f"   Created at: {thread.created_at}")
        if metadata:
            print(f"   Metadata: {json.dumps(metadata, indent=2)}")
        
    except Exception as e:
        print(f"X Failed to create thread: {e}")
    finally:
        await manager.close()


async def list_threads_command(args):
    """List threads command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        threads = await manager.list_threads(args.limit)
        
        if not threads:
            print("No threads found.")
            return
        
        print(f"Found {len(threads)} threads:")
        print("-" * 80)
        
        for thread in threads:
            print(f"Thread ID: {thread.id}")
            print(f"Created: {thread.created_at}")
            print(f"Updated: {thread.updated_at}")
            print(f"Messages: {thread.message_count}")
            if thread.metadata:
                print(f"Metadata: {json.dumps(thread.metadata, indent=2)}")
            print("-" * 80)
        
    except Exception as e:
        print(f"X Failed to list threads: {e}")
    finally:
        await manager.close()


async def add_message_command(args):
    """Add message command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        # Verify thread exists
        thread = await manager.get_thread(args.thread_id)
        if not thread:
            print(f"X Thread {args.thread_id} not found")
            return
        
        message = await manager.add_message(
            args.thread_id, 
            args.role, 
            args.content, 
            args.citation_url
        )
        
        print(f"OK Added message to thread {args.thread_id}")
        print(f"   Message ID: {message.id}")
        print(f"   Role: {message.role.value}")
        print(f"   Content: {message.content}")
        print(f"   Timestamp: {message.timestamp}")
        if message.citation_url:
            print(f"   Citation: {message.citation_url}")
        
    except Exception as e:
        print(f"X Failed to add message: {e}")
    finally:
        await manager.close()


async def get_messages_command(args):
    """Get messages command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        messages = await manager.get_thread_messages(args.thread_id, args.limit)
        
        if not messages:
            print(f"No messages found for thread {args.thread_id}")
            return
        
        print(f"Messages for thread {args.thread_id}:")
        print("-" * 80)
        
        for message in messages:
            print(f"[{message.timestamp}] {message.role.value.upper()}")
            print(f"{message.content}")
            if message.citation_url:
                print(f"Citation: {message.citation_url}")
            print("-" * 80)
        
    except Exception as e:
        print(f"X Failed to get messages: {e}")
    finally:
        await manager.close()


async def get_history_command(args):
    """Get thread history command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        messages = await manager.get_thread_history(args.thread_id, args.max_messages)
        
        if not messages:
            print(f"No history found for thread {args.thread_id}")
            return
        
        print(f"Recent history for thread {args.thread_id} (last {len(messages)} messages):")
        print("-" * 80)
        
        for message in messages:
            print(f"[{message.timestamp}] {message.role.value.upper()}")
            print(f"{message.content}")
            if message.citation_url:
                print(f"Citation: {message.citation_url}")
            print("-" * 80)
        
    except Exception as e:
        print(f"X Failed to get history: {e}")
    finally:
        await manager.close()


async def delete_thread_command(args):
    """Delete thread command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        success = await manager.delete_thread(args.thread_id)
        
        if success:
            print(f"OK Deleted thread {args.thread_id}")
        else:
            print(f"X Thread {args.thread_id} not found")
        
    except Exception as e:
        print(f"X Failed to delete thread: {e}")
    finally:
        await manager.close()


async def search_command(args):
    """Search command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        if args.type == "threads":
            results = await manager.search_threads(args.query, args.limit)
            print(f"Found {len(results)} threads matching '{args.query}':")
            
            for thread in results:
                print(f"Thread ID: {thread.id}")
                print(f"Updated: {thread.updated_at}")
                print(f"Messages: {thread.message_count}")
                print("-" * 40)
        
        elif args.type == "messages":
            if not args.thread_id:
                print("X Thread ID required for message search")
                return
            
            messages = await manager.store.search_messages(args.thread_id, args.query, args.limit)
            print(f"Found {len(messages)} messages in thread {args.thread_id} matching '{args.query}':")
            
            for message in messages:
                print(f"[{message.timestamp}] {message.role.value}")
                print(f"{message.content}")
                print("-" * 40)
        
    except Exception as e:
        print(f"X Search failed: {e}")
    finally:
        await manager.close()


async def stats_command(args):
    """Statistics command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        stats = await manager.get_session_stats()
        
        print("Session Statistics:")
        print("-" * 40)
        print(f"Total threads: {stats['total_threads']}")
        print(f"Active threads: {stats['active_threads']}")
        print(f"Total messages: {stats['total_messages']}")
        print(f"Average messages per thread: {stats['average_messages_per_thread']:.2f}")
        print(f"Oldest thread age: {stats['oldest_thread_age_hours']:.1f} hours")
        print(f"Newest thread age: {stats['newest_thread_age_hours']:.1f} hours")
        
    except Exception as e:
        print(f"X Failed to get stats: {e}")
    finally:
        await manager.close()


async def cleanup_command(args):
    """Cleanup command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        deleted_count = await manager.cleanup_expired_threads(args.max_age_hours)
        
        print(f"OK Cleaned up {deleted_count} expired threads")
        
    except Exception as e:
        print(f"X Cleanup failed: {e}")
    finally:
        await manager.close()


async def health_command(args):
    """Health check command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        health = await manager.health_check()
        
        print("Health Check Results:")
        print("-" * 40)
        print(f"Status: {health['status']}")
        print(f"Database path: {health['database_path']}")
        print(f"Database size: {health['database_size_bytes']} bytes")
        print(f"Thread count: {health['thread_count']}")
        print(f"Message count: {health['message_count']}")
        print(f"Connection test: {health['connection_test']}")
        
        if health['status'] == 'unhealthy':
            print(f"Error: {health.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"X Health check failed: {e}")
    finally:
        await manager.close()


async def test_isolation_command(args):
    """Test thread isolation command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        print("Testing Thread Isolation...")
        print("=" * 50)
        
        # Create two threads
        thread1 = await manager.create_thread({"test": "isolation", "session": "1"})
        thread2 = await manager.create_thread({"test": "isolation", "session": "2"})
        
        print(f"Created thread1: {thread1.id}")
        print(f"Created thread2: {thread2.id}")
        
        # Add messages to each thread
        await manager.add_message(thread1.id, "user", "What is HDFC Equity Fund?")
        await manager.add_message(thread1.id, "assistant", "HDFC Equity Fund is a large-cap equity scheme.", "https://www.hdfcfund.com")
        
        await manager.add_message(thread2.id, "user", "What are the returns of Axis Bluechip Fund?")
        await manager.add_message(thread2.id, "assistant", "For detailed performance information, please refer to the official scheme factsheet.", "https://www.axismutualfund.com")
        
        # Get messages for each thread
        messages1 = await manager.get_thread_messages(thread1.id)
        messages2 = await manager.get_thread_messages(thread2.id)
        
        print(f"\nThread 1 messages ({len(messages1)}):")
        for msg in messages1:
            print(f"  [{msg.role.value}] {msg.content}")
        
        print(f"\nThread 2 messages ({len(messages2)}):")
        for msg in messages2:
            print(f"  [{msg.role.value}] {msg.content}")
        
        # Verify isolation
        thread1_content = [msg.content for msg in messages1]
        thread2_content = [msg.content for msg in messages2]
        
        # Check that thread1 doesn't contain thread2 content
        isolation_passed = True
        for content in thread2_content:
            if content in thread1_content:
                isolation_passed = False
                break
        
        # Check that thread2 doesn't contain thread1 content
        for content in thread1_content:
            if content in thread2_content:
                isolation_passed = False
                break
        
        print(f"\nIsolation Test Result: {'PASSED' if isolation_passed else 'FAILED'}")
        
        # Cleanup test threads
        await manager.delete_thread(thread1.id)
        await manager.delete_thread(thread2.id)
        print("Test threads cleaned up")
        
    except Exception as e:
        print(f"X Isolation test failed: {e}")
    finally:
        await manager.close()


async def interactive_command(args):
    """Interactive session command."""
    manager = Phase6SessionManager(args.db_path)
    
    try:
        print("Phase 6 Interactive Session Mode")
        print("Commands: 'new', 'list', 'switch <thread_id>', 'send <message>', 'history', 'quit'")
        print("=" * 50)
        
        current_thread = None
        
        while True:
            try:
                user_input = input(f"\n[{current_thread[:8] + '...' if current_thread else 'No thread'}]> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Exiting interactive mode...")
                    break
                
                elif user_input.lower() == 'new':
                    thread = await manager.create_thread()
                    current_thread = thread.id
                    print(f"Created new thread: {thread.id}")
                
                elif user_input.lower() == 'list':
                    threads = await manager.list_threads(10)
                    print(f"Recent threads:")
                    for thread in threads:
                        marker = " (current)" if thread.id == current_thread else ""
                        print(f"  {thread.id[:8]}... - {thread.message_count} messages{marker}")
                
                elif user_input.startswith('switch '):
                    thread_id = user_input[7:].strip()
                    thread = await manager.get_thread(thread_id)
                    if thread:
                        current_thread = thread.id
                        print(f"Switched to thread: {thread.id}")
                    else:
                        print(f"Thread {thread_id} not found")
                
                elif user_input.startswith('send '):
                    if not current_thread:
                        print("No current thread. Use 'new' to create one or 'switch' to select one.")
                        continue
                    
                    message = user_input[5:].strip()
                    await manager.add_message(current_thread, "user", message)
                    
                    # Simulate assistant response
                    response = f"I received your message: '{message}'. This is a simulated response."
                    await manager.add_message(current_thread, "assistant", response)
                    
                    print(f"Sent: {message}")
                    print(f"Assistant: {response}")
                
                elif user_input.lower() == 'history':
                    if not current_thread:
                        print("No current thread selected")
                        continue
                    
                    messages = await manager.get_thread_messages(current_thread, 10)
                    print(f"Recent messages for thread {current_thread}:")
                    for msg in messages:
                        print(f"  [{msg.role.value}] {msg.content}")
                
                else:
                    print("Unknown command. Available: new, list, switch, send, history, quit")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
        
    finally:
        await manager.close()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Phase 6 - Multiple Independent Chat Threads")
    parser.add_argument("--db-path", default="data/sessions/threads.db", help="SQLite database path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Thread management
    parser_create = subparsers.add_parser("create-thread", help="Create a new thread")
    parser_create.add_argument("--metadata", help="Thread metadata as JSON string")
    
    parser_list = subparsers.add_parser("list-threads", help="List threads")
    parser_list.add_argument("--limit", type=int, help="Maximum number of threads to show")
    
    parser_delete = subparsers.add_parser("delete-thread", help="Delete a thread")
    parser_delete.add_argument("thread_id", help="Thread ID to delete")
    
    # Message management
    parser_add = subparsers.add_parser("add-message", help="Add message to thread")
    parser_add.add_argument("thread_id", help="Thread ID")
    parser_add.add_argument("role", choices=["user", "assistant", "system"], help="Message role")
    parser_add.add_argument("content", help="Message content")
    parser_add.add_argument("--citation-url", help="Citation URL for assistant messages")
    
    parser_messages = subparsers.add_parser("get-messages", help="Get messages from thread")
    parser_messages.add_argument("thread_id", help="Thread ID")
    parser_messages.add_argument("--limit", type=int, help="Maximum number of messages")
    
    parser_history = subparsers.add_parser("get-history", help="Get thread history for context")
    parser_history.add_argument("thread_id", help="Thread ID")
    parser_history.add_argument("--max-messages", type=int, help="Maximum messages to return")
    
    # Search
    parser_search = subparsers.add_parser("search", help="Search threads or messages")
    parser_search.add_argument("type", choices=["threads", "messages"], help="Search type")
    parser_search.add_argument("query", help="Search query")
    parser_search.add_argument("--thread-id", help="Thread ID for message search")
    parser_search.add_argument("--limit", type=int, help="Maximum results")
    
    # Administrative
    parser_stats = subparsers.add_parser("stats", help="Show session statistics")
    
    parser_cleanup = subparsers.add_parser("cleanup", help="Clean up expired threads")
    parser_cleanup.add_argument("--max-age-hours", type=int, help="Maximum age in hours")
    
    parser_health = subparsers.add_parser("health", help="Health check")
    
    # Testing
    parser_test = subparsers.add_parser("test-isolation", help="Test thread isolation")
    
    # Interactive
    parser_interactive = subparsers.add_parser("interactive", help="Interactive session mode")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == "create-thread":
        asyncio.run(create_thread_command(args))
    elif args.command == "list-threads":
        asyncio.run(list_threads_command(args))
    elif args.command == "delete-thread":
        asyncio.run(delete_thread_command(args))
    elif args.command == "add-message":
        asyncio.run(add_message_command(args))
    elif args.command == "get-messages":
        asyncio.run(get_messages_command(args))
    elif args.command == "get-history":
        asyncio.run(get_history_command(args))
    elif args.command == "search":
        asyncio.run(search_command(args))
    elif args.command == "stats":
        asyncio.run(stats_command(args))
    elif args.command == "cleanup":
        asyncio.run(cleanup_command(args))
    elif args.command == "health":
        asyncio.run(health_command(args))
    elif args.command == "test-isolation":
        asyncio.run(test_isolation_command(args))
    elif args.command == "interactive":
        asyncio.run(interactive_command(args))
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()
