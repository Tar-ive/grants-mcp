#!/usr/bin/env python3
"""
Basic import test to isolate dependency issues.
"""

import logging
import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_basic_imports():
    """Test basic Python imports."""
    try:
        logger.info("✅ Basic logging works")
        import os
        logger.info("✅ os module imported")
        import json
        logger.info("✅ json module imported")
        import asyncio
        logger.info("✅ asyncio module imported")
        return True
    except Exception as e:
        logger.error(f"❌ Basic imports failed: {e}")
        return False

def test_installed_packages():
    """Test if required packages are installed."""
    packages_to_test = [
        'fastmcp',
        'httpx', 
        'pydantic',
        'uvicorn',
        'aiohttp',
        'tenacity'
    ]
    
    for package in packages_to_test:
        try:
            __import__(package)
            logger.info(f"✅ {package} imported successfully")
        except ImportError as e:
            logger.error(f"❌ {package} import failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ {package} unexpected error: {e}")
            return False
    
    return True

def test_fastmcp_import():
    """Test FastMCP specific import."""
    try:
        from fastmcp import FastMCP
        logger.info("✅ FastMCP imported successfully")
        
        # Try to create instance
        mcp = FastMCP(name="test", version="1.0.0")
        logger.info("✅ FastMCP instance created successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ FastMCP import/creation failed: {e}")
        logger.error("Full traceback:")
        traceback.print_exc()
        return False

def test_mcp_server_imports():
    """Test our MCP server imports."""
    try:
        from mcp_server.config.settings import Settings
        logger.info("✅ Settings imported successfully")
        
        from mcp_server.tools.utils.cache_manager import InMemoryCache
        logger.info("✅ InMemoryCache imported successfully")
        
        from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
        logger.info("✅ SimplerGrantsAPIClient imported successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ MCP server imports failed: {e}")
        logger.error("Full traceback:")
        traceback.print_exc()
        return False

def main():
    """Run all import tests."""
    logger.info("🧪 Starting import diagnostics...")
    
    success = True
    
    logger.info("\n📦 Test 1: Basic imports...")
    if not test_basic_imports():
        success = False
    
    logger.info("\n📚 Test 2: Installed packages...")
    if not test_installed_packages():
        success = False
    
    logger.info("\n⚡ Test 3: FastMCP import...")
    if not test_fastmcp_import():
        success = False
    
    logger.info("\n🏗️ Test 4: MCP server imports...")
    if not test_mcp_server_imports():
        success = False
    
    if success:
        logger.info("\n🎉 All import tests passed!")
        
        # Start a simple HTTP server to keep the container running
        logger.info("🌐 Starting simple HTTP server to keep container alive...")
        
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import os
        
        class TestHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    "status": "healthy",
                    "message": "All imports successful!",
                    "fastmcp_working": True
                }
                import json
                self.wfile.write(json.dumps(response, indent=2).encode())
        
        port = int(os.getenv("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), TestHandler)
        logger.info(f"🚀 Server running on port {port}")
        server.serve_forever()
        
    else:
        logger.error("\n❌ Import tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()