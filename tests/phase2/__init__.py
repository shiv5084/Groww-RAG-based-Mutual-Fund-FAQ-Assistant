"""Test suite for Phase 2 - Chunking, metadata, and indexing preparation.

This module contains test cases for all Phase 2 components:
- Chunking strategies (section-aware, fixed-window, hybrid)
- Chunk metadata and schema validation
- Configuration management
- CLI functionality
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
