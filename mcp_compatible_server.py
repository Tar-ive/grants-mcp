#!/usr/bin/env python3
"""
MCP-compatible server for Cloud Run deployment.
Implements the MCP protocol without relying on FastMCP's built-in HTTP server.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.parse

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_server.config.settings import Settings
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server implementation with Cloud Run compatibility."""
    
    def __init__(self, settings: Settings):
        """Initialize the MCP server."""
        self.settings = settings
        self.cache = InMemoryCache(
            ttl=settings.cache_ttl,
            max_size=settings.max_cache_size
        )
        self.api_client = SimplerGrantsAPIClient(
            api_key=settings.api_key,
            base_url=settings.api_base_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries
        )
        
        # Create server context for real tool functions
        self.context = {
            "cache": self.cache,
            "api_client": self.api_client,
            "search_history": [],
            "settings": settings
        }
        
        # MCP protocol state
        self.initialized = False
        self.client_capabilities = {}
        
        logger.info("🚀 MCP Server initialized successfully")
    
    def run_async(self, coro):
        """Helper to run async functions synchronously."""
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new thread
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(coro)
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=30)  # 30 second timeout
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No loop exists, create one
            return asyncio.run(coro)
    
    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        logger.info(f"Initializing MCP server with protocol version: {params.get('protocolVersion')}")
        
        self.client_capabilities = params.get('capabilities', {})
        self.initialized = True
        
        return {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "tools": {},  # We support tools
                "resources": {},  # We support resources
                "prompts": {}  # We support prompts
            },
            "serverInfo": {
                "name": "grants-mcp",
                "version": "2.0.0",
                "description": "Government grants discovery and analysis MCP server"
            }
        }
    
    def handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        logger.info("Listing available MCP tools")
        
        tools = [
            {
                "name": "opportunity_discovery",
                "description": "Search and analyze grant opportunities with advanced filtering",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Keywords to search for in grants"
                        },
                        "max_results": {
                            "type": "integer", 
                            "description": "Maximum number of results to return",
                            "default": 10
                        },
                        "filters": {
                            "type": "object",
                            "description": "Advanced filtering options",
                            "properties": {
                                "agency": {"type": "string"},
                                "funding_category": {"type": "string"},
                                "min_amount": {"type": "number"},
                                "max_amount": {"type": "number"}
                            }
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "agency_landscape",
                "description": "Analyze agencies and their funding patterns",
                "inputSchema": {
                    "type": "object", 
                    "properties": {
                        "include_opportunities": {
                            "type": "boolean",
                            "description": "Include current opportunities",
                            "default": True
                        },
                        "focus_agencies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific agency codes to analyze"
                        }
                    }
                }
            },
            {
                "name": "funding_trend_scanner", 
                "description": "Analyze funding trends and patterns over time",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "time_window_days": {
                            "type": "integer",
                            "description": "Analysis period in days",
                            "default": 90
                        },
                        "category_filter": {
                            "type": "string",
                            "description": "Focus on specific categories"
                        }
                    }
                }
            }
        ]
        
        return {"tools": tools}
    
    def handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
        
        try:
            if tool_name == "opportunity_discovery":
                return self._call_opportunity_discovery(arguments)
            elif tool_name == "agency_landscape":
                return self._call_agency_landscape(arguments)
            elif tool_name == "funding_trend_scanner":
                return self._call_funding_trend_scanner(arguments)
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Unknown tool: {tool_name}"
                        }
                    ],
                    "isError": True
                }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"Error executing {tool_name}: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    def _call_opportunity_discovery(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call the opportunity discovery tool."""
        try:
            # Import the real tool function
            from mcp_server.tools.discovery.opportunity_discovery_tool import register_opportunity_discovery_tool
            
            # Create a mock FastMCP object to capture the registered function
            class MockMCP:
                def __init__(self):
                    self.tool_func = None
                
                def tool(self, func):
                    self.tool_func = func
                    return func
            
            # Register the tool and capture the function
            mock_mcp = MockMCP()
            register_opportunity_discovery_tool(mock_mcp, self.context)
            
            # Extract parameters
            query = args.get("query")
            max_results = args.get("max_results", 10)
            filters = args.get("filters", {})
            page = 1
            grants_per_page = max_results
            
            # Call the real async function
            result = self.run_async(mock_mcp.tool_func(
                query=query,
                filters=filters,
                max_results=max_results,
                page=page,
                grants_per_page=grants_per_page
            ))
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in opportunity discovery: {e}")
            # Fallback to demo data if API fails
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"# Grant Opportunity Discovery\n\n**Query**: {args.get('query', '')}\n\n**Error**: {str(e)}\n\nFallback: Please check API key configuration or try again later."
                    }
                ]
            }
    
    def _call_agency_landscape(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call the agency landscape tool."""
        try:
            # Import the real tool function
            from mcp_server.tools.discovery.agency_landscape_tool import register_agency_landscape_tool
            
            # Create a mock FastMCP object to capture the registered function
            class MockMCP:
                def __init__(self):
                    self.tool_func = None
                
                def tool(self, func):
                    self.tool_func = func
                    return func
            
            # Register the tool and capture the function
            mock_mcp = MockMCP()
            register_agency_landscape_tool(mock_mcp, self.context)
            
            # Extract parameters
            include_opportunities = args.get("include_opportunities", True)
            focus_agencies = args.get("focus_agencies", [])
            
            # Call the real async function
            result = self.run_async(mock_mcp.tool_func(
                include_opportunities=include_opportunities,
                focus_agencies=focus_agencies
            ))
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in agency landscape: {e}")
            # Fallback to demo data if API fails
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"# Agency Landscape Analysis\n\n**Error**: {str(e)}\n\nFallback: Please check API key configuration or try again later."
                    }
                ]
            }
    
    def _call_funding_trend_scanner(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call the funding trend scanner tool."""
        try:
            # Import the real tool function
            from mcp_server.tools.discovery.funding_trend_scanner_tool import register_funding_trend_scanner_tool
            
            # Create a mock FastMCP object to capture the registered function
            class MockMCP:
                def __init__(self):
                    self.tool_func = None
                
                def tool(self, func):
                    self.tool_func = func
                    return func
            
            # Register the tool and capture the function
            mock_mcp = MockMCP()
            register_funding_trend_scanner_tool(mock_mcp, self.context)
            
            # Extract parameters
            time_window_days = args.get("time_window_days", 90)
            category_filter = args.get("category_filter")
            
            # Call the real async function
            result = self.run_async(mock_mcp.tool_func(
                time_window_days=time_window_days,
                category_filter=category_filter
            ))
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in funding trend scanner: {e}")
            # Fallback to demo data if API fails
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"# Funding Trend Analysis\n\n**Error**: {str(e)}\n\nFallback: Please check API key configuration or try again later."
                    }
                ]
            }
    
    def handle_json_rpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request and return response."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.info(f"Handling JSON-RPC method: {method}")
        
        try:
            if method == "initialize":
                # Always return full initialization response
                result = self.handle_initialize(params)
                
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request_id
                }
            
            elif method == "tools/list":
                result = self.handle_list_tools()
                return {
                    "jsonrpc": "2.0", 
                    "result": result,
                    "id": request_id
                }
            
            elif method == "tools/call":
                result = self.handle_tool_call(params)
                return {
                    "jsonrpc": "2.0",
                    "result": result, 
                    "id": request_id
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": request_id
                }
        
        except Exception as e:
            logger.error(f"Error handling JSON-RPC request: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": request_id
            }


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP protocol."""
    
    def __init__(self, *args, mcp_server: MCPServer = None, **kwargs):
        self.mcp_server = mcp_server
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        logger.info(f"GET request: {self.path}")
        
        if self.path == "/health":
            response = {
                "status": "healthy",
                "service": "grants-mcp",
                "timestamp": datetime.now().isoformat(),
                "message": "MCP-compatible server is running!",
                "mcp_initialized": self.mcp_server.initialized if self.mcp_server else False
            }
        elif self.path == "/":
            response = {
                "service": "grants-mcp",
                "status": "running", 
                "message": "MCP-compatible server deployed successfully!",
                "endpoints": ["/", "/health", "/mcp"],
                "protocol": "MCP (Model Context Protocol)",
                "version": "2.0.0"
            }
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {"error": "Not found", "path": self.path}
            self.wfile.write(json.dumps(error_response).encode())
            return
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_POST(self):
        """Handle POST requests (MCP protocol)."""
        if self.path != "/mcp":
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers() 
            error_response = {"error": "POST endpoint not found", "path": self.path}
            self.wfile.write(json.dumps(error_response).encode())
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            logger.info(f"MCP POST request: {request_data.get('method', 'unknown')}")
            
            # Handle JSON-RPC request
            response_data = self.mcp_server.handle_json_rpc(request_data)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }
            self.wfile.write(json.dumps(error_response).encode())
            
        except Exception as e:
            logger.error(f"POST request error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json') 
            self.end_headers()
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": None
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(format % args)


def main():
    """Main entry point for the MCP-compatible server."""
    try:
        # Load environment variables
        load_dotenv()
        
        logger.info("🚀 Starting MCP-compatible Grants Analysis Server")
        
        # Get API key from environment
        api_key = os.getenv("API_KEY") or os.getenv("SIMPLER_GRANTS_API_KEY")
        if not api_key:
            logger.error("API_KEY or SIMPLER_GRANTS_API_KEY not found in environment variables")
            # For demo purposes, continue without API key
            logger.warning("⚠️ Continuing without API key - using demonstration data")
            api_key = "demo-key"
        
        # Create settings
        settings = Settings(
            api_key=api_key,
            cache_ttl=int(os.getenv("CACHE_TTL", "300")),
            max_cache_size=int(os.getenv("MAX_CACHE_SIZE", "1000")),
            rate_limit_requests=100,
            rate_limit_period=60,
            api_base_url="https://api.simpler.grants.gov/v1"
        )
        
        # Create MCP server
        mcp_server = MCPServer(settings)
        
        # Get port and host for Cloud Run
        port = int(os.getenv("PORT", 8080))
        host = "0.0.0.0"
        
        logger.info(f"🌐 Server configured for {host}:{port}")
        logger.info(f"📊 MCP endpoint: http://{host}:{port}/mcp")
        logger.info(f"❤️ Health endpoint: http://{host}:{port}/health")
        logger.info(f"🏠 Root endpoint: http://{host}:{port}/")
        
        # Create HTTP server with MCP handler
        def handler_factory(*args, **kwargs):
            return MCPRequestHandler(*args, mcp_server=mcp_server, **kwargs)
        
        server = HTTPServer((host, port), handler_factory)
        
        logger.info("✅ MCP-compatible server is ready to accept connections")
        logger.info("🔌 Claude Desktop can now connect to this server!")
        
        server.serve_forever()
        
    except Exception as e:
        logger.error(f"💥 Server startup failed: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()