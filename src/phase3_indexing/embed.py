"""
Embedding engine for Phase 3

Handles batch embedding of chunks using sentence-transformers.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

try:
    from fastembed import TextEmbedding
    HAS_FASTEMBED = True
except ImportError:
    HAS_FASTEMBED = False

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Handles embedding of text chunks using fastembed (memory-efficient)."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu"):
        """
        Initialize embedding engine.
        
        Args:
            model_name: Name of the fastembed model
            device: Device to run embeddings on ('cpu', 'cuda', etc.)
        """
        if not HAS_FASTEMBED:
            raise ImportError("fastembed is required. Install with: pip install fastembed")
        
        self.model_name = model_name
        self.device = device
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the fastembed model."""
        try:
            # FastEmbed uses a slightly different initialization
            self.model = TextEmbedding(model_name=self.model_name)
            logger.info(f"Loaded fastembed model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load fastembed model {self.model_name}: {e}")
            raise
    
    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32) -> List[Dict[str, Any]]:
        """
        Embed a list of chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'text' field
            batch_size: Batch size for embedding
            
        Returns:
            List of chunks with added 'embedding' field
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        logger.info(f"Embedding {len(chunks)} chunks")
        
        # Extract texts from chunks with null checks
        texts = []
        valid_chunks = []
        
        for chunk in chunks:
            text = chunk.get('text', '')
            
            # Skip chunks with null or empty text
            if not text or text == 'null' or not text.strip():
                logger.warning(f"Skipping chunk {chunk.get('chunk_id', 'unknown')}: null or empty text")
                continue
            
            # Handle null metadata fields
            processed_chunk = chunk.copy()
            
            # Flatten metadata if it exists as a nested dictionary
            if 'metadata' in processed_chunk and isinstance(processed_chunk['metadata'], dict):
                metadata_dict = processed_chunk.pop('metadata')
                for k, v in metadata_dict.items():
                    if k not in processed_chunk:  # Don't overwrite top-level fields
                        processed_chunk[k] = v
            
            # Handle null fetched_at
            fetched_at = processed_chunk.get('fetched_at')
            if not fetched_at or fetched_at == 'null':
                processed_chunk['fetched_at'] = datetime.now().isoformat()
                logger.info(f"Added current timestamp for chunk {processed_chunk.get('chunk_id', 'unknown')}")
            
            # Handle null scheme
            scheme = processed_chunk.get('scheme')
            if not scheme or scheme == 'null':
                processed_chunk['scheme'] = 'general'
                logger.info(f"Set general scheme for chunk {processed_chunk.get('chunk_id', 'unknown')}")
            
            # Handle null doc_type
            doc_type = processed_chunk.get('doc_type')
            if not doc_type or doc_type == 'null':
                processed_chunk['doc_type'] = 'general'
                logger.info(f"Set general doc_type for chunk {processed_chunk.get('chunk_id', 'unknown')}")
            
            texts.append(text)
            valid_chunks.append(processed_chunk)
        
        if not texts:
            logger.warning("No valid chunks to embed")
            return []
        
        # Embed in batches
        # fastembed.embed() returns an iterator of embeddings
        embeddings_iter = self.model.embed(texts, batch_size=batch_size)
        embeddings = list(embeddings_iter)
        
        # Add embeddings to chunks
        embedded_chunks = []
        for chunk, embedding in zip(valid_chunks, embeddings):
            embedded_chunk = chunk.copy()
            embedded_chunk['embedding'] = embedding.tolist()
            embedded_chunk['embedded_at'] = datetime.now().isoformat()
            embedded_chunks.append(embedded_chunk)
        
        logger.info(f"Successfully embedded {len(embedded_chunks)} chunks")
        return embedded_chunks
    
    def embed_single(self, text: str) -> List[float]:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        # fastembed.embed() always returns an iterator
        embeddings_iter = self.model.embed([text])
        embedding = list(embeddings_iter)[0]
        return embedding.tolist()
    
    def save_embeddings(self, embedded_chunks: List[Dict[str, Any]], output_path: Path):
        """
        Save embedded chunks to JSONL file.
        
        Args:
            embedded_chunks: List of chunks with embeddings
            output_path: Path to save the embeddings
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in embedded_chunks:
                # Remove embedding from main dict for cleaner JSONL
                chunk_copy = chunk.copy()
                embedding = chunk_copy.pop('embedding', None)
                
                # Create the JSONL entry
                entry = {
                    **chunk_copy,
                    'embedding': embedding
                }
                f.write(json.dumps(entry) + '\n')
        
        logger.info(f"Saved {len(embedded_chunks)} embeddings to {output_path}")
    
    def load_embeddings(self, input_path: Path) -> List[Dict[str, Any]]:
        """
        Load embedded chunks from JSONL file.
        
        Args:
            input_path: Path to load embeddings from
            
        Returns:
            List of chunks with embeddings
        """
        chunks = []
        
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line.strip())
                chunks.append(chunk)
        
        logger.info(f"Loaded {len(chunks)} embedded chunks from {input_path}")
        return chunks
