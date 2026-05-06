#!/usr/bin/env python3
"""
Phase 7 - Backend API Service Startup Script.

Launches the FastAPI server for the Mutual Fund FAQ Assistant.
Provides command-line options for configuration and deployment.
"""

import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import uvicorn
    from phase7_api.main import app
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required dependencies:")
    print("pip install fastapi uvicorn pydantic python-dotenv")
    sys.exit(1)


def setup_logging(log_level: str = "info"):
    """Setup logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    # Configure root logger to console only (for Phase 5 components)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Override any existing configuration
    )
    
    # Configure API-specific logger to also write to file
    api_logger = logging.getLogger('phase7_api')
    api_logger.setLevel(numeric_level)
    
    # Remove any existing handlers
    api_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    api_logger.addHandler(console_handler)
    
    # Prevent API logs from propagating to root logger
    api_logger.propagate = False


def check_environment():
    """Check if environment is properly configured."""
    warnings = []
    
    # Check for .env file
    env_file = Path('.env')
    if not env_file.exists():
        warnings.append("No .env file found - using environment variables")
    
    # Check for required directories
    required_dirs = ['data/sessions', 'data/artifacts']
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            warnings.append(f"Required directory missing: {dir_path}")
    
    # Check for Phase 5 components
    try:
        from phase5_generation.generation.generator import AnswerGenerator
        from phase5_generation.formatting.validator import OutputValidator
    except ImportError as e:
        warnings.append(f"Phase 5 components not available: {e}")
    
    # Check for Phase 6 components
    try:
        from phase6_sessions.sqlite_store import SQLiteSessionStore
    except ImportError as e:
        warnings.append(f"Phase 6 components not available: {e}")
    
    return warnings


def create_directories():
    """Create required directories if they don't exist."""
    directories = [
        'data/sessions',
        'data/artifacts'
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


def main():
    """Main entry point for API server."""
    parser = argparse.ArgumentParser(
        description="Phase 7 - Mutual Fund FAQ Assistant API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_phase7_api.py                          # Start with defaults
  python run_phase7_api.py --host 0.0.0.0 --port 8000
  python run_phase7_api.py --reload --log-level debug
  python run_phase7_api.py --workers 4
        """
    )
    
    # Server configuration
    parser.add_argument(
        "--host", 
        default="127.0.0.1", 
        help="Host to bind the server to (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind the server to (default: 8000)"
    )
    
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--workers", 
        type=int, 
        default=1, 
        help="Number of worker processes (default: 1)"
    )
    
    parser.add_argument(
        "--log-level", 
        choices=["debug", "info", "warning", "error", "critical"], 
        default="info", 
        help="Logging level (default: info)"
    )
    
    parser.add_argument(
        "--access-log", 
        action="store_true", 
        help="Enable access logging"
    )
    
    parser.add_argument(
        "--ssl-keyfile", 
        help="Path to SSL private key file"
    )
    
    parser.add_argument(
        "--ssl-certfile", 
        help="Path to SSL certificate file"
    )
    
    # Application configuration
    parser.add_argument(
        "--db-path", 
        default="data/sessions/threads.db", 
        help="Path to SQLite database (default: data/sessions/threads.db)"
    )
    
    parser.add_argument(
        "--max-history", 
        type=int, 
        default=10, 
        help="Maximum message history length (default: 10)"
    )
    
    parser.add_argument(
        "--session-timeout", 
        type=int, 
        default=60, 
        help="Session timeout in minutes (default: 60)"
    )
    
    # Utility commands
    parser.add_argument(
        "--check-env", 
        action="store_true", 
        help="Check environment configuration"
    )
    
    parser.add_argument(
        "--create-dirs", 
        action="store_true", 
        help="Create required directories"
    )
    
    parser.add_argument(
        "--version", 
        action="store_true", 
        help="Show version information"
    )
    
    args = parser.parse_args()
    
    # Handle utility commands
    if args.version:
        print("Phase 7 API Server v1.0.0")
        print("Mutual Fund FAQ Assistant")
        return
    
    if args.check_env:
        print("Checking environment configuration...")
        warnings = check_environment()
        
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("Environment configuration looks good!")
        return
    
    if args.create_dirs:
        print("Creating required directories...")
        create_directories()
        print("Directories created successfully!")
        return
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Environment check
    warnings = check_environment()
    if warnings:
        logger.warning("Environment warnings detected:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    # Create directories
    create_directories()
    
    # Set environment variables for configuration
    os.environ["PHASE7_DB_PATH"] = args.db_path
    os.environ["PHASE7_MAX_HISTORY"] = str(args.max_history)
    os.environ["PHASE7_SESSION_TIMEOUT"] = str(args.session_timeout)
    
    # Configure uvicorn
    config = {
        "app": app,
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": args.access_log,
    }
    
    # SSL configuration
    if args.ssl_keyfile and args.ssl_certfile:
        config["ssl_keyfile"] = args.ssl_keyfile
        config["ssl_certfile"] = args.ssl_certfile
        protocol = "https"
    else:
        protocol = "http"
    
    # Worker configuration
    if args.workers > 1:
        config["workers"] = args.workers
        if args.reload:
            logger.warning("Auto-reload is not compatible with multiple workers")
            args.reload = False
    
    # Reload configuration
    if args.reload:
        config["reload"] = True
        config["reload_dirs"] = ["src"]
    
    # Print startup information
    print("=" * 60)
    print("Phase 7 - Mutual Fund FAQ Assistant API Server")
    print("=" * 60)
    print(f"Version: 1.0.0")
    print(f"Protocol: {protocol.upper()}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Workers: {args.workers}")
    print(f"Log Level: {args.log_level}")
    print(f"Database: {args.db_path}")
    print(f"Max History: {args.max_history} messages")
    print(f"Session Timeout: {args.session_timeout} minutes")
    print("=" * 60)
    print(f"API Documentation: {protocol}://{args.host}:{args.port}/docs")
    print(f"ReDoc Documentation: {protocol}://{args.host}:{args.port}/redoc")
    print(f"Health Check: {protocol}://{args.host}:{args.port}/api/v1/health")
    print("=" * 60)
    
    # Start server
    try:
        logger.info(f"Starting Phase 7 API server on {protocol}://{args.host}:{args.port}")
        uvicorn.run(**config)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
