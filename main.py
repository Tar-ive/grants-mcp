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
        
        # Get transport mode
        transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
        logger.info(f"Transport mode: {transport}")
        
        # Get API key from environment - support both variable names
        api_key = os.getenv("API_KEY") or os.getenv("SIMPLER_GRANTS_API_KEY")
        if not api_key:
            logger.error("API_KEY or SIMPLER_GRANTS_API_KEY not found in environment variables")
            logger.info("Available environment variables:")
            for key, value in os.environ.items():
                if 'KEY' in key.upper() or 'API' in key.upper():
                    logger.info(f"  {key}={'***' if value else 'None'}")
            sys.exit(1)
        
        # Create settings
        settings = Settings(
            api_key=api_key,
            cache_ttl=int(os.getenv("CACHE_TTL", "300")),  # 5 minutes default
            max_cache_size=int(os.getenv("MAX_CACHE_SIZE", "1000")),  # Max 1000 cached items
            rate_limit_requests=100,
            rate_limit_period=60,
            api_base_url="https://api.simpler.grants.gov/v1"
        )
        
        # Initialize and run the server
        logger.info("🚀 Starting Grants Analysis MCP Server v2.0.0")
        logger.info(f"🔧 Transport: {transport}")
        logger.info(f"🔑 API Key configured: {'Yes' if api_key else 'No'}")
        logger.info(f"💾 Cache TTL: {settings.cache_ttl}s")
        logger.info(f"📊 Max cache size: {settings.max_cache_size}")
        
        logger.info("📦 Creating server instance...")
        server = GrantsAnalysisServer(settings)
        
        logger.info("▶️ Starting server...")
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