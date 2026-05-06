"""
Phase 6 Session Models.

Defines the data models for chat threads and messages in the multi-threaded
conversation system. These models provide the foundation for session isolation
and thread management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


class MessageRole(Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a single message in a chat thread."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: str = ""
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    citation_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "citation_url": self.citation_url,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary representation."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            thread_id=data.get("thread_id", ""),
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            citation_url=data.get("citation_url"),
            metadata=data.get("metadata", {})
        )


@dataclass
class Thread:
    """Represents a chat thread containing multiple messages."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thread to dictionary representation."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.message_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Thread":
        """Create thread from dictionary representation."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
            message_count=data.get("message_count", 0),
            metadata=data.get("metadata", {})
        )
    
    def update_timestamp(self):
        """Update the thread's last updated timestamp."""
        self.updated_at = datetime.utcnow()


@dataclass
class ThreadMessage:
    """Combined thread and message for database operations."""
    
    thread_id: str
    message_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    citation_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "thread_id": self.thread_id,
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "citation_url": self.citation_url,
            "metadata": self.metadata
        }


@dataclass
class SessionConfig:
    """Configuration for session management."""
    
    max_history_length: int = 10
    session_timeout_minutes: int = 60
    cleanup_interval_minutes: int = 30
    max_concurrent_sessions: int = 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "max_history_length": self.max_history_length,
            "session_timeout_minutes": self.session_timeout_minutes,
            "cleanup_interval_minutes": self.cleanup_interval_minutes,
            "max_concurrent_sessions": self.max_concurrent_sessions
        }


@dataclass
class SessionStats:
    """Statistics for session management."""
    
    total_threads: int = 0
    active_threads: int = 0
    total_messages: int = 0
    average_messages_per_thread: float = 0.0
    oldest_thread_age_hours: float = 0.0
    newest_thread_age_hours: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_threads": self.total_threads,
            "active_threads": self.active_threads,
            "total_messages": self.total_messages,
            "average_messages_per_thread": self.average_messages_per_thread,
            "oldest_thread_age_hours": self.oldest_thread_age_hours,
            "newest_thread_age_hours": self.newest_thread_age_hours
        }


# Type aliases for better readability
ThreadID = str
MessageID = str
SessionID = str
