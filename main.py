#!/usr/bin/env python3
"""
Grants Analysis MCP Server - Main Entry Point

A comprehensive MCP server for discovering and analyzing government grants
using the Simpler Grants API.
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_server.server import GrantsAnalysisServer
from mcp_server.config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the MCP server."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get API key from environment
        api_key = os.getenv("API_KEY")
        if not api_key:
            logger.error("API_KEY not found in environment variables")
            sys.exit(1)
        
        # Create settings
        settings = Settings(
            api_key=api_key,
            cache_ttl=300,  # 5 minutes
            max_cache_size=1000,  # Max 1000 cached items
            rate_limit_requests=100,
            rate_limit_period=60,
            api_base_url="https://api.simpler.grants.gov/v1"
        )
        
        # Initialize and run the server
        logger.info("Starting Grants Analysis MCP Server v2.0.0")
        server = GrantsAnalysisServer(settings)
        
        # Run the server synchronously (FastMCP handles its own async)
        server.run_sync()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()