"""
Vector store implementation for Phase 3

Handles ChromaDB operations for storing and retrieving embeddings.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import uuid

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB vector store for embeddings."""
    
    def __init__(self, persist_directory: Path, collection_name: str = "mf_faq_chunks"):
        """
        Initialize vector store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
        """
        if not HAS_CHROMADB:
            raise ImportError("chromadb is required. Install with: pip install chromadb")
        
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Initialize client with persistent storage
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Connected to existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(name=self.collection_name)
                logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_chunks(self, embedded_chunks: List[Dict[str, Any]]):
        """
        Add embedded chunks to the vector store.
        
        Args:
            embedded_chunks: List of chunks with embeddings and metadata
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        logger.info(f"Adding {len(embedded_chunks)} chunks to vector store")
        
        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for chunk in embedded_chunks:
            # Generate unique ID if not present
            chunk_id = chunk.get('chunk_id') or str(uuid.uuid4())
            ids.append(chunk_id)
            
            # Get embedding
            embedding = chunk.get('embedding', [])
            embeddings.append(embedding)
            
            # Get text content
            documents.append(chunk.get('text', ''))
            
            # Prepare metadata (exclude embedding and text from metadata)
            # Flatten nested dictionaries and convert to simple types
            raw_metadata = {k: v for k, v in chunk.items() 
                           if k not in ['embedding', 'text', 'chunk_id']}
            
            # Flatten metadata to only include simple types
            metadata = {}
            for k, v in raw_metadata.items():
                if v is None:
                    metadata[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    metadata[k] = v
                elif isinstance(v, list):
                    # Convert lists to strings if they contain complex types
                    try:
                        metadata[k] = str(v)
                    except:
                        metadata[k] = "[]"
                elif isinstance(v, dict):
                    # Convert dicts to JSON strings
                    try:
                        import json
                        metadata[k] = json.dumps(v, separators=(',', ':'))
                    except:
                        metadata[k] = "{}"
                else:
                    # Convert other types to strings
                    try:
                        metadata[k] = str(v)
                    except:
                        metadata[k] = "unknown"
            metadatas.append(metadata)
        
        # Add to collection in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            self.collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
        
        logger.info(f"Successfully added {len(embedded_chunks)} chunks to vector store")
    
    def search(
        self, 
        query_embedding: List[float], 
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filters
            where_document: Document content filters
            
        Returns:
            Search results from ChromaDB
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {'ids': [[]], 'distances': [[]], 'metadatas': [[]], 'documents': [[]]}
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific chunk by ID.
        
        Args:
            chunk_id: ID of the chunk to retrieve
            
        Returns:
            Chunk data if found, None otherwise
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            results = self.collection.get(ids=[chunk_id])
            if results['ids'] and results['ids'][0]:
                return {
                    'chunk_id': results['ids'][0][0],
                    'text': results['documents'][0][0],
                    'metadata': results['metadatas'][0][0]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None
    
    def delete_chunks(self, chunk_ids: List[str]):
        """
        Delete chunks from the vector store.
        
        Args:
            chunk_ids: List of chunk IDs to delete
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            self.collection.delete(ids=chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks from vector store")
        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Collection statistics
        """
        if not self.collection:
            raise RuntimeError("Collection not initialized")
        
        try:
            count = self.collection.count()
            return {
                'name': self.collection_name,
                'count': count,
                'persist_directory': str(self.persist_directory)
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}
    
    def reset_collection(self):
        """Reset the entire collection and clean up old UUID directories."""
        try:
            # Delete the existing collection
            if self.collection:
                self.client.delete_collection(name=self.collection_name)
                logger.info(f"Deleted existing collection: {self.collection_name}")
            
            # Clean up old UUID directories before creating new collection
            self._cleanup_old_directories()
            
            # Create new collection
            self.collection = self.client.create_collection(name=self.collection_name)
            logger.info(f"Created new collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise
    
    def _cleanup_old_directories(self):
        """Clean up old UUID directories in the persist directory."""
        try:
            import shutil
            import re
            import time
            import os
            
            persist_dir = self.persist_directory
            
            # Look for UUID directories directly in the persist directory
            uuid_dirs = []
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
            
            if persist_dir.exists():
                for item in persist_dir.iterdir():
                    if item.is_dir() and uuid_pattern.match(item.name):
                        uuid_dirs.append(item)
            
            # Remove old UUID directories with retry mechanism
            cleaned_count = 0
            for uuid_dir in uuid_dirs:
                removed = False
                for attempt in range(3):  # Try 3 times
                    try:
                        # Force close any file handles on Windows
                        if os.name == 'nt':  # Windows
                            try:
                                import ctypes
                                ctypes.windll.kernel32.SetFileAttributesW(str(uuid_dir), 2)  # FILE_ATTRIBUTE_HIDDEN
                                time.sleep(0.1)  # Brief pause
                            except:
                                pass
                        
                        shutil.rmtree(uuid_dir)
                        logger.info(f"Cleaned up old collection directory: {uuid_dir.name}")
                        cleaned_count += 1
                        removed = True
                        break
                    except Exception as e:
                        if attempt < 2:  # Don't sleep on last attempt
                            time.sleep(0.5)  # Wait before retry
                        else:
                            logger.warning(f"Failed to remove directory {uuid_dir} after 3 attempts: {e}")
            
            if uuid_dirs:
                logger.info(f"Cleaned up {cleaned_count}/{len(uuid_dirs)} old collection directories")
            else:
                logger.debug("No old collection directories found")
                
        except Exception as e:
            logger.warning(f"Error during directory cleanup: {e}")
            # Don't raise - cleanup failure shouldn't stop collection reset
