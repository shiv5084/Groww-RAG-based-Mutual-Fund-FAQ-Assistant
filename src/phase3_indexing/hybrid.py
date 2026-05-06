"""
Hybrid retrieval implementation for Phase 3

Combines semantic search (ChromaDB) with lexical search (BM25) for better retrieval.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import math
from datetime import datetime

try:
    from whoosh import fields, index
    from whoosh.analysis import StandardAnalyzer
    from whoosh.qparser import QueryParser
    HAS_WHOOSH = True
except ImportError:
    HAS_WHOOSH = False

from .embed import EmbeddingEngine
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 index for lexical search using Whoosh."""
    
    def __init__(self, index_dir: Path):
        """
        Initialize BM25 index.
        
        Args:
            index_dir: Directory to store the index
        """
        if not HAS_WHOOSH:
            raise ImportError("whoosh is required. Install with: pip install whoosh")
        
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Whoosh index."""
        schema = fields.Schema(
            chunk_id=fields.ID(stored=True),
            text=fields.TEXT(analyzer=StandardAnalyzer()),
            metadata=fields.TEXT(stored=True)
        )
        
        if index.exists_in(self.index_dir):
            self.index = index.open_dir(self.index_dir)
            logger.info(f"Opened existing BM25 index at {self.index_dir}")
        else:
            self.index = index.create_in(self.index_dir, schema)
            logger.info(f"Created new BM25 index at {self.index_dir}")
    
    def add_documents(self, chunks: List[Dict[str, Any]]):
        """
        Add documents to the BM25 index.
        
        Args:
            chunks: List of chunks to index
        """
        writer = self.index.writer()
        
        try:
            valid_chunks = []
            for chunk in chunks:
                # Null checks for required fields
                # Extract chunk_id from metadata if not at top level
                chunk_id = chunk.get('chunk_id')
                if not chunk_id:
                    metadata = chunk.get('metadata', {})
                    chunk_id = metadata.get('chunk_id')
                
                text = chunk.get('text', '')
                
                # Skip chunks with null or empty chunk_id
                if not chunk_id or chunk_id == 'null':
                    logger.warning(f"Skipping chunk: null chunk_id")
                    continue
                
                # Skip chunks with null or empty text
                if not text or text == 'null' or not text.strip():
                    logger.warning(f"Skipping chunk {chunk_id}: null or empty text")
                    continue
                
                # Handle null metadata fields
                processed_chunk = chunk.copy()
                
                # Handle null fetched_at
                fetched_at = chunk.get('fetched_at')
                if not fetched_at or fetched_at == 'null':
                    processed_chunk['fetched_at'] = datetime.now().isoformat()
                
                # Handle null scheme
                scheme = chunk.get('scheme')
                if not scheme or scheme == 'null':
                    processed_chunk['scheme'] = 'general'
                
                # Handle null doc_type
                doc_type = chunk.get('doc_type')
                if not doc_type or doc_type == 'null':
                    processed_chunk['doc_type'] = 'general'
                
                valid_chunks.append(processed_chunk)
                
                # Use existing metadata if available, otherwise use processed chunk metadata
                if 'metadata' in chunk:
                    metadata_dict = chunk['metadata'].copy()
                    # Update with any processed fields
                    for k, v in processed_chunk.items():
                        if k not in ['chunk_id', 'text', 'embedding', 'metadata']:
                            metadata_dict[k] = v
                else:
                    metadata_dict = {k: v for k, v in processed_chunk.items() 
                                   if k not in ['chunk_id', 'text', 'embedding']}
                
                metadata = json.dumps(metadata_dict)
                
                writer.add_document(
                    chunk_id=chunk_id,
                    text=text,
                    metadata=metadata
                )
            
            writer.commit()
            logger.info(f"Added {len(valid_chunks)} documents to BM25 index")
            if len(valid_chunks) < len(chunks):
                logger.warning(f"Skipped {len(chunks) - len(valid_chunks)} invalid chunks")
        except Exception as e:
            writer.cancel()
            logger.error(f"Failed to add documents to BM25 index: {e}")
            raise
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the BM25 index.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results with scores
        """
        with self.index.searcher() as searcher:
            parser = QueryParser("text", self.index.schema)
            query_obj = parser.parse(query)
            
            results = searcher.search(query_obj, limit=limit)
            
            search_results = []
            for hit in results:
                # Use hit.fields() to access stored fields
                fields = hit.fields()
                chunk_id = fields.get('chunk_id', '')
                text_content = fields.get('text', '')
                metadata_str = fields.get('metadata', '{}')
                
                result = {
                    'chunk_id': chunk_id,
                    'text': text_content,
                    'score': hit.score,
                    'metadata': json.loads(metadata_str) if metadata_str else {}
                }
                search_results.append(result)
            
            return search_results
    
    def get_doc_count(self) -> int:
        """Get the number of documents in the index."""
        with self.index.searcher() as searcher:
            return searcher.doc_count()


class HybridRetriever:
    """Hybrid retriever combining semantic and lexical search."""
    
    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store: VectorStore,
        bm25_index: BM25Index,
        alpha: float = 0.5
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            embedding_engine: Embedding engine for semantic search
            vector_store: Vector store for semantic search
            bm25_index: BM25 index for lexical search
            alpha: Weight for semantic search (0-1), lexical weight = 1-alpha
        """
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.alpha = alpha
        
        logger.info(f"Initialized hybrid retriever with alpha={alpha}")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        semantic_k: int = 10,
        lexical_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search.
        
        Args:
            query: Search query
            top_k: Final number of results to return
            semantic_k: Number of semantic search results
            lexical_k: Number of lexical search results
            filters: Metadata filters for semantic search
            
        Returns:
            List of hybrid search results
        """
        logger.info(f"Performing hybrid search for query: '{query}'")
        
        # Semantic search
        query_embedding = self.embedding_engine.embed_single(query)
        semantic_results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=semantic_k,
            where=filters
        )
        
        # Lexical search
        lexical_results = self.bm25_index.search(query, limit=lexical_k)
        
        # Convert semantic results to standard format
        semantic_docs = []
        if semantic_results['ids'] and semantic_results['ids'][0]:
            for i, chunk_id in enumerate(semantic_results['ids'][0]):
                semantic_docs.append({
                    'chunk_id': chunk_id,
                    'text': semantic_results['documents'][0][i],
                    'score': 1.0 - semantic_results['distances'][0][i],  # Convert distance to similarity
                    'metadata': semantic_results['metadatas'][0][i] if semantic_results['metadatas'][0] else {}
                })
        
        # Score normalization and fusion
        hybrid_results = self._fuse_results(semantic_docs, lexical_results, top_k)
        
        logger.info(f"Returning {len(hybrid_results)} hybrid search results")
        return hybrid_results
    
    def _fuse_results(
        self,
        semantic_results: List[Dict[str, Any]],
        lexical_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Fuse semantic and lexical results using score normalization.
        
        Args:
            semantic_results: Results from semantic search
            lexical_results: Results from lexical search
            top_k: Final number of results
            
        Returns:
            Fused results
        """
        # Normalize semantic scores
        if semantic_results:
            max_semantic_score = max(r['score'] for r in semantic_results)
            min_semantic_score = min(r['score'] for r in semantic_results)
            semantic_range = max_semantic_score - min_semantic_score
            
            for result in semantic_results:
                if semantic_range > 0:
                    result['semantic_score'] = (result['score'] - min_semantic_score) / semantic_range
                else:
                    result['semantic_score'] = 1.0
        else:
            # Empty semantic results
            semantic_results = []
        
        # Normalize lexical scores (BM25 scores)
        if lexical_results:
            max_lexical_score = max(r['score'] for r in lexical_results)
            min_lexical_score = min(r['score'] for r in lexical_results)
            lexical_range = max_lexical_score - min_lexical_score
            
            for result in lexical_results:
                if lexical_range > 0:
                    result['lexical_score'] = (result['score'] - min_lexical_score) / lexical_range
                else:
                    result['lexical_score'] = 1.0
        else:
            # Empty lexical results
            lexical_results = []
        
        # Combine results by chunk_id
        combined_scores = {}
        
        # Add semantic scores
        for result in semantic_results:
            chunk_id = result['chunk_id']
            combined_scores[chunk_id] = {
                'chunk_id': chunk_id,
                'text': result['text'],
                'metadata': result.get('metadata', {}),
                'semantic_score': result['semantic_score'],
                'lexical_score': 0.0
            }
        
        # Add lexical scores
        for result in lexical_results:
            chunk_id = result['chunk_id']
            if chunk_id in combined_scores:
                combined_scores[chunk_id]['lexical_score'] = result['lexical_score']
            else:
                combined_scores[chunk_id] = {
                    'chunk_id': chunk_id,
                    'text': result['text'],
                    'metadata': result.get('metadata', {}),
                    'semantic_score': 0.0,
                    'lexical_score': result['lexical_score']
                }
        
        # Calculate hybrid scores
        for chunk_id, result in combined_scores.items():
            result['hybrid_score'] = (
                self.alpha * result['semantic_score'] + 
                (1 - self.alpha) * result['lexical_score']
            )
        
        # Sort by hybrid score and return top_k
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x['hybrid_score'],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            'vector_store_count': self.vector_store.get_collection_info().get('count', 0),
            'bm25_count': self.bm25_index.get_doc_count(),
            'alpha': self.alpha
        }
