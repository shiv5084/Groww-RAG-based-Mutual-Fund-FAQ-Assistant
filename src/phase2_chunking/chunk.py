"""Phase 2: Chunking strategies and implementation.

This module implements chunking strategies for creating retrieval units
that align with "one fact + one source" principle.

Strategies implemented:
1. Section-aware chunking for structured content (HTML, PDFs with headings)
2. Fixed-window chunking with overlap for unstructured content
3. Hybrid approach combining both strategies
"""

from __future__ import annotations

import re
import logging
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

try:
    import yaml
except ImportError:
    yaml = None

from bs4 import BeautifulSoup, Tag

from .schema import (
    Chunk,
    ChunkSchema,
    create_chunk_metadata,
    DocType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChunkStrategy(Enum):
    """Available chunking strategies."""
    SECTION_AWARE = "section_aware"
    FIXED_WINDOW = "fixed_window"
    HYBRID = "hybrid"


@dataclass
class ChunkingConfig:
    """Configuration for chunking strategies."""
    
    # Fixed window parameters
    window_size: int = 600              # Target window size (characters)
    overlap_size: int = 60              # Overlap size (characters, ~10%)
    min_chunk_size: int = 100           # Minimum chunk size
    
    # Section-aware parameters
    min_section_size: int = 50          # Minimum section size
    max_section_size: int = 2000        # Maximum section size
    combine_short_sections: bool = True  # Combine very short sections
    
    # Quality parameters
    min_content_quality: float = 0.3    # Minimum quality score
    prefer_meaningful_chunks: bool = True # Prefer chunks with meaningful content
    
    # Processing parameters
    strip_html_tags: bool = True         # Strip HTML tags for text extraction
    preserve_section_titles: bool = True # Keep section titles in chunks
    detect_language: bool = True         # Detect chunk language
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "ChunkingConfig":
        """Load configuration from YAML file."""
        if yaml is None:
            logger.error("PyYAML not available, using defaults")
            return cls()
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            return cls(**config_data)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return cls()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return cls()


class BaseChunker(ABC):
    """Abstract base class for chunking strategies."""
    
    def __init__(self, config: ChunkingConfig):
        self.config = config
    
    @abstractmethod
    def chunk_document(
        self,
        doc_id: str,
        source_url: str,
        doc_type: Union[str, DocType],
        text: str,
        fetched_at: str,
        scheme: Optional[str] = None,
        original_format: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk a document into retrieval units."""
        pass
    
    def _create_chunks_with_metadata(
        self,
        doc_id: str,
        source_url: str,
        doc_type: Union[str, DocType],
        chunks_text: List[str],
        chunk_strategy: str,
        fetched_at: str,
        scheme: Optional[str] = None,
        section_info: Optional[List[Dict[str, Any]]] = None
    ) -> List[Chunk]:
        """Create Chunk objects with metadata."""
        chunks = []
        total_chunks = len(chunks_text)
        
        for i, chunk_text in enumerate(chunks_text):
            # Prepend scheme name if available to improve searchability (Context Enrichment)
            enriched_text = chunk_text
            if scheme and scheme != 'general' and scheme != 'null':
                # Only prepend if it's not already at the very beginning of the text
                scheme_prefix = f"Scheme: {scheme}\n"
                if not chunk_text.startswith(scheme_prefix):
                    enriched_text = f"{scheme_prefix}{chunk_text}"

            # Get section info if available
            section_title = None
            heading_level = None
            char_start = None
            char_end = None
            
            if section_info and i < len(section_info):
                info = section_info[i]
                section_title = info.get("title")
                heading_level = info.get("heading_level")
                char_start = info.get("char_start")
                char_end = info.get("char_end")
            
            # Create metadata
            metadata = create_chunk_metadata(
                doc_id=doc_id,
                source_url=source_url,
                doc_type=doc_type,
                chunk_index=i,
                total_chunks=total_chunks,
                text=enriched_text,
                chunk_strategy=chunk_strategy,
                fetched_at=fetched_at,
                scheme=scheme,
                section_title=section_title,
                heading_level=heading_level,
                char_start=char_start,
                char_end=char_end
            )
            
            # Only include chunks meeting quality criteria
            if (metadata.has_meaningful_content or 
                not self.config.prefer_meaningful_chunks or
                len(enriched_text.strip()) >= self.config.min_chunk_size):
                
                chunks.append(Chunk(text=enriched_text, metadata=metadata))
        
        return chunks


class SectionAwareChunker(BaseChunker):
    """Section-aware chunking for structured content."""
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.heading_pattern = re.compile(r'<h([1-6])[^>]*>(.*?)</h[1-6]>', re.IGNORECASE | re.DOTALL)
    
    def chunk_document(
        self,
        doc_id: str,
        source_url: str,
        doc_type: Union[str, DocType],
        text: str,
        fetched_at: str,
        scheme: Optional[str] = None,
        original_format: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk document using section-aware strategy."""
        
        if original_format == "html" and self._looks_like_html(text):
            return self._chunk_html_content(doc_id, source_url, doc_type, text, fetched_at, scheme)
        else:
            return self._chunk_text_content(doc_id, source_url, doc_type, text, fetched_at, scheme)
    
    def _looks_like_html(self, text: str) -> bool:
        """Check if text looks like HTML."""
        return bool(re.search(r'<[^>]+>', text))
    
    def _chunk_html_content(
        self,
        doc_id: str,
        source_url: str,
        doc_type: Union[str, DocType],
        html_text: str,
        fetched_at: str,
        scheme: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk HTML content by sections."""
        
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            sections = self._extract_html_sections(soup)
            
            # Process sections into chunks
            chunks_text = []
            section_info = []
            
            for section in sections:
                section_text = self._clean_section_text(section['content'])
                
                # Skip empty or very short sections
                if len(section_text.strip()) < self.config.min_section_size:
                    continue
                
                # Split large sections if needed
                if len(section_text) > self.config.max_section_size:
                    sub_chunks = self._split_large_section(section_text)
                    for sub_chunk in sub_chunks:
                        chunks_text.append(sub_chunk)
                        section_info.append({
                            'title': section['title'],
                            'heading_level': section['heading_level'],
                            'char_start': None,
                            'char_end': None
                        })
                else:
                    chunks_text.append(section_text)
                    section_info.append({
                        'title': section['title'],
                        'heading_level': section['heading_level'],
                        'char_start': None,
                        'char_end': None
                    })
            
            # Combine very short sections if enabled
            if self.config.combine_short_sections:
                chunks_text, section_info = self._combine_short_sections(chunks_text, section_info)
            
            return self._create_chunks_with_metadata(
                doc_id, source_url, doc_type, chunks_text,
                ChunkStrategy.SECTION_AWARE.value, fetched_at, scheme, section_info
            )
            
        except Exception as e:
            logger.error(f"Error chunking HTML content: {e}")
            # Fallback to text chunking
            return self._chunk_text_content(doc_id, source_url, doc_type, html_text, fetched_at, scheme)
    
    def _extract_html_sections(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract sections from HTML based on headings."""
        sections = []
        
        # Find main content area
        main_content = soup.find('main') or soup.find('body') or soup
        
        if not main_content:
            return sections
        
        current_section = {"title": None, "heading_level": 0, "content": ""}
        
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'ul', 'ol', 'section']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Save previous section if it has content
                if current_section["content"].strip():
                    sections.append(current_section.copy())
                
                # Start new section
                current_section = {
                    "title": self._extract_heading_text(element),
                    "heading_level": int(element.name[1]),
                    "content": ""
                }
            else:
                # Add content to current section
                content_text = self._extract_element_text(element)
                if content_text.strip():
                    if current_section["content"]:
                        current_section["content"] += "\n\n"
                    current_section["content"] += content_text
        
        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _extract_heading_text(self, heading_tag: Tag) -> str:
        """Extract clean text from heading tag."""
        return heading_tag.get_text(strip=True)
    
    def _extract_element_text(self, element: Tag) -> str:
        """Extract clean text from element."""
        if self.config.strip_html_tags:
            return element.get_text(separator='\n', strip=True)
        else:
            return str(element)
    
    def _clean_section_text(self, text: str) -> str:
        """Clean section text."""
        # Replace 3 or more newlines with 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    def _split_large_section(self, text: str) -> List[str]:
        """Split a large section into smaller chunks."""
        chunks = []
        
        # Try to split at paragraph boundaries first
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= self.config.max_section_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                # Save current chunk if not empty
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # Start new chunk
                current_chunk = paragraph
                
                # If paragraph itself is too large, split it
                if len(paragraph) > self.config.max_section_size:
                    words = paragraph.split()
                    current_chunk = ""
                    word_count = 0
                    
                    for word in words:
                        if len(current_chunk) + len(word) + 1 <= self.config.max_section_size:
                            if current_chunk:
                                current_chunk += " "
                            current_chunk += word
                            word_count += 1
                        else:
                            if current_chunk.strip():
                                chunks.append(current_chunk.strip())
                            current_chunk = word
                            word_count = 1
                    
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = ""
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _combine_short_sections(self, chunks_text: List[str], section_info: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Combine very short sections with adjacent ones."""
        if not chunks_text:
            return chunks_text, section_info
        
        combined_chunks = []
        combined_info = []
        
        i = 0
        while i < len(chunks_text):
            current_chunk = chunks_text[i]
            current_info = section_info[i]
            
            # If current chunk is too short, try to combine with next
            if (len(current_chunk) < self.config.min_chunk_size and 
                i + 1 < len(chunks_text)):
                
                next_chunk = chunks_text[i + 1]
                next_info = section_info[i + 1]
                
                combined_text = current_chunk + "\n\n" + next_chunk
                combined_title = current_info['title'] or next_info['title']
                combined_level = current_info['heading_level'] or next_info['heading_level']
                
                combined_chunks.append(combined_text)
                combined_info.append({
                    'title': combined_title,
                    'heading_level': combined_level,
                    'char_start': None,
                    'char_end': None
                })
                
                i += 2  # Skip next chunk as it's been combined
            else:
                combined_chunks.append(current_chunk)
                combined_info.append(current_info)
                i += 1
        
        return combined_chunks, combined_info
    
    def _chunk_text_content(
        self,
        doc_id: str,
        source_url: str,
        doc_type: Union[str, DocType],
        text: str,
        fetched_at: str,
        scheme: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk plain text content using section-like patterns."""
        
        # Try to identify section-like patterns
        sections = self._identify_text_sections(text)
        
        if sections:
            # Use identified sections
            chunks_text = [section['content'] for section in sections]
            section_info = [
                {
                    'title': section['title'],
                    'heading_level': section['heading_level'],
                    'char_start': section.get('char_start'),
                    'char_end': section.get('char_end')
                }
                for section in sections
            ]
        else:
            # Fallback to fixed-window chunking
            return FixedWindowChunker(self.config).chunk_document(
                doc_id, source_url, doc_type, text, fetched_at, scheme
            )
        
        return self._create_chunks_with_metadata(
            doc_id, source_url, doc_type, chunks_text,
            ChunkStrategy.SECTION_AWARE.value, fetched_at, scheme, section_info
        )
    
    def _identify_text_sections(self, text: str) -> List[Dict[str, Any]]:
        """Identify sections in plain text using patterns."""
        sections = []
        
        # Patterns that might indicate sections
        section_patterns = [
            r'^(#{1,6})\s+(.+)$',  # Markdown headers
            r'^([A-Z][A-Z\s]{5,})$',  # ALL CAPS headers
            r'^(\d+\.\s+.+)$',  # Numbered sections
            r'^([A-Z][a-z\s]+:)$',  # Title followed by colon
        ]
        
        lines = text.split('\n')
        current_section = {"title": None, "heading_level": 0, "content": "", "char_start": 0}
        char_position = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line looks like a header
            is_header = False
            header_title = None
            header_level = 0
            
            for pattern in section_patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    is_header = True
                    if pattern == section_patterns[0]:  # Markdown
                        header_level = len(match.group(1))
                        header_title = match.group(2)
                    elif pattern == section_patterns[1]:  # ALL CAPS
                        header_level = 2
                        header_title = match.group(1)
                    elif pattern == section_patterns[2]:  # Numbered
                        header_level = 3
                        header_title = match.group(1)
                    else:  # Colon
                        header_level = 2
                        header_title = match.group(1)
                    break
            
            if is_header and current_section["content"].strip():
                # Save previous section
                sections.append(current_section.copy())
                
                # Start new section
                current_section = {
                    "title": header_title,
                    "heading_level": header_level,
                    "content": "",
                    "char_start": char_position
                }
            else:
                # Add to current section
                if current_section["content"]:
                    current_section["content"] += "\n"
                current_section["content"] += line
            
            char_position += len(line) + 1  # +1 for newline
        
        # Add final section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections


class FixedWindowChunker(BaseChunker):
    """Fixed-window chunking with overlap for unstructured content."""
    
    def chunk_document(
        self,
        doc_id: str,
        source_url: str,
        doc_type: Union[str, DocType],
        text: str,
        fetched_at: str,
        scheme: Optional[str] = None,
        original_format: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk document using fixed-window strategy with overlap."""
        
        # Clean text first
        clean_text = self._clean_text(text)
        
        if len(clean_text) <= self.config.window_size:
            # Single chunk if text is short enough
            return self._create_chunks_with_metadata(
                doc_id, source_url, doc_type, [clean_text],
                ChunkStrategy.FIXED_WINDOW.value, fetched_at, scheme
            )
        
        # Create overlapping windows
        chunks_text = []
        char_start = 0
        
        while char_start < len(clean_text):
            # Calculate window end
            char_end = min(char_start + self.config.window_size, len(clean_text))
            
            # Extract window
            chunk_text = clean_text[char_start:char_end]
            
            # Try to break at sentence boundaries
            if char_end < len(clean_text):
                chunk_text = self._break_at_sentence_boundary(chunk_text)
                char_end = char_start + len(chunk_text)
            
            chunks_text.append(chunk_text)
            
            # Calculate next start position with overlap
            if char_end >= len(clean_text):
                break
            
            char_start = max(char_start + 1, char_end - self.config.overlap_size)
        
        return self._create_chunks_with_metadata(
            doc_id, source_url, doc_type, chunks_text,
            ChunkStrategy.FIXED_WINDOW.value, fetched_at, scheme
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean text for chunking."""
        # Replace 3 or more newlines with 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    def _break_at_sentence_boundary(self, text: str) -> str:
        """Try to break text at sentence boundary."""
        # Look for sentence endings
        sentence_patterns = [
            r'(.+?\.)\s+',     # End with period
            r'(.+?\!)\s+',     # End with exclamation
            r'(.+?\?)\s+',     # End with question mark
        ]
        
        for pattern in sentence_patterns:
            match = re.search(pattern, text)
            if match and len(match.group(1)) > self.config.min_chunk_size // 2:
                return match.group(1)
        
        # If no good sentence boundary found, try to break at word boundary
        words = text.split()
        if len(words) > 1:
            # Remove last incomplete word
            return ' '.join(words[:-1])
        
        return text


class HybridChunker(BaseChunker):
    """Hybrid chunking combining section-aware and fixed-window strategies."""
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.section_chunker = SectionAwareChunker(config)
        self.window_chunker = FixedWindowChunker(config)
    
    def chunk_document(
        self,
        doc_id: str,
        source_url: str,
        doc_type: Union[str, DocType],
        text: str,
        fetched_at: str,
        scheme: Optional[str] = None,
        original_format: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk document using hybrid strategy."""
        
        # First try section-aware chunking
        try:
            section_chunks = self.section_chunker.chunk_document(
                doc_id, source_url, doc_type, text, fetched_at, scheme, original_format
            )
            
            # Check if section chunking produced good results
            if self._evaluate_chunking_quality(section_chunks):
                return section_chunks
            
        except Exception as e:
            logger.warning(f"Section-aware chunking failed: {e}")
        
        # Fallback to fixed-window chunking
        logger.info("Using fixed-window chunking as fallback")
        return self.window_chunker.chunk_document(
            doc_id, source_url, doc_type, text, fetched_at, scheme, original_format
        )
    
    def _evaluate_chunking_quality(self, chunks: List[Chunk]) -> bool:
        """Evaluate if chunking results are good quality."""
        if not chunks:
            return False
        
        # Check average chunk size
        avg_size = sum(len(chunk.text) for chunk in chunks) / len(chunks)
        
        # Should have reasonable average size
        if avg_size < self.config.min_chunk_size:
            return False
        
        # Should have meaningful content
        meaningful_chunks = sum(1 for chunk in chunks if chunk.metadata.has_meaningful_content)
        meaningful_ratio = meaningful_chunks / len(chunks)
        
        if meaningful_ratio < 0.5:
            return False
        
        # Check if chunks are too large
        oversized_chunks = sum(1 for chunk in chunks if len(chunk.text) > self.config.max_section_size)
        if oversized_chunks > len(chunks) * 0.3:  # More than 30% oversized
            return False
        
        return True


# Factory function
def create_chunker(strategy: Union[str, ChunkStrategy], config: ChunkingConfig) -> BaseChunker:
    """Create chunker instance based on strategy."""
    if isinstance(strategy, str):
        strategy = ChunkStrategy(strategy)
    
    if strategy == ChunkStrategy.SECTION_AWARE:
        return SectionAwareChunker(config)
    elif strategy == ChunkStrategy.FIXED_WINDOW:
        return FixedWindowChunker(config)
    elif strategy == ChunkStrategy.HYBRID:
        return HybridChunker(config)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


# Utility functions
def chunk_documents_from_manifest(
    manifest_path: Path,
    text_dir: Path,
    output_path: Path,
    strategy: Union[str, ChunkStrategy] = ChunkStrategy.HYBRID,
    config_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Chunk all documents from a manifest file."""
    
    import json
    from datetime import datetime
    
    # Load configuration
    if config_path:
        config = ChunkingConfig.from_yaml(config_path)
    else:
        config = ChunkingConfig()
    
    # Load manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Create chunker
    chunker = create_chunker(strategy, config)
    
    # Process documents
    all_chunks = []
    processed_docs = 0
    failed_docs = 0
    
    for doc in manifest.get('documents', []):
        if doc.get('processing_status') != 'completed':
            continue
        
        doc_id = doc.get('doc_id')
        source_url = doc.get('source_url')
        doc_type = doc.get('doc_type', 'general')
        fetched_at = doc.get('fetched_at')
        scheme = doc.get('scheme')
        text_file_path = doc.get('text_file_path')
        
        # Null checks and fallbacks
        if not all([doc_id, source_url, text_file_path]):
            logger.warning(f"Skipping document {doc_id}: missing required fields")
            failed_docs += 1
            continue
        
        # Handle null fetched_at with current timestamp fallback
        if not fetched_at or fetched_at == 'null':
            fetched_at = datetime.now().isoformat()
            logger.info(f"Using current timestamp for {doc_id}: fetched_at was null")
        
        # Handle null scheme with default categorization
        if not scheme or scheme == 'null':
            scheme = 'general'
            logger.info(f"Using general scheme for {doc_id}: scheme was null")
        
        # Validate doc_type
        if not doc_type or doc_type == 'null':
            doc_type = 'general'
            logger.info(f"Using general doc_type for {doc_id}: doc_type was null")
        
        # Read text file
        try:
            text_path = Path(text_file_path)
            if not text_path.exists():
                logger.warning(f"Text file not found: {text_path}")
                failed_docs += 1
                continue
            
            with open(text_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # Chunk document
            chunks = chunker.chunk_document(
                doc_id=doc_id,
                source_url=source_url,
                doc_type=doc_type,
                text=text_content,
                fetched_at=fetched_at,
                scheme=scheme
            )
            
            all_chunks.extend(chunks)
            processed_docs += 1
            
            logger.info(f"Processed {doc_id}: {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing document {doc_id}: {e}")
            failed_docs += 1
    
    # Save chunks to JSONL file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(chunk.to_jsonl() + '\n')
    
    # Create summary
    summary = {
        "phase": "2.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "chunking_strategy": strategy.value if isinstance(strategy, ChunkStrategy) else strategy,
        "total_documents": processed_docs + failed_docs,
        "processed_documents": processed_docs,
        "failed_documents": failed_docs,
        "total_chunks": len(all_chunks),
        "average_chunk_size": sum(len(chunk.text) for chunk in all_chunks) / len(all_chunks) if all_chunks else 0,
        "output_file": str(output_path),
        "config": {
            "window_size": config.window_size,
            "overlap_size": config.overlap_size,
            "min_chunk_size": config.min_chunk_size,
            "min_content_quality": config.min_content_quality
        }
    }
    
    logger.info(f"Chunking complete: {len(all_chunks)} chunks from {processed_docs} documents")
    
    return summary
