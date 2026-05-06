"""
Phase 6 Session Store Interface.

Defines the abstract interface for session storage implementations.
This allows swapping between different storage backends (SQLite, Redis, etc.)
while maintaining the same API.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .models import Thread, Message, ThreadMessage, SessionStats, SessionConfig


class SessionStore(ABC):
    """Abstract interface for session storage."""
    
    def __init__(self, config: Optional[SessionConfig] = None):
        """
        Initialize session store with configuration.
        
        Args:
            config: Session configuration options
        """
        self.config = config or SessionConfig()
    
    @abstractmethod
    async def create_thread(self, metadata: Optional[Dict[str, Any]] = None) -> Thread:
        """
        Create a new chat thread.
        
        Args:
            metadata: Optional metadata for the thread
            
        Returns:
            Created thread object
        """
        pass
    
    @abstractmethod
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """
        Get thread by ID.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Thread object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update_thread(self, thread: Thread) -> bool:
        """
        Update thread metadata.
        
        Args:
            thread: Thread object with updated data
            
        Returns:
            True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_thread(self, thread_id: str) -> bool:
        """
        Delete thread and all its messages.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def list_threads(self, limit: Optional[int] = None, 
                          offset: Optional[int] = None) -> List[Thread]:
        """
        List all threads.
        
        Args:
            limit: Maximum number of threads to return
            offset: Number of threads to skip
            
        Returns:
            List of thread objects
        """
        pass
    
    @abstractmethod
    async def add_message(self, message: Message) -> bool:
        """
        Add a message to a thread.
        
        Args:
            message: Message object to add
            
        Returns:
            True if message added successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[Message]:
        """
        Get message by ID.
        
        Args:
            message_id: Message identifier
            
        Returns:
            Message object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_thread_messages(self, thread_id: str, 
                                 limit: Optional[int] = None,
                                 offset: Optional[int] = None) -> List[Message]:
        """
        Get all messages for a thread.
        
        Args:
            thread_id: Thread identifier
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of message objects ordered by timestamp
        """
        pass
    
    @abstractmethod
    async def get_thread_history(self, thread_id: str, 
                               max_messages: Optional[int] = None) -> List[Message]:
        """
        Get recent message history for a thread (for context window).
        
        Args:
            thread_id: Thread identifier
            max_messages: Maximum number of recent messages to return
            
        Returns:
            List of recent message objects ordered by timestamp
        """
        pass
    
    @abstractmethod
    async def delete_message(self, message_id: str) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message identifier
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_thread_message_count(self, thread_id: str) -> int:
        """
        Get message count for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Number of messages in the thread
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_threads(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up expired threads based on age.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup (uses config default if None)
            
        Returns:
            Number of threads cleaned up
        """
        pass
    
    @abstractmethod
    async def get_session_stats(self) -> SessionStats:
        """
        Get session statistics.
        
        Returns:
            Session statistics object
        """
        pass
    
    @abstractmethod
    async def search_threads(self, query: str, limit: Optional[int] = None) -> List[Thread]:
        """
        Search threads by content or metadata.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching thread objects
        """
        pass
    
    @abstractmethod
    async def search_messages(self, thread_id: str, query: str, 
                             limit: Optional[int] = None) -> List[Message]:
        """
        Search messages within a thread.
        
        Args:
            thread_id: Thread identifier
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching message objects
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the storage backend.
        
        Returns:
            Health check results
        """
        pass
    
    async def close(self):
        """Close the storage connection and cleanup resources."""
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class SessionStoreError(Exception):
    """Base exception for session store errors."""
    pass


class ThreadNotFoundError(SessionStoreError):
    """Raised when a thread is not found."""
    pass


class MessageNotFoundError(SessionStoreError):
    """Raised when a message is not found."""
    pass


class SessionStoreConnectionError(SessionStoreError):
    """Raised when there's a connection error with the storage backend."""
    pass


class SessionStoreValidationError(SessionStoreError):
    """Raised when there's a validation error."""
    pass
