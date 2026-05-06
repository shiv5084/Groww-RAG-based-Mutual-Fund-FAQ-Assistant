"""
Phase 6 SQLite Session Store Implementation.

Implements the SessionStore interface using SQLite for persistent storage.
This provides a lightweight, file-based solution for session management.
"""

import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .store import SessionStore, ThreadNotFoundError, MessageNotFoundError, SessionStoreConnectionError
from .models import Thread, Message, ThreadMessage, SessionStats, SessionConfig, MessageRole


class SQLiteSessionStore(SessionStore):
    """SQLite implementation of the session store interface."""
    
    def __init__(self, db_path: str = "data/sessions/threads.db", config: Optional[SessionConfig] = None):
        """
        Initialize SQLite session store.
        
        Args:
            db_path: Path to SQLite database file
            config: Session configuration options
        """
        super().__init__(config)
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS threads (
                        id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        message_count INTEGER DEFAULT 0,
                        metadata TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        thread_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        citation_url TEXT,
                        metadata TEXT,
                        FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes for better performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_threads_updated_at ON threads(updated_at)")
                
                conn.commit()
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to initialize database: {e}")
    
    async def create_thread(self, metadata: Optional[Dict[str, Any]] = None) -> Thread:
        """Create a new chat thread."""
        thread = Thread(metadata=metadata or {})
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO threads (id, created_at, updated_at, message_count, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    thread.id,
                    thread.created_at.isoformat(),
                    thread.updated_at.isoformat(),
                    thread.message_count,
                    json.dumps(thread.metadata)
                ))
                conn.commit()
                
            self.logger.info(f"Created thread: {thread.id}")
            return thread
            
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to create thread: {e}")
    
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get thread by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, created_at, updated_at, message_count, metadata
                    FROM threads WHERE id = ?
                """, (thread_id,))
                
                row = cursor.fetchone()
                if row:
                    return Thread(
                        id=row[0],
                        created_at=datetime.fromisoformat(row[1]),
                        updated_at=datetime.fromisoformat(row[2]),
                        message_count=row[3],
                        metadata=json.loads(row[4]) if row[4] else {}
                    )
                return None
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to get thread: {e}")
    
    async def update_thread(self, thread: Thread) -> bool:
        """Update thread metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE threads 
                    SET updated_at = ?, message_count = ?, metadata = ?
                    WHERE id = ?
                """, (
                    thread.updated_at.isoformat(),
                    thread.message_count,
                    json.dumps(thread.metadata),
                    thread.id
                ))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to update thread: {e}")
    
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete thread and all its messages."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    self.logger.info(f"Deleted thread: {thread_id}")
                return success
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to delete thread: {e}")
    
    async def list_threads(self, limit: Optional[int] = None, 
                          offset: Optional[int] = None) -> List[Thread]:
        """List all threads."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT id, created_at, updated_at, message_count, metadata
                    FROM threads
                    ORDER BY updated_at DESC
                """
                params = []
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                if offset:
                    query += " OFFSET ?"
                    params.append(offset)
                
                cursor = conn.execute(query, params)
                threads = []
                
                for row in cursor.fetchall():
                    threads.append(Thread(
                        id=row[0],
                        created_at=datetime.fromisoformat(row[1]),
                        updated_at=datetime.fromisoformat(row[2]),
                        message_count=row[3],
                        metadata=json.loads(row[4]) if row[4] else {}
                    ))
                
                return threads
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to list threads: {e}")
    
    async def add_message(self, message: Message) -> bool:
        """Add a message to a thread."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Add message
                conn.execute("""
                    INSERT INTO messages (id, thread_id, role, content, timestamp, citation_url, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.id,
                    message.thread_id,
                    message.role.value,
                    message.content,
                    message.timestamp.isoformat(),
                    message.citation_url,
                    json.dumps(message.metadata)
                ))
                
                # Update thread message count and timestamp
                conn.execute("""
                    UPDATE threads 
                    SET message_count = message_count + 1, updated_at = ?
                    WHERE id = ?
                """, (message.timestamp.isoformat(), message.thread_id))
                
                conn.commit()
                self.logger.debug(f"Added message {message.id} to thread {message.thread_id}")
                return True
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to add message: {e}")
    
    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get message by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, thread_id, role, content, timestamp, citation_url, metadata
                    FROM messages WHERE id = ?
                """, (message_id,))
                
                row = cursor.fetchone()
                if row:
                    return Message(
                        id=row[0],
                        thread_id=row[1],
                        role=MessageRole(row[2]),
                        content=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        citation_url=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                return None
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to get message: {e}")
    
    async def get_thread_messages(self, thread_id: str, 
                                 limit: Optional[int] = None,
                                 offset: Optional[int] = None) -> List[Message]:
        """Get all messages for a thread."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT id, thread_id, role, content, timestamp, citation_url, metadata
                    FROM messages
                    WHERE thread_id = ?
                    ORDER BY timestamp ASC
                """
                params = [thread_id]
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                if offset:
                    query += " OFFSET ?"
                    params.append(offset)
                
                cursor = conn.execute(query, params)
                messages = []
                
                for row in cursor.fetchall():
                    messages.append(Message(
                        id=row[0],
                        thread_id=row[1],
                        role=MessageRole(row[2]),
                        content=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        citation_url=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    ))
                
                return messages
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to get thread messages: {e}")
    
    async def get_thread_history(self, thread_id: str, 
                               max_messages: Optional[int] = None) -> List[Message]:
        """Get recent message history for a thread."""
        max_messages = max_messages or self.config.max_history_length
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, thread_id, role, content, timestamp, citation_url, metadata
                    FROM messages
                    WHERE thread_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (thread_id, max_messages))
                
                messages = []
                for row in cursor.fetchall():
                    messages.append(Message(
                        id=row[0],
                        thread_id=row[1],
                        role=MessageRole(row[2]),
                        content=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        citation_url=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    ))
                
                # Return in chronological order
                return list(reversed(messages))
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to get thread history: {e}")
    
    async def delete_message(self, message_id: str) -> bool:
        """Delete a message."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get message info for thread update
                cursor = conn.execute("""
                    SELECT thread_id FROM messages WHERE id = ?
                """, (message_id,))
                
                row = cursor.fetchone()
                if not row:
                    return False
                
                thread_id = row[0]
                
                # Delete message
                cursor = conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
                
                if cursor.rowcount > 0:
                    # Update thread message count
                    conn.execute("""
                        UPDATE threads 
                        SET message_count = message_count - 1
                        WHERE id = ?
                    """, (thread_id,))
                    
                    conn.commit()
                    self.logger.debug(f"Deleted message: {message_id}")
                    return True
                
                return False
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to delete message: {e}")
    
    async def get_thread_message_count(self, thread_id: str) -> int:
        """Get message count for a thread."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM messages WHERE thread_id = ?
                """, (thread_id,))
                
                row = cursor.fetchone()
                return row[0] if row else 0
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to get message count: {e}")
    
    async def cleanup_expired_threads(self, max_age_hours: Optional[int] = None) -> int:
        """Clean up expired threads based on age."""
        max_age_hours = max_age_hours or self.config.session_timeout_minutes / 60
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM threads 
                    WHERE updated_at < ?
                """, (cutoff_time.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    self.logger.info(f"Cleaned up {deleted_count} expired threads")
                
                return deleted_count
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to cleanup expired threads: {e}")
    
    async def get_session_stats(self) -> SessionStats:
        """Get session statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total threads
                cursor = conn.execute("SELECT COUNT(*) FROM threads")
                total_threads = cursor.fetchone()[0]
                
                # Active threads (updated within last hour)
                one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM threads WHERE updated_at > ?
                """, (one_hour_ago,))
                active_threads = cursor.fetchone()[0]
                
                # Total messages
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]
                
                # Average messages per thread
                avg_messages = total_messages / total_threads if total_threads > 0 else 0.0
                
                # Oldest and newest thread ages
                cursor = conn.execute("""
                    SELECT MIN(created_at), MAX(created_at) FROM threads
                """)
                oldest_newest = cursor.fetchone()
                
                oldest_age = 0.0
                newest_age = 0.0
                
                if oldest_newest[0]:
                    oldest_created = datetime.fromisoformat(oldest_newest[0])
                    oldest_age = (datetime.utcnow() - oldest_created).total_seconds() / 3600
                
                if oldest_newest[1]:
                    newest_created = datetime.fromisoformat(oldest_newest[1])
                    newest_age = (datetime.utcnow() - newest_created).total_seconds() / 3600
                
                return SessionStats(
                    total_threads=total_threads,
                    active_threads=active_threads,
                    total_messages=total_messages,
                    average_messages_per_thread=avg_messages,
                    oldest_thread_age_hours=oldest_age,
                    newest_thread_age_hours=newest_age
                )
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to get session stats: {e}")
    
    async def search_threads(self, query: str, limit: Optional[int] = None) -> List[Thread]:
        """Search threads by content or metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                sql_query = """
                    SELECT DISTINCT t.id, t.created_at, t.updated_at, t.message_count, t.metadata
                    FROM threads t
                    LEFT JOIN messages m ON t.id = m.thread_id
                    WHERE t.metadata LIKE ? OR m.content LIKE ?
                    ORDER BY t.updated_at DESC
                """
                params = [f"%{query}%", f"%{query}%"]
                
                if limit:
                    sql_query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(sql_query, params)
                threads = []
                
                for row in cursor.fetchall():
                    threads.append(Thread(
                        id=row[0],
                        created_at=datetime.fromisoformat(row[1]),
                        updated_at=datetime.fromisoformat(row[2]),
                        message_count=row[3],
                        metadata=json.loads(row[4]) if row[4] else {}
                    ))
                
                return threads
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to search threads: {e}")
    
    async def search_messages(self, thread_id: str, query: str, 
                             limit: Optional[int] = None) -> List[Message]:
        """Search messages within a thread."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                sql_query = """
                    SELECT id, thread_id, role, content, timestamp, citation_url, metadata
                    FROM messages
                    WHERE thread_id = ? AND content LIKE ?
                    ORDER BY timestamp DESC
                """
                params = [thread_id, f"%{query}%"]
                
                if limit:
                    sql_query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(sql_query, params)
                messages = []
                
                for row in cursor.fetchall():
                    messages.append(Message(
                        id=row[0],
                        thread_id=row[1],
                        role=MessageRole(row[2]),
                        content=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        citation_url=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    ))
                
                return messages
                
        except sqlite3.Error as e:
            raise SessionStoreConnectionError(f"Failed to search messages: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the storage backend."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Test database connectivity
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()
                
                # Get database size
                db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                
                # Get table counts
                cursor = conn.execute("SELECT COUNT(*) FROM threads")
                thread_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                message_count = cursor.fetchone()[0]
                
                return {
                    "status": "healthy",
                    "database_path": self.db_path,
                    "database_size_bytes": db_size,
                    "thread_count": thread_count,
                    "message_count": message_count,
                    "connection_test": "passed"
                }
                
        except sqlite3.Error as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_test": "failed"
            }
    
    async def close(self):
        """Close the storage connection and cleanup resources."""
        # SQLite doesn't require explicit connection closing in this implementation
        # since we use context managers for each operation
        self.logger.info("SQLite session store closed")
