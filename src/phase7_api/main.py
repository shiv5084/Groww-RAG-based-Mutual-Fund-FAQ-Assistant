"""
Phase 7 - Backend API Service.

FastAPI application providing REST endpoints for the Mutual Fund FAQ Assistant.
Integrates Phase 6 (session management) and Phase 5 (generation pipeline).
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add src to path for imports
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from phase6_sessions.models import Thread, Message, MessageRole as SessionMessageRole, SessionConfig
from phase6_sessions.sqlite_store import SQLiteSessionStore
from phase5_generation.generation.generator import AnswerGenerator
from phase5_generation.formatting.validator import OutputValidator

# Added Phase 4 and Phase 3 imports
import yaml
from phase4_retrieval import IntentRouter, RetrievalEngine, ContextPacker, RouteLabel
from phase3_indexing import EmbeddingEngine, VectorStore, HybridRetriever
from phase3_indexing.hybrid import BM25Index

from .models import (
    ThreadCreateRequest, MessageCreateRequest, ThreadResponse, MessageResponse,
    MessageHistoryResponse, AssistantResponse, HealthResponse, ErrorResponse,
    ValidationErrorResponse, StatsResponse, create_error_response,
    create_validation_error_response, create_health_response, RequestContext
)


# Use API-specific logger
logger = logging.getLogger('phase7_api.main')

# Global variables for services
session_store: Optional[SQLiteSessionStore] = None
answer_generator: Optional[AnswerGenerator] = None
output_validator: Optional[OutputValidator] = None
# Added retrieval components
intent_router: Optional[IntentRouter] = None
retrieval_engine: Optional[RetrievalEngine] = None
context_packer: Optional[ContextPacker] = None
start_time: datetime = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global session_store, answer_generator, output_validator
    
    logger.info("Starting Phase 7 API Service...")
    
    try:
        # Initialize Phase 6 session store
        session_config = SessionConfig(
            max_history_length=10,
            session_timeout_minutes=60,
            cleanup_interval_minutes=30,
            max_concurrent_sessions=1000
        )
        session_store = SQLiteSessionStore(str(ROOT_DIR / "data/sessions/threads.db"), session_config)
        logger.info("Session store initialized")
        
        # Load retrieval configuration
        config_path = ROOT_DIR / "config/retrieval.yaml"
        if not config_path.exists():
            logger.error(f"Retrieval config not found at {config_path}")
            raise FileNotFoundError(f"Retrieval config not found at {config_path}")
            
        with open(config_path, 'r') as f:
            retrieval_config = yaml.safe_load(f)
            
        # Initialize Phase 3 components for retrieval
        logger.info("Initializing retrieval components...")
        embedding_config = retrieval_config.get('phase3_integration', {})
        embedding_engine = EmbeddingEngine(
            model_name=embedding_config.get('embedding_model', 'BAAI/bge-small-en-v1.5'),
            device=embedding_config.get('embedding_device', 'cpu')
        )
        vector_store_config = embedding_config.get('vector_store', {})
        vector_store = VectorStore(
            persist_directory=ROOT_DIR / vector_store_config.get('vector_store_path', 'data/index/chroma'),
            collection_name=vector_store_config.get('vector_store_collection', 'mf_faq_chunks')
        )
        bm25_index_path = ROOT_DIR / embedding_config.get('bm25_index_path', 'data/bm25')
        bm25_index = BM25Index(bm25_index_path)
        hybrid_config = embedding_config.get('hybrid_retrieval', {})
        hybrid_retriever = HybridRetriever(
            embedding_engine=embedding_engine,
            vector_store=vector_store,
            bm25_index=bm25_index,
            alpha=hybrid_config.get('hybrid_alpha', 0.5)
        )
        
        # Initialize Phase 4 components
        global intent_router, retrieval_engine, context_packer
        router_config = retrieval_config.get('router', {})
        intent_router = IntentRouter(router_config)
        
        ret_engine_config = retrieval_config.get('retrieval', {})
        retrieval_engine = RetrievalEngine(
            embedding_engine=embedding_engine,
            vector_store=vector_store,
            hybrid_retriever=hybrid_retriever,
            config=ret_engine_config
        )
        
        cp_config = retrieval_config.get('context_packer', {})
        if 'system_prompts' in retrieval_config:
            cp_config['system_prompts'] = retrieval_config['system_prompts']
        context_packer = ContextPacker(cp_config)
        logger.info("Retrieval pipeline initialized")
        
        # Initialize Phase 5 generation pipeline
        try:
            answer_generator = AnswerGenerator()
            output_validator = OutputValidator()
            logger.info("Generation pipeline initialized")
        except Exception as e:
            logger.warning(f"Generation pipeline initialization failed: {e}")
            logger.info("API will run in session-only mode")
        
        logger.info("Phase 7 API Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start API service: {e}")
        raise
    finally:
        # Cleanup
        if session_store:
            await session_store.close()
        logger.info("Phase 7 API Service stopped")


# Create FastAPI application
app = FastAPI(
    title="Mutual Fund FAQ Assistant API",
    description="REST API for mutual fund FAQ assistant with session management and generation pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content=create_validation_error_response(validation_errors).dict()
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_type="http_error",
            message=exc.detail,
            details={"status_code": exc.status_code}
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            error_type="internal_error",
            message="An internal server error occurred",
            details={"exception": str(exc)}
        ).dict()
    )


# Utility functions
def get_session_store() -> SQLiteSessionStore:
    """Get the session store instance."""
    if session_store is None:
        raise HTTPException(status_code=503, detail="Session store not available")
    return session_store


def get_generation_pipeline() -> tuple[AnswerGenerator, OutputValidator]:
    """Get the generation pipeline components."""
    if answer_generator is None or output_validator is None:
        raise HTTPException(status_code=503, detail="Generation pipeline not available")
    return answer_generator, output_validator


def get_retrieval_pipeline() -> tuple[IntentRouter, RetrievalEngine, ContextPacker]:
    """Get the retrieval pipeline components."""
    if intent_router is None or retrieval_engine is None or context_packer is None:
        raise HTTPException(status_code=503, detail="Retrieval pipeline not available")
    return intent_router, retrieval_engine, context_packer


def convert_session_message_to_response(message: Message) -> MessageResponse:
    """Convert session message to API response model."""
    return MessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        role=message.role.value,
        content=message.content,
        timestamp=message.timestamp,
        citation_url=message.citation_url,
        metadata=message.metadata
    )


def convert_thread_to_response(thread: Thread) -> ThreadResponse:
    """Convert session thread to API response model."""
    return ThreadResponse(
        thread_id=thread.id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        message_count=thread.message_count,
        metadata=thread.metadata
    )


# API Endpoints

@app.post("/api/v1/threads", response_model=ThreadResponse)
async def create_thread(request: ThreadCreateRequest) -> ThreadResponse:
    """Create a new chat thread."""
    store = get_session_store()
    
    try:
        thread = await store.create_thread(request.metadata)
        logger.info(f"Created thread: {thread.id}")
        return convert_thread_to_response(thread)
        
    except Exception as e:
        logger.error(f"Failed to create thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to create thread")


@app.get("/api/v1/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str) -> ThreadResponse:
    """Get thread information."""
    store = get_session_store()
    
    try:
        thread = await store.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return convert_thread_to_response(thread)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get thread")


@app.get("/api/v1/threads/{thread_id}/messages", response_model=MessageHistoryResponse)
async def get_thread_messages(
    thread_id: str,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0
) -> MessageHistoryResponse:
    """Get message history for a thread."""
    store = get_session_store()
    
    try:
        # Verify thread exists
        thread = await store.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Get messages
        messages = await store.get_thread_messages(thread_id, limit, offset)
        total_count = await store.get_thread_message_count(thread_id)
        has_more = (offset + len(messages)) < total_count
        
        response_messages = [convert_session_message_to_response(msg) for msg in messages]
        
        return MessageHistoryResponse(
            messages=response_messages,
            total_count=total_count,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get messages")


@app.post("/api/v1/threads/{thread_id}/messages", response_model=AssistantResponse)
async def send_message(thread_id: str, request: MessageCreateRequest) -> AssistantResponse:
    """Send a user message and get assistant response."""
    store = get_session_store()
    
    try:
        # Verify thread exists
        thread = await store.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Add user message
        user_message = Message(
            thread_id=thread_id,
            role=SessionMessageRole.USER,
            content=request.user_message
        )
        await store.add_message(user_message)
        
        # Get thread history for context
        history = await store.get_thread_history(thread_id, max_messages=10)
        
        # Generate assistant response
        start_processing = time.time()
        assistant_content = "I'm sorry, I'm currently unable to process your request. The generation pipeline is not available."
        citation_url = None
        
        try:
            generator, validator = get_generation_pipeline()
            router, engine, packer = get_retrieval_pipeline()
            
            # Step 1: Intent routing
            route_label = router.classify(request.user_message)
            
            # Step 2: Retrieval
            retrieval_results = engine.retrieve(request.user_message, route_label)
            
            # Step 3: Context packing
            # Convert history to context format expected by packer
            context_messages = []
            for msg in history:
                if msg.role == SessionMessageRole.USER:
                    context_messages.append({"role": "user", "content": msg.content})
                elif msg.role == SessionMessageRole.ASSISTANT:
                    context_messages.append({"role": "assistant", "content": msg.content})
            
            if route_label == RouteLabel.ADVISORY and not retrieval_results:
                context_bundle = packer.build_refusal_response(request.user_message)
            elif route_label == RouteLabel.PERFORMANCE and retrieval_results:
                factsheet_url = retrieval_results[0].source_url
                context_bundle = packer.build_performance_response(request.user_message, factsheet_url)
            else:
                context_bundle = packer.build_context(request.user_message, route_label, retrieval_results)
            
            # Add conversation history to context bundle if needed
            # (ContextPacker currently doesn't handle history, so we might need to inject it or handle in generator)
            
            # Generate response
            generation_result = generator.generate_answer(context_bundle)
            
            if generation_result and "answer" in generation_result:
                assistant_content = generation_result["answer"]
                citation_url = generation_result.get("citation_url", "")
                
                # Validate the response
                validation_result = validator.validate_complete_flow(generation_result)
                if not validation_result.get("valid", False):
                    logger.warning(f"Generated response failed validation: {validation_result}")
                    assistant_content = "I apologize, but I cannot provide a response to that question."
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            # Use fallback response
        
        processing_time_ms = int((time.time() - start_processing) * 1000)
        
        # Add assistant message
        assistant_message = Message(
            thread_id=thread_id,
            role=SessionMessageRole.ASSISTANT,
            content=assistant_content,
            citation_url=citation_url
        )
        await store.add_message(assistant_message)
        
        return AssistantResponse(
            assistant_message=assistant_content,
            citation_url=citation_url,
            last_updated=datetime.utcnow().isoformat(),
            thread_id=thread_id,
            message_id=assistant_message.id,
            processing_time_ms=processing_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process message for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@app.delete("/api/v1/threads/{thread_id}")
async def delete_thread(thread_id: str) -> Dict[str, str]:
    """Delete a thread and all its messages."""
    store = get_session_store()
    
    try:
        success = await store.delete_thread(thread_id)
        if not success:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        logger.info(f"Deleted thread: {thread_id}")
        return {"message": "Thread deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete thread")


@app.get("/api/v1/threads", response_model=List[ThreadResponse])
async def list_threads(limit: Optional[int] = 50, offset: Optional[int] = 0) -> List[ThreadResponse]:
    """List all threads."""
    store = get_session_store()
    
    try:
        threads = await store.list_threads(limit, offset)
        return [convert_thread_to_response(thread) for thread in threads]
        
    except Exception as e:
        logger.error(f"Failed to list threads: {e}")
        raise HTTPException(status_code=500, detail="Failed to list threads")


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    components = {}
    uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
    
    # Check session store
    try:
        if session_store:
            store_health = await session_store.health_check()
            components["session_store"] = store_health["status"]
        else:
            components["session_store"] = "not_initialized"
    except Exception as e:
        components["session_store"] = f"error: {str(e)}"
    
    # Check generation pipeline
    try:
        if answer_generator and output_validator:
            components["generation_pipeline"] = "healthy"
        else:
            components["generation_pipeline"] = "not_available"
    except Exception as e:
        components["generation_pipeline"] = f"error: {str(e)}"
    
    # Determine overall status
    overall_status = "healthy"
    if any("error" in status or status == "not_initialized" for status in components.values()):
        overall_status = "unhealthy"
    elif any(status == "not_available" for status in components.values()):
        overall_status = "degraded"
    
    return create_health_response(
        status=overall_status,
        components=components,
        uptime_seconds=uptime_seconds
    )


@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Get API statistics."""
    store = get_session_store()
    
    try:
        session_stats = await store.get_session_stats()
        uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        return StatsResponse(
            total_threads=session_stats.total_threads,
            active_threads=session_stats.active_threads,
            total_messages=session_stats.total_messages,
            average_messages_per_thread=session_stats.average_messages_per_thread,
            uptime_seconds=uptime_seconds,
            requests_processed=0,  # TODO: Implement request tracking
            average_response_time_ms=None  # TODO: Implement response time tracking
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Mutual Fund FAQ Assistant API",
        "version": "1.0.0",
        "description": "REST API for mutual fund FAQ assistant",
        "docs_url": "/docs",
        "health_url": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
