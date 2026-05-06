"""Test suite for Phase 1 - Data Ingestion Pipeline.

This module contains test cases for all Phase 1 subphases:
- Phase 1.1: URL registry validation and scope filtering
- Phase 1.2: HTTP fetch, retries, robots.txt handling
- Phase 1.3: PDF/HTML → clean text normalization
- Phase 1.4: Manifest and provenance building
- Phase 1.5: Quality gate and handoff to Phase 2
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
