#!/usr/bin/env python3
"""
Fixed MCP server using uvicorn for Cloud Run compatibility.
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
    """Main entry point using uvicorn for Cloud Run."""
    try:
        # Load environment variables
        load_dotenv()
        
        logger.info("🚀 Starting Fixed Grants Analysis MCP Server")
        
        # Get API key from environment
        api_key = os.getenv("API_KEY") or os.getenv("SIMPLER_GRANTS_API_KEY")
        if not api_key:
            logger.error("API_KEY or SIMPLER_GRANTS_API_KEY not found in environment variables")
            sys.exit(1)
        
        # Create settings
        settings = Settings(
            api_key=api_key,
            cache_ttl=int(os.getenv("CACHE_TTL", "300")),
            max_cache_size=int(os.getenv("MAX_CACHE_SIZE", "1000")),
            rate_limit_requests=100,
            rate_limit_period=60,
            api_base_url="https://api.simpler.grants.gov/v1"
        )
        
        logger.info("📦 Creating server instance...")
        server = GrantsAnalysisServer(settings)
        
        # Get port from environment (Cloud Run sets this)
        port = int(os.getenv("PORT", 8080))
        host = "0.0.0.0"
        
        logger.info(f"🌐 Server configured for {host}:{port}")
        
        # Try using FastMCP with explicit configuration
        logger.info("▶️ Starting FastMCP server with explicit config...")
        
        # Add health check endpoint
        @server.mcp.get("/health")
        async def health_check():
            """Health check endpoint for Cloud Run."""
            return {
                "status": "healthy",
                "service": "grants-mcp-fixed",
                "message": "Fixed MCP server is running!"
            }

        # Add root path handler
        @server.mcp.get("/")
        async def root_handler():
            """Root path handler."""
            return {
                "service": "grants-mcp-fixed",
                "status": "running",
                "mcp_endpoint": "/mcp",
                "health_endpoint": "/health"
            }
        
        # Use FastMCP's run method but with better error handling
        try:
            server.mcp.run(
                transport="http",
                host=host,
                port=port,
                path="/mcp",
                # Try different settings
                reload=False,  # Disable reload for production
                log_level="info"
            )
        except Exception as server_error:
            logger.error(f"FastMCP server failed: {server_error}")
            logger.exception("FastMCP error details:")
            
            # Fallback to basic HTTP server
            logger.info("🔄 Falling back to basic HTTP server...")
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import json
            
            class FallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/health":
                        response = {"status": "healthy", "message": "Fallback server running"}
                    else:
                        response = {"error": "FastMCP failed to start", "fallback": True}
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
            
            fallback_server = HTTPServer((host, port), FallbackHandler)
            logger.info(f"🆘 Fallback server running on {host}:{port}")
            fallback_server.serve_forever()
        
    except Exception as e:
        logger.error(f"💥 Server startup failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()