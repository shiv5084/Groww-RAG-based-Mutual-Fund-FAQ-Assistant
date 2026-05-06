"""Phase 2: Chunking, metadata, and indexing preparation.

This module implements chunking strategies for creating retrieval units
that align with "one fact + one source" principle.

Key components:
- Section-aware chunking for structured content
- Fixed-window chunking with overlap for unstructured content
- Rich metadata attachment for each chunk
- Configurable chunking parameters
"""

from .chunk import (
    ChunkStrategy,
    SectionAwareChunker,
    FixedWindowChunker,
    HybridChunker,
    Chunk,
    ChunkingConfig,
    chunk_documents_from_manifest,
    create_chunker
)
from .schema import (
    ChunkMetadata,
    ChunkSchema
)

__all__ = [
    "ChunkStrategy",
    "SectionAwareChunker", 
    "FixedWindowChunker",
    "HybridChunker",
    "Chunk",
    "ChunkingConfig",
    "chunk_documents_from_manifest",
    "create_chunker",
    "ChunkMetadata",
    "ChunkSchema"
]
