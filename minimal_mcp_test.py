#!/usr/bin/env python3
"""
Minimal MCP server test to isolate FastMCP issues.
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if we can import FastMCP and dependencies."""
    try:
        logger.info("Testing FastMCP import...")
        from fastmcp import FastMCP
        logger.info("✅ FastMCP imported successfully")
        
        logger.info("Testing MCP server imports...")
        from mcp_server.config.settings import Settings
        logger.info("✅ Settings imported successfully")
        
        return True
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_fastmcp_basic():
    """Test basic FastMCP functionality."""
    try:
        from fastmcp import FastMCP
        
        logger.info("Creating minimal FastMCP instance...")
        mcp = FastMCP(name="test-server", version="1.0.0")
        
        # Add a simple tool
        @mcp.tool()
        def test_tool() -> str:
            """A simple test tool."""
            return "Hello from test tool!"
        
        # Add health endpoint
        @mcp.get("/health")
        async def health():
            return {"status": "healthy", "message": "Minimal MCP server working"}
        
        logger.info("✅ FastMCP instance created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ FastMCP setup error: {e}")
        return False

def test_http_server():
    """Test starting HTTP server."""
    try:
        from fastmcp import FastMCP
        
        port = int(os.getenv("PORT", 8080))
        host = "0.0.0.0"
        
        logger.info(f"Testing HTTP server startup on {host}:{port}")
        
        mcp = FastMCP(name="test-server", version="1.0.0")
        
        @mcp.get("/health")
        async def health():
            return {"status": "healthy", "message": "HTTP test successful"}
        
        @mcp.get("/")
        async def root():
            return {"message": "Minimal MCP server running", "port": port}
        
        logger.info("Starting HTTP server...")
        # Use a timeout to prevent hanging
        import signal
        
        def timeout_handler(signum, frame):
            logger.info("⏰ Server startup timeout - this is expected for testing")
            raise TimeoutError("Server startup timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 second timeout
        
        try:
            mcp.run(
                transport="http",
                host=host,
                port=port,
                path="/mcp",
                stateless_http=True
            )
        except TimeoutError:
            logger.info("✅ Server started successfully (timed out as expected)")
            return True
        
    except Exception as e:
        logger.error(f"❌ HTTP server error: {e}")
        logger.exception("Full traceback:")
        return False
    finally:
        signal.alarm(0)  # Cancel alarm

def main():
    """Run all tests."""
    logger.info("🧪 Starting MCP server diagnostics...")
    
    # Test 1: Basic imports
    logger.info("\n📦 Test 1: Testing imports...")
    if not test_imports():
        logger.error("❌ Import test failed")
        sys.exit(1)
    
    # Test 2: FastMCP basic functionality
    logger.info("\n⚡ Test 2: Testing FastMCP basic setup...")
    if not test_fastmcp_basic():
        logger.error("❌ FastMCP basic test failed")
        sys.exit(1)
    
    # Test 3: HTTP server startup
    logger.info("\n🌐 Test 3: Testing HTTP server startup...")
    if not test_http_server():
        logger.error("❌ HTTP server test failed")
        sys.exit(1)
    
    logger.info("\n🎉 All tests passed! MCP server should work.")
    
    # If we get here, try to start the actual server
    logger.info("\n🚀 Starting actual minimal MCP server...")
    
    try:
        from fastmcp import FastMCP
        
        port = int(os.getenv("PORT", 8080))
        mcp = FastMCP(name="minimal-mcp", version="1.0.0")
        
        @mcp.tool()
        def hello() -> str:
            """Say hello."""
            return "Hello from minimal MCP server!"
        
        @mcp.get("/health")
        async def health():
            return {"status": "healthy", "server": "minimal-mcp"}
        
        @mcp.get("/")
        async def root():
            return {"message": "Minimal MCP server is running!", "mcp_endpoint": "/mcp"}
        
        logger.info(f"🎯 Starting server on 0.0.0.0:{port}")
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=port,
            path="/mcp",
            stateless_http=True
        )
        
    except Exception as e:
        logger.error(f"💥 Server startup failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)

if __name__ == "__main__":
    main()