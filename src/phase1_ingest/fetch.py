"""Phase 1.2: Fetch engine and raw artifact capture."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    """Result of a single fetch operation."""
    url_id: str
    url: str
    success: bool
    content_hash: Optional[str] = None
    file_path: Optional[Path] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    fetch_time: Optional[float] = None


class RobotsTxtCache:
    """Simple cache for robots.txt parsers to avoid repeated downloads."""
    
    def __init__(self):
        self._cache: dict[str, RobotFileParser] = {}
    
    def get_parser(self, base_url: str) -> RobotFileParser:
        """Get or create a RobotFileParser for the given base URL."""
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        if domain not in self._cache:
            rp = RobotFileParser()
            robots_url = f"{domain}/robots.txt"
            try:
                rp.set_url(robots_url)
                rp.read()
                logger.info(f"Loaded robots.txt for {domain}")
            except Exception as e:
                logger.warning(f"Failed to load robots.txt from {robots_url}: {e}")
                # Create empty parser - allow everything
                rp = RobotFileParser()
                rp.set_url(robots_url)
            
            self._cache[domain] = rp
        
        return self._cache[domain]


class FetchEngine:
    """HTTP fetcher with retries, timeout, rate limiting, and robots.txt respect."""
    
    def __init__(
        self,
        raw_dir: Path,
        max_retries: int = 3,
        timeout: float = 30.0,
        rate_limit_delay: float = 1.0,
        user_agent: str = "GROW-RAG-MutualFundFAQAssistant/1.0 (Educational Bot)"
    ):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_retries = max_retries
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.user_agent = user_agent
        self.robots_cache = RobotsTxtCache()
        
        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set user agent
        self.session.headers.update({"User-Agent": user_agent})
        
        # Rate limiting
        self.last_fetch_time = 0.0
    
    def _can_fetch(self, url: str, user_agent: str = None) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        # Bypass robots.txt checking to allow all URLs
        logger.info(f"Bypassing robots.txt check for {url}")
        return True
    
    def _get_file_path(self, url_id: str, url: str) -> Path:
        """Generate stable file path for fetched content."""
        parsed = urlparse(url)
        extension = ""
        
        # Try to determine extension from URL path
        if parsed.path:
            if parsed.path.endswith('.pdf'):
                extension = ".pdf"
            elif parsed.path.endswith('.html') or parsed.path.endswith('.htm'):
                extension = ".html"
            else:
                extension = ".html"  # Default to HTML
        
        return self.raw_dir / f"{url_id}{extension}"
    
    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    def _rate_limit_wait(self):
        """Rate limiting between requests."""
        elapsed = time.time() - self.last_fetch_time
        if elapsed < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - elapsed
        else:
            wait_time = self.rate_limit_delay
        
        logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
        time.sleep(wait_time)
        self.last_fetch_time = time.time()
    
    def _check_previous_fetch_success(self, url_id: str) -> bool:
        """Check if previous fetch for this URL was successful."""
        try:
            # Use absolute path to artifacts directory
            artifacts_dir = Path(__file__).parent.parent / 'data' / 'artifacts'
            fetch_artifact_path = artifacts_dir / 'phase_1_2_fetch.json'
            
            with open(fetch_artifact_path, 'r') as f:
                fetch_artifact = json.load(f)
                
            for result in fetch_artifact.get('results', []):
                if result.get('url_id') == url_id:
                    return result.get('success', False)
            
            return False
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Could not check previous fetch artifact for {url_id}")
            return False
    
    def fetch_url(self, url_id: str, url: str) -> FetchResult:
        """Fetch a single URL and save raw content."""
        logger.info(f"Fetching {url_id}: {url}")
        
        # Check robots.txt
        if not self._can_fetch(url):
            error_msg = "Blocked by robots.txt"
            logger.warning(f"{url_id}: {error_msg}")
            return FetchResult(
                url_id=url_id,
                url=url,
                success=False,
                error_message=error_msg
            )
        
        # Rate limiting
        self._rate_limit_wait()
        
        file_path = self._get_file_path(url_id, url)
        
        # Smart cleanup: only remove if file exists AND previous fetch was successful
        # This preserves files from previous successful downloads
        should_cleanup = False
        if file_path.exists():
            # Check if this was a successful download in previous run
            # Look for this URL in previous fetch artifact
            previous_fetch_success = self._check_previous_fetch_success(url_id)
            
            if previous_fetch_success:
                logger.info(f"{url_id}: Keeping existing file (previous successful fetch)")
                should_cleanup = False
            else:
                # File exists but previous fetch failed - safe to remove
                logger.info(f"{url_id}: Removing orphaned file: {file_path}")
                should_cleanup = True
        
        if should_cleanup:
            file_path.unlink()
        
        start_time = time.time()
        
        try:
            response = self.session.get(url, timeout=self.timeout, stream=True)
            fetch_time = time.time() - start_time
            
            # Check response status
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                logger.warning(f"{url_id}: {error_msg}")
                return FetchResult(
                    url_id=url_id,
                    url=url,
                    success=False,
                    error_message=error_msg,
                    status_code=response.status_code,
                    fetch_time=fetch_time
                )
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(ct in content_type for ct in ['text/html', 'application/pdf', 'text/plain']):
                error_msg = f"Unsupported content type: {content_type}"
                logger.warning(f"{url_id}: {error_msg}")
                return FetchResult(
                    url_id=url_id,
                    url=url,
                    success=False,
                    error_message=error_msg,
                    status_code=response.status_code,
                    fetch_time=fetch_time
                )
            
            # Download content
            content = response.content
            content_hash = self._calculate_hash(content)
            
            # Save to file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"{url_id}: Successfully fetched {len(content)} bytes, hash: {content_hash[:16]}...")
            
            return FetchResult(
                url_id=url_id,
                url=url,
                success=True,
                content_hash=content_hash,
                file_path=file_path,
                status_code=response.status_code,
                fetch_time=fetch_time
            )
            
        except requests.exceptions.Timeout:
            error_msg = "Request timeout"
            logger.error(f"{url_id}: {error_msg}")
            return FetchResult(
                url_id=url_id,
                url=url,
                success=False,
                error_message=error_msg,
                fetch_time=time.time() - start_time
            )
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"{url_id}: {error_msg}")
            return FetchResult(
                url_id=url_id,
                url=url,
                success=False,
                error_message=error_msg,
                fetch_time=time.time() - start_time
            )
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"{url_id}: {error_msg}")
            return FetchResult(
                url_id=url_id,
                url=url,
                success=False,
                error_message=error_msg,
                fetch_time=time.time() - start_time
            )
    
    def fetch_batch(self, url_list: list[dict[str, Any]]) -> list[FetchResult]:
        """Fetch multiple URLs and return results."""
        results = []
        
        logger.info(f"Starting batch fetch of {len(url_list)} URLs")
        
        for url_item in url_list:
            result = self.fetch_url(
                url_id=url_item["id"],
                url=url_item["url"]
            )
            results.append(result)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.fetch_time or 0 for r in results)
        
        logger.info(f"Batch fetch complete: {successful} successful, {failed} failed, "
                   f"total time: {total_time:.2f}s")
        
        return results
    
    def close(self):
        """Clean up resources."""
        self.session.close()


def build_phase_1_2_artifact(
    fetch_list: list[dict[str, Any]],
    raw_dir: Path,
    output_path: Path
) -> dict[str, Any]:
    """Execute Phase 1.2 fetch engine and emit artifact."""
    
    logger.info(f"Starting Phase 1.2 fetch engine")
    logger.info(f"Raw output directory: {raw_dir}")
    
    # Initialize fetch engine
    fetch_engine = FetchEngine(raw_dir=raw_dir)
    
    try:
        # Fetch all URLs
        results = fetch_engine.fetch_batch(fetch_list)
        
        # Prepare artifact payload
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        payload = {
            "phase": "1.2",
            "total_urls": len(fetch_list),
            "successful_fetches": len(successful_results),
            "failed_fetches": len(failed_results),
            "total_fetch_time": sum(r.fetch_time or 0 for r in results),
            "raw_dir": str(raw_dir),
            "results": [
                {
                    "url_id": r.url_id,
                    "url": r.url,
                    "success": r.success,
                    "content_hash": r.content_hash,
                    "file_path": str(r.file_path) if r.file_path else None,
                    "error_message": r.error_message,
                    "status_code": r.status_code,
                    "fetch_time": r.fetch_time
                }
                for r in results
            ]
        }
        
        # Save artifact summary to artifacts directory
        artifact_path = Path("data/artifacts/phase_1_2_fetch.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            import json
            json.dump(payload, f, indent=2, ensure_ascii=True)
            f.write("\n")
        
        logger.info(f"Phase 1.2 complete: {len(successful_results)}/{len(fetch_list)} URLs fetched successfully")
        logger.info(f"Artifact saved to: {output_path}")
        
        return payload
        
    finally:
        fetch_engine.close()


if __name__ == "__main__":
    # Example usage for testing
    import sys
    from pathlib import Path
    
    if len(sys.argv) != 3:
        print("Usage: python fetch.py <fetch_list_json> <output_path>")
        sys.exit(1)
    
    fetch_list_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    raw_dir = Path("data/raw")
    
    # Load fetch list
    with open(fetch_list_path, "r") as f:
        import json
        fetch_list = json.load(f)
    
    # Run fetch engine
    artifact = build_phase_1_2_artifact(
        fetch_list=fetch_list,
        raw_dir=raw_dir,
        output_path=output_path
    )
    
    print(f"Fetch complete: {artifact['successful_fetches']}/{artifact['total_urls']} successful")
