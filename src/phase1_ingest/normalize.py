"""Phase 1.3: Parsing and normalization.

Convert raw files into clean, index-ready text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# HTML parsing
try:
    from bs4 import BeautifulSoup, Tag
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logging.warning("BeautifulSoup4 not available. HTML parsing will be limited.")

# PDF parsing
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logging.warning("PyMuPDF not available. PDF parsing will be limited.")

# Text processing
try:
    import trafilatura
    from trafilatura import extract, fetch_url
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    logging.warning("trafilatura not available. Advanced text extraction will be limited.")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NormalizationResult:
    """Result of a single normalization operation."""
    url_id: str
    source_file: Path
    success: bool
    text_file: Optional[Path] = None
    text_length: Optional[int] = None
    error_message: Optional[str] = None
    content_type: Optional[str] = None


class TextNormalizer:
    """Parse and normalize HTML/PDF files to clean text."""
    
    def __init__(self, raw_dir: Path, text_dir: Path):
        self.raw_dir = Path(raw_dir)
        self.text_dir = Path(text_dir)
        self.text_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TextNormalizer initialized. BS4 available: {HAS_BS4}, Trafilatura available: {HAS_TRAFILATURA}")
        
        # Common boilerplate patterns to remove
        self.boilerplate_patterns = [
            # Navigation and menu items
            r'(?i)(skip to main content|navigation|menu|search)',
            r'(?i)(home|about us|contact|login|register|sign in)',
            # Footer elements
            r'(?i)(copyright|all rights reserved|privacy policy|terms of use)',
            r'(?i)(cookie|cookie policy|cookie consent)',
            # Social media links
            r'(?i)(facebook|twitter|linkedin|instagram|youtube|social)',
            # Common financial site boilerplate
            r'(?i)(download app|mobile app|play store|app store)',
            r'(?i)(invest now|start investing|open account)',
            # Generic repetitive text
            r'(?i)(click here|learn more|read more|find out more)',
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = [(re.compile(pattern), '') for pattern in self.boilerplate_patterns]
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing boilerplate and normalizing whitespace."""
        if not text:
            return ""
        
        # Apply boilerplate pattern removal
        for pattern, replacement in self.compiled_patterns:
            text = pattern.sub(replacement, text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _parse_html_with_trafilatura(self, file_path: Path) -> Optional[str]:
        """Parse HTML using trafilatura for high-quality extraction."""
        if not HAS_TRAFILATURA:
            return None
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Use trafilatura for extraction
            extracted = trafilatura.extract(content, include_comments=False, 
                                           include_tables=True, include_formatting=False)
            
            # For Groww pages, we still want our custom field extraction
            # so we'll use BS4 just for that part even if trafilatura succeeded
            groww_fields = ""
            if HAS_BS4 and ("groww.in" in content or "Groww" in content):
                soup = BeautifulSoup(content, 'html.parser')
                groww_fields = self._extract_groww_fields(soup)
            
            if extracted:
                cleaned_text = self._clean_text(extracted)
                if groww_fields:
                    return f"{groww_fields}\n\n{cleaned_text}"
                return cleaned_text
            elif groww_fields:
                return groww_fields
            
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed for {file_path}: {e}")
        
        return None
    
    def _extract_groww_fields(self, soup: BeautifulSoup) -> str:
        """Extract specific mutual fund fields from Groww HTML."""
        fields = []
        
        # 1. Scheme Name
        name_elem = soup.find('h1', class_=re.compile(r'header_schemeName'))
        if name_elem:
            fields.append(f"Scheme Name: {name_elem.get_text(strip=True)}")
            
        # 2. Riskometer (from pills or specific risk labels)
        risk_pill = soup.find('div', class_=re.compile(r'pill12Pill'), string=re.compile(r'Risk'))
        if not risk_pill:
            # Try searching in spans inside pills
            risk_span = soup.find('span', class_=re.compile(r'bodySmallHeavy'), string=re.compile(r'Risk'))
            if risk_span:
                risk_pill = risk_span.parent
        
        if risk_pill:
            fields.append(f"Riskometer: {risk_pill.get_text(strip=True)}")
            
        # 3. Fund Details (NAV, Min SIP, Fund Size, Expense Ratio)
        # These are usually in containers with class fundDetails_gap4__E4x8C
        detail_containers = soup.find_all('div', class_=re.compile(r'fundDetails_gap4__E4x8C'))
        for container in detail_containers:
            # Some labels are in divs with contentTertiary
            label_elem = container.find('div', class_=re.compile(r'contentTertiary'))
            # Some values are in divs with contentPrimary or bodyXLargeHeavy
            value_elem = container.find('div', class_=re.compile(r'contentPrimary|bodyXLargeHeavy'))
            
            if label_elem and value_elem:
                label = label_elem.get_text(strip=True).replace(':', '').strip()
                value = value_elem.get_text(strip=True).strip()
                if label and value:
                    fields.append(f"{label}: {value}")

        # 4. Exit Load
        # Exit load is often under a heading in the section exitLoadStampDutyTax
        exit_load_header = soup.find(['h3', 'h4'], string=re.compile(r'Exit load', re.I))
        if exit_load_header:
            # Look for the next div with contentSecondary
            exit_load_content = exit_load_header.find_next('div', class_=re.compile(r'contentSecondary'))
            if exit_load_content:
                fields.append(f"Exit Load: {exit_load_content.get_text(strip=True)}")

        # 5. Lock-in (specifically for ELSS)
        lock_in_elem = soup.find('span', class_=re.compile(r'bodyBaseHeavy'), string=re.compile(r'Lock-in'))
        if lock_in_elem:
            fields.append(f"Lock-in Period: {lock_in_elem.get_text(strip=True)}")
        elif any("ELSS" in f for f in fields):
            # Fallback for ELSS if lock-in not explicitly found but it's an ELSS fund
            fields.append("Lock-in Period: 3 years (standard for ELSS)")

        return "\n".join(fields)

    def _parse_html_with_bs4(self, file_path: Path) -> Optional[str]:
        """Parse HTML using BeautifulSoup as fallback."""
        if not HAS_BS4:
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract Groww-specific fields if it looks like a Groww page
            groww_fields = ""
            if "groww.in" in content or soup.find(string=re.compile("Groww")):
                groww_fields = self._extract_groww_fields(soup)
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Try to find main content area
            main_content = None
            
            # Look for common content containers
            for selector in ['main', 'article', '.content', '#content', '.main', '.article']:
                element = soup.select_one(selector)
                if element:
                    main_content = element
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.find('body') or soup
            
            # Extract text
            text = main_content.get_text(separator=' ', strip=True)
            cleaned_text = self._clean_text(text)
            
            # Combine groww fields with general content
            if groww_fields:
                return f"{groww_fields}\n\n{cleaned_text}"
            
            return cleaned_text
            
        except Exception as e:
            logger.warning(f"BeautifulSoup extraction failed for {file_path}: {e}")
        
        return None
    
    def _parse_pdf(self, file_path: Path) -> Optional[str]:
        """Parse PDF using PyMuPDF (fitz)."""
        if not HAS_PYMUPDF:
            return None
        
        try:
            # Open PDF document
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    
                    # Extract text with better formatting
                    page_text = page.get_text()
                    
                    if page_text.strip():
                        # Add page separator for better chunking later
                        text_parts.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
                        
                        # Also try to extract tables if present (useful for financial data)
                        try:
                            tables = page.find_tables()
                            if tables:
                                for table_idx, table in enumerate(tables):
                                    table_data = table.extract()
                                    if table_data:
                                        # Convert table to text format
                                        table_text = self._table_to_text(table_data)
                                        if table_text.strip():
                                            text_parts.append(f"\n--- Table {table_idx + 1} (Page {page_num + 1}) ---\n{table_text}")
                        except Exception as table_error:
                            # Table extraction is optional, don't fail if it doesn't work
                            logger.debug(f"Table extraction failed on page {page_num + 1}: {table_error}")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
            
            # Close the document
            doc.close()
            
            full_text = '\n'.join(text_parts)
            return self._clean_text(full_text)
                
        except Exception as e:
            logger.warning(f"PDF parsing failed for {file_path}: {e}")
        
        return None
    
    def _table_to_text(self, table_data: list[list[str]]) -> str:
        """Convert table data to readable text format."""
        if not table_data:
            return ""
        
        text_lines = []
        for row_idx, row in enumerate(table_data):
            if row and isinstance(row, list):
                # Clean cell data and join with tabs
                cleaned_cells = [str(cell).strip() for cell in row if cell is not None]
                if cleaned_cells:
                    row_text = " | ".join(cleaned_cells)
                    text_lines.append(row_text)
        
        return "\n".join(text_lines)
    
    def _parse_text_file(self, file_path: Path) -> Optional[str]:
        """Parse plain text file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            return self._clean_text(text)
        except Exception as e:
            logger.warning(f"Text file parsing failed for {file_path}: {e}")
        
        return None
    
    def _detect_content_type(self, file_path: Path) -> str:
        """Detect content type based on file extension."""
        suffix = file_path.suffix.lower()
        
        if suffix in ['.html', '.htm']:
            return 'html'
        elif suffix == '.pdf':
            return 'pdf'
        elif suffix in ['.txt', '.md']:
            return 'text'
        else:
            # Try to detect by content
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(1024)
                    if b'%PDF' in header:
                        return 'pdf'
                    elif b'<html' in header.lower() or b'<!DOCTYPE' in header.upper():
                        return 'html'
                    else:
                        return 'text'
            except Exception:
                return 'unknown'
    
    def normalize_file(self, url_id: str, source_file: Path) -> NormalizationResult:
        """Normalize a single file to clean text."""
        logger.info(f"Normalizing {url_id}: {source_file}")
        
        # Detect content type
        content_type = self._detect_content_type(source_file)
        
        # Extract text based on content type
        extracted_text = None
        
        if content_type == 'html':
            # Try trafilatura first (better quality), fallback to BeautifulSoup
            extracted_text = self._parse_html_with_trafilatura(source_file)
            if not extracted_text:
                extracted_text = self._parse_html_with_bs4(source_file)
                
        elif content_type == 'pdf':
            extracted_text = self._parse_pdf(source_file)
            
        else:
            # Treat as text file
            extracted_text = self._parse_text_file(source_file)
        
        # Check if extraction was successful
        if not extracted_text or len(extracted_text.strip()) < 50:
            error_msg = "Extracted text too short or empty"
            logger.warning(f"{url_id}: {error_msg}")
            return NormalizationResult(
                url_id=url_id,
                source_file=source_file,
                success=False,
                error_message=error_msg,
                content_type=content_type
            )
        
        # Create output file path
        text_file = self.text_dir / f"{url_id}.txt"
        
        # Write normalized text
        try:
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            
            logger.info(f"{url_id}: Successfully normalized {len(extracted_text)} characters")
            
            return NormalizationResult(
                url_id=url_id,
                source_file=source_file,
                success=True,
                text_file=text_file,
                text_length=len(extracted_text),
                content_type=content_type
            )
            
        except Exception as e:
            error_msg = f"Failed to write normalized text: {e}"
            logger.error(f"{url_id}: {error_msg}")
            return NormalizationResult(
                url_id=url_id,
                source_file=source_file,
                success=False,
                error_message=error_msg,
                content_type=content_type
            )
    
    def normalize_batch(self, fetch_results: list[dict[str, Any]]) -> list[NormalizationResult]:
        """Normalize multiple files based on fetch results."""
        results = []
        
        logger.info(f"Starting batch normalization of {len(fetch_results)} files")
        
        for result in fetch_results:
            url_id = result['url_id']
            file_path = result.get('file_path')
            
            # Try to find the file even if file_path is null
            source_file = None
            if file_path:
                source_file = Path(file_path)
            else:
                # Try to find file by URL ID in raw directory
                for ext in ['', '.html', '.htm', '.txt', '.pdf']:
                    potential_file = self.raw_dir / (url_id + ext)
                    if potential_file.exists():
                        source_file = potential_file
                        logger.info(f"Found {url_id} file with extension: {ext}")
                        break
            
            if not source_file:
                logger.info(f"Skipping {url_id}: no file found")
                continue
            
            # Check if file exists
            if not source_file.exists():
                logger.warning(f"Source file not found: {source_file}")
                continue
            
            normalized = self.normalize_file(
                url_id=result['url_id'],
                source_file=source_file
            )
            results.append(normalized)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_chars = sum(r.text_length or 0 for r in results)
        
        logger.info(f"Batch normalization complete: {successful} successful, {failed} failed")
        logger.info(f"Total characters extracted: {total_chars:,}")
        
        return results


def build_phase_1_3_artifact(
    fetch_artifact: dict[str, Any],
    raw_dir: Path,
    text_dir: Path,
    output_path: Path
) -> dict[str, Any]:
    """Execute Phase 1.3 parsing and normalization and emit artifact."""
    
    logger.info(f"Starting Phase 1.3: Parsing and normalization")
    logger.info(f"Raw input directory: {raw_dir}")
    logger.info(f"Text output directory: {text_dir}")
    
    # Initialize normalizer
    normalizer = TextNormalizer(raw_dir=raw_dir, text_dir=text_dir)
    
    # Get fetch results
    fetch_results = fetch_artifact.get('results', [])
    
    # Normalize all files
    normalization_results = normalizer.normalize_batch(fetch_results)
    
    # Prepare artifact payload
    successful_results = [r for r in normalization_results if r.success]
    failed_results = [r for r in normalization_results if not r.success]
    
    payload = {
        "phase": "1.3",
        "input_fetch_artifact": str(output_path.parent / "phase_1_2_fetch.json"),
        "total_files": len(fetch_results),
        "successful_normalizations": len(successful_results),
        "failed_normalizations": len(failed_results),
        "total_characters_extracted": sum(r.text_length or 0 for r in successful_results),
        "raw_dir": str(raw_dir),
        "text_dir": str(text_dir),
        "content_type_stats": {},
        "results": [
            {
                "url_id": r.url_id,
                "source_file": str(r.source_file),
                "success": r.success,
                "text_file": str(r.text_file) if r.text_file else None,
                "text_length": r.text_length,
                "error_message": r.error_message,
                "content_type": r.content_type
            }
            for r in normalization_results
        ]
    }
    
    # Calculate content type statistics
    content_types = {}
    for result in successful_results:
        ct = result.content_type or 'unknown'
        content_types[ct] = content_types.get(ct, 0) + 1
    payload["content_type_stats"] = content_types
    
      
    # Save artifact summary to artifacts directory
    artifact_path = Path("data/artifacts/phase_1_3_normalize.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        import json
        json.dump(payload, f, indent=2, ensure_ascii=True)
        f.write("\n")
    
    logger.info(f"Phase 1.3 complete: {len(successful_results)}/{len(fetch_results)} files normalized")
    logger.info(f"Artifact saved to: {output_path}")
    
    return payload


if __name__ == "__main__":
    # Example usage for testing
    import sys
    from pathlib import Path
    
    if len(sys.argv) != 4:
        print("Usage: python normalize.py <fetch_artifact_json> <raw_dir> <output_path>")
        sys.exit(1)
    
    fetch_artifact_path = Path(sys.argv[1])
    raw_dir = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    text_dir = output_path.parent / "text"
    
    # Load fetch artifact
    with open(fetch_artifact_path, "r") as f:
        import json
        fetch_artifact = json.load(f)
    
    # Run normalization
    artifact = build_phase_1_3_artifact(
        fetch_artifact=fetch_artifact,
        raw_dir=raw_dir,
        text_dir=text_dir,
        output_path=output_path
    )
    
    print(f"Normalization complete: {artifact['successful_normalizations']}/{artifact['total_files']} successful")
    print(f"Total characters extracted: {artifact['total_characters_extracted']:,}")
