#!/usr/bin/env python3
"""
Simple test server to verify Cloud Run deployment works.
This helps us isolate whether the issue is with the deployment pipeline or the MCP server.
"""

import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        logger.info(f"GET request: {self.path}")
        
        if self.path == "/health":
            response = {
                "status": "healthy",
                "service": "grants-mcp-test",
                "timestamp": datetime.now().isoformat(),
                "message": "Simple test server is working!"
            }
        elif self.path == "/":
            response = {
                "service": "grants-mcp-test", 
                "status": "running",
                "message": "Test server deployed successfully!",
                "endpoints": ["/", "/health"]
            }
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
            return
            
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(format % args)

def main():
    """Start the test server."""
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting test server on {host}:{port}")
    logger.info(f"❤️ Health endpoint: http://{host}:{port}/health")
    logger.info(f"🏠 Root endpoint: http://{host}:{port}/")
    
    server = HTTPServer((host, port), TestHandler)
    
    try:
        logger.info("✅ Server is ready to accept connections")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested")
        server.shutdown()

if __name__ == "__main__":
    main()