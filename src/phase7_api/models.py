"""
Phase 7 API Models.

Pydantic models for request/response validation in the REST API.
These models ensure type safety and proper validation for all API endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# Request Models

class ThreadCreateRequest(BaseModel):
    """Request model for creating a new thread."""
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional thread metadata")


class MessageCreateRequest(BaseModel):
    """Request model for creating a new message."""
    user_message: str = Field(..., min_length=1, max_length=10000, description="User message content")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context for generation")


# Response Models

class ThreadResponse(BaseModel):
    """Response model for thread information."""
    thread_id: str = Field(..., description="Unique thread identifier")
    created_at: datetime = Field(..., description="Thread creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(..., ge=0, description="Number of messages in thread")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Thread metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageResponse(BaseModel):
    """Response model for message information."""
    id: str = Field(..., description="Unique message identifier")
    thread_id: str = Field(..., description="Thread identifier")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    citation_url: Optional[str] = Field(default=None, description="Citation URL for assistant messages")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Message metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageHistoryResponse(BaseModel):
    """Response model for message history."""
    messages: List[MessageResponse] = Field(..., description="List of messages in chronological order")
    total_count: int = Field(..., ge=0, description="Total number of messages")
    has_more: bool = Field(default=False, description="Whether more messages are available")


class AssistantResponse(BaseModel):
    """Response model for assistant message generation."""
    assistant_message: str = Field(..., description="Assistant's response")
    citation_url: Optional[str] = Field(default=None, description="Citation URL for the response")
    last_updated: str = Field(..., description="Last updated timestamp")
    thread_id: str = Field(..., description="Thread identifier")
    message_id: str = Field(..., description="Generated message identifier")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(default="1.0.0", description="API version")
    components: Optional[Dict[str, str]] = Field(default=None, description="Component health status")
    uptime_seconds: Optional[float] = Field(default=None, description="Service uptime in seconds")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Response model for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    """Response model for validation errors."""
    error: str = Field(default="validation_error", description="Error type")
    message: str = Field(..., description="Error message")
    validation_errors: List[Dict[str, Any]] = Field(..., description="Detailed validation errors")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")


class StatsResponse(BaseModel):
    """Response model for API statistics."""
    total_threads: int = Field(..., ge=0, description="Total number of threads")
    active_threads: int = Field(..., ge=0, description="Number of active threads")
    total_messages: int = Field(..., ge=0, description="Total number of messages")
    average_messages_per_thread: float = Field(..., ge=0, description="Average messages per thread")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime in seconds")
    requests_processed: int = Field(..., ge=0, description="Total number of requests processed")
    average_response_time_ms: Optional[float] = Field(default=None, description="Average response time in milliseconds")


# Internal Models (not exposed in API)

class ProcessingMetrics(BaseModel):
    """Internal model for processing metrics."""
    start_time: datetime
    end_time: Optional[datetime] = None
    processing_steps: List[str] = Field(default_factory=list)
    
    @property
    def processing_time_ms(self) -> Optional[int]:
        """Calculate processing time in milliseconds."""
        if self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return None
    
    def mark_step(self, step_name: str):
        """Mark a processing step."""
        self.processing_steps.append(step_name)
    
    def finish(self):
        """Mark processing as finished."""
        self.end_time = datetime.utcnow()


class RequestContext(BaseModel):
    """Internal model for request context."""
    request_id: str
    thread_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_metrics: ProcessingMetrics = Field(default_factory=lambda: ProcessingMetrics(start_time=datetime.utcnow()))


# Custom Validators

@validator('user_message', pre=True, always=True)
def validate_user_message(cls, v):
    """Validate user message content."""
    if not v or not v.strip():
        raise ValueError("User message cannot be empty")
    return v.strip()


@validator('metadata', pre=True, always=True)
def validate_metadata(cls, v):
    """Validate metadata fields."""
    if v is None:
        return v
    
    if not isinstance(v, dict):
        raise ValueError("Metadata must be a dictionary")
    
    # Ensure metadata keys are strings
    for key, value in v.items():
        if not isinstance(key, str):
            raise ValueError("Metadata keys must be strings")
    
    return v


@validator('citation_url', pre=True, always=True)
def validate_citation_url(cls, v):
    """Validate citation URL format."""
    if v is None:
        return v
    
    if not isinstance(v, str):
        raise ValueError("Citation URL must be a string")
    
    v = v.strip()
    if not v:
        return None
    
    # Basic URL validation
    if not (v.startswith('http://') or v.startswith('https://')):
        raise ValueError("Citation URL must start with http:// or https://")
    
    return v


# Utility Functions

def create_error_response(error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Create a standardized error response."""
    return ErrorResponse(
        error=error_type,
        message=message,
        details=details
    )


def create_validation_error_response(validation_errors: List[Dict[str, Any]]) -> ValidationErrorResponse:
    """Create a validation error response."""
    return ValidationErrorResponse(
        message="Request validation failed",
        validation_errors=validation_errors
    )


def create_health_response(status: str, components: Optional[Dict[str, str]] = None, uptime_seconds: Optional[float] = None) -> HealthResponse:
    """Create a health check response."""
    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        components=components,
        uptime_seconds=uptime_seconds
    )
