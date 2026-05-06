#!/usr/bin/env python3
"""
Full Pipeline Scheduler

Orchestrates the complete RAG pipeline end-to-end:
  Phase 1: Fetch → Phase 2: Chunk → Phase 3: Index → Phase 4-5: Validate

Usage:
    python src/scripts/run_scheduler.py --full
    python src/scripts/run_scheduler.py --phases fetch,chunk,index
    python src/scripts/run_scheduler.py --schedule daily
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("scheduler")

# Add file handler for persistent logs
LOG_DIR = Path("logs/scheduler")
LOG_DIR.mkdir(parents=True, exist_ok=True)


class PipelineScheduler:
    """Orchestrates the full RAG pipeline with error handling and reporting."""
    
    PHASES = {
        "fetch": {
            "script": "src/scripts/run_fetch.py",
            "description": "Phase 1: Fetch and normalize",
            "args": ["--registry", "config/url_registry.yaml"],
        },
        "chunk": {
            "script": "src/scripts/run_chunk.py",
            "description": "Phase 2: Chunk and metadata",
            "args": ["--manifest", "data/processed/manifest.json", "--output", "data/chunks/chunks.jsonl"],
        },
        "index": {
            "script": "src/scripts/run_index.py",
            "description": "Phase 3: Embeddings and indexing",
            "args": ["--chunks", "data/chunks/chunks.jsonl", "--output", "data/index", "--reset"],
        },
        "validate": {
            "script": "src/phase9/evaluation/evaluator.py",
            "description": "Phase 9: Validation and evaluation",
            "args": [],
        },
    }
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path.cwd()
        self.results = {}
        self.start_time = None
        self.log_file = LOG_DIR / f"scheduler_{datetime.now():%Y%m%d_%H%M%S}.log"
        
        # Add file handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        logger.addHandler(file_handler)
    
    def run_phase(self, phase_name: str, extra_args: Optional[List[str]] = None) -> dict:
        """Run a single phase and capture results."""
        phase_config = self.PHASES.get(phase_name)
        if not phase_config:
            raise ValueError(f"Unknown phase: {phase_name}")
        
        script_path = self.base_dir / phase_config["script"]
        if not script_path.exists():
            logger.warning(f"Script not found: {script_path}, skipping {phase_name}")
            return {"status": "skipped", "reason": "script_not_found"}
        
        cmd = [sys.executable, str(script_path)] + phase_config["args"]
        if extra_args:
            cmd.extend(extra_args)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {phase_config['description']}")
        logger.info(f"Command: {' '.join(cmd)}")
        logger.info(f"{'='*60}")
        
        phase_start = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=3600,  # 1 hour timeout per phase
            )
            
            elapsed = time.time() - phase_start
            
            # Log output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    logger.info(f"  {line}")
            
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    if "error" in line.lower() or "exception" in line.lower():
                        logger.error(f"  {line}")
                    else:
                        logger.warning(f"  {line}")
            
            if result.returncode == 0:
                logger.info(f"  Phase '{phase_name}' completed in {elapsed:.1f}s")
                return {
                    "status": "success",
                    "elapsed_seconds": elapsed,
                    "returncode": result.returncode,
                }
            else:
                logger.error(f"  Phase '{phase_name}' failed with code {result.returncode}")
                return {
                    "status": "failed",
                    "elapsed_seconds": elapsed,
                    "returncode": result.returncode,
                    "stderr": result.stderr[:500],
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"  Phase '{phase_name}' timed out after 1 hour")
            return {"status": "timeout", "elapsed_seconds": 3600}
        except Exception as e:
            logger.error(f"  Phase '{phase_name}' error: {e}")
            return {"status": "error", "error": str(e)}
    
    def run_pipeline(self, phases: Optional[List[str]] = None) -> dict:
        """Run the full or partial pipeline."""
        self.start_time = time.time()
        phases = phases or ["fetch", "chunk", "index", "validate"]
        
        logger.info(f"\n{'#'*60}")
        logger.info(f"# Pipeline Scheduler Started")
        logger.info(f"# Timestamp: {datetime.now().isoformat()}")
        logger.info(f"# Phases: {', '.join(phases)}")
        logger.info(f"# Base Dir: {self.base_dir}")
        logger.info(f"{'#'*60}\n")
        
        # Track overall status
        overall_status = "success"
        
        for phase_name in phases:
            result = self.run_phase(phase_name)
            self.results[phase_name] = result
            
            # Stop pipeline on failure (unless it's validate)
            if result["status"] != "success" and phase_name != "validate":
                logger.error(f"Pipeline halted due to {phase_name} failure")
                overall_status = "failed"
                break
        
        total_elapsed = time.time() - self.start_time
        
        # Generate report
        report = self._generate_report(total_elapsed, overall_status)
        
        logger.info(f"\n{'#'*60}")
        logger.info(f"# Pipeline Scheduler Complete")
        logger.info(f"# Status: {overall_status.upper()}")
        logger.info(f"# Total Time: {total_elapsed:.1f}s")
        logger.info(f"# Log File: {self.log_file}")
        logger.info(f"{'#'*60}\n")
        
        return report
    
    def _generate_report(self, total_elapsed: float, status: str) -> dict:
        """Generate execution report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "total_elapsed_seconds": total_elapsed,
            "phases": self.results,
            "summary": {
                "total_phases": len(self.results),
                "successful": sum(1 for r in self.results.values() if r.get("status") == "success"),
                "failed": sum(1 for r in self.results.values() if r.get("status") not in ["success", "skipped"]),
                "skipped": sum(1 for r in self.results.values() if r.get("status") == "skipped"),
            },
        }
        
        # Save report
        report_file = self.base_dir / "data/artifacts/scheduler_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to: {report_file}")
        return report


def main():
    parser = argparse.ArgumentParser(
        description="Full Pipeline Scheduler for RAG Mutual Fund FAQ Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python src/scripts/run_scheduler.py --full
  
  # Run specific phases
  python src/scripts/run_scheduler.py --phases fetch,chunk
  
  # Run validation only
  python src/scripts/run_scheduler.py --phases validate
        """
    )
    
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run complete pipeline (fetch → chunk → index → validate)"
    )
    parser.add_argument(
        "--phases",
        type=str,
        help="Comma-separated list of phases to run (fetch,chunk,index,validate)"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path.cwd(),
        help="Base directory for the project"
    )
    
    args = parser.parse_args()
    
    # Determine phases to run
    if args.full:
        phases = ["fetch", "chunk", "index", "validate"]
    elif args.phases:
        phases = [p.strip() for p in args.phases.split(",")]
    else:
        # Default: run fetch + chunk + index (skip validation)
        phases = ["fetch", "chunk", "index"]
    
    # Validate phase names
    valid_phases = set(PipelineScheduler.PHASES.keys())
    invalid = [p for p in phases if p not in valid_phases]
    if invalid:
        logger.error(f"Invalid phases: {invalid}. Valid: {', '.join(valid_phases)}")
        sys.exit(1)
    
    # Run scheduler
    scheduler = PipelineScheduler(base_dir=args.base_dir)
    report = scheduler.run_pipeline(phases=phases)
    
    # Exit with appropriate code
    if report["status"] == "success":
        logger.info("Pipeline completed successfully!")
        sys.exit(0)
    else:
        logger.error("Pipeline completed with failures")
        sys.exit(1)


if __name__ == "__main__":
    main()
