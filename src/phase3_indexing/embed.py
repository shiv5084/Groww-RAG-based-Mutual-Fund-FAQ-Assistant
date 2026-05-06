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

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Handles embedding of text chunks using fastembed or sentence-transformers."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu"):
        """
        Initialize embedding engine.
        
        Args:
            model_name: Name of the embedding model
            device: Device to run embeddings on ('cpu', 'cuda', etc.)
        """
        if not HAS_FASTEMBED and not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError("Either fastembed or sentence-transformers is required.")
        
        self.model_name = model_name
        self.device = device
        self.model = None
        self.engine_type = None  # 'fastembed' or 'sbert'
        self._load_model()
    
    def _load_model(self):
        """Load the available embedding model."""
        # Prefer FastEmbed for memory efficiency (good for Render)
        if HAS_FASTEMBED:
            try:
                self.model = TextEmbedding(model_name=self.model_name)
                self.engine_type = 'fastembed'
                logger.info(f"Loaded FastEmbed model: {self.model_name}")
                return
            except Exception as e:
                logger.warning(f"Failed to load FastEmbed model, trying SentenceTransformer: {e}")
        
        # Fallback to SentenceTransformer
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer(self.model_name, device=self.device)
                self.engine_type = 'sbert'
                logger.info(f"Loaded SentenceTransformer model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model {self.model_name}: {e}")
                raise
        else:
            raise RuntimeError("No embedding library available to load model.")
    
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
        
        logger.info(f"Embedding {len(chunks)} chunks using {self.engine_type}")
        
        # Extract texts from chunks with null checks
        texts = []
        valid_chunks = []
        
        for chunk in chunks:
            text = chunk.get('text', '')
            if not text or text == 'null' or not text.strip():
                continue
            
            processed_chunk = chunk.copy()
            # Handle metadata flattening and timestamping (omitted for brevity in this mock but present in original)
            if 'metadata' in processed_chunk and isinstance(processed_chunk['metadata'], dict):
                metadata_dict = processed_chunk.pop('metadata')
                for k, v in metadata_dict.items():
                    if k not in processed_chunk:
                        processed_chunk[k] = v
            
            if not processed_chunk.get('fetched_at'):
                processed_chunk['fetched_at'] = datetime.now().isoformat()
            
            texts.append(text)
            valid_chunks.append(processed_chunk)
        
        if not texts:
            return []
        
        # Perform embedding based on engine type
        if self.engine_type == 'fastembed':
            embeddings_iter = self.model.embed(texts, batch_size=batch_size)
            embeddings = [e.tolist() for e in embeddings_iter]
        else:
            embeddings_raw = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            embeddings = embeddings_raw.tolist()
        
        # Add embeddings to chunks
        embedded_chunks = []
        for chunk, embedding in zip(valid_chunks, embeddings):
            embedded_chunk = chunk.copy()
            embedded_chunk['embedding'] = embedding
            embedded_chunk['embedded_at'] = datetime.now().isoformat()
            embedded_chunks.append(embedded_chunk)
        
        return embedded_chunks
    
    def embed_single(self, text: str) -> List[float]:
        """Embed a single text string."""
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        if self.engine_type == 'fastembed':
            embeddings_iter = self.model.embed([text])
            embedding = list(embeddings_iter)[0]
            return embedding.tolist()
        else:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embedding.tolist()
    
    def save_embeddings(self, embedded_chunks: List[Dict[str, Any]], output_path: Path):
        """Save embedded chunks to JSONL file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in embedded_chunks:
                f.write(json.dumps(chunk) + '\n')
        logger.info(f"Saved {len(embedded_chunks)} embeddings to {output_path}")
    
    def load_embeddings(self, input_path: Path) -> List[Dict[str, Any]]:
        """Load embedded chunks from JSONL file."""
        chunks = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                chunks.append(json.loads(line.strip()))
        logger.info(f"Loaded {len(chunks)} embedded chunks from {input_path}")
        return chunks
