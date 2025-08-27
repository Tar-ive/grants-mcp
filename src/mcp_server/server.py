"""Main MCP server implementation for Grants Analysis."""

import logging
import sys
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from mcp_server.config.settings import Settings
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient

logger = logging.getLogger(__name__)


class GrantsAnalysisServer:
    """
    Main server class for the Grants Analysis MCP.
    
    Coordinates all tools, resources, and prompts for comprehensive
    grants discovery and analysis.
    """
    
    def __init__(self, settings: Settings):
        """Initialize the Grants Analysis Server."""
        self.settings = settings
        self.settings.validate()
        
        # Initialize FastMCP
        self.mcp = FastMCP(
            name=settings.server_name,
            version=settings.server_version
        )
        
        # Initialize components
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
        
        # Store server context for tools
        self.context = {
            "cache": self.cache,
            "api_client": self.api_client,
            "settings": settings,
            "search_history": [],  # Simple search history tracking
        }
        
        # Register all components
        self._register_tools()
        self._register_resources()
        self._register_prompts()
        
        logger.info(f"Initialized {settings.server_name} v{settings.server_version}")
    
    def _register_tools(self):
        """Register all available tools with the MCP server."""
        # Import and register tools
        from mcp_server.tools.discovery.opportunity_discovery_tool import (
            register_opportunity_discovery_tool
        )
        
        # Register each tool with the server context
        register_opportunity_discovery_tool(self.mcp, self.context)
        
        # Future tools will be registered here:
        # register_agency_landscape_tool(self.mcp, self.context)
        # register_funding_trend_scanner_tool(self.mcp, self.context)
        # etc.
        
        logger.info("Registered all tools")
    
    def _register_resources(self):
        """Register all available resources with the MCP server."""
        
        @self.mcp.resource("grants://api/status")
        async def get_api_status() -> str:
            """Get current API status and health information."""
            try:
                # Check API health
                health_status = await self.api_client.check_health()
                
                return {
                    "api_health": {
                        "status": health_status.get("status", "unknown"),
                        "response_time_ms": health_status.get("response_time", -1),
                        "rate_limit_remaining": self.api_client.rate_limit_remaining,
                        "rate_limit_reset": self.api_client.rate_limit_reset,
                    },
                    "cache_stats": self.cache.get_stats(),
                    "search_history_count": len(self.context["search_history"]),
                }
            except Exception as e:
                logger.error(f"Error getting API status: {e}")
                return {"error": str(e)}
        
        @self.mcp.resource("grants://cache/stats")
        async def get_cache_stats() -> str:
            """Get cache statistics."""
            return self.cache.get_stats()
        
        @self.mcp.resource("grants://search/history")
        async def get_search_history() -> str:
            """Get recent search history."""
            # Return last 20 searches
            return {
                "searches": self.context["search_history"][-20:],
                "total_searches": len(self.context["search_history"])
            }
        
        logger.info("Registered all resources")
    
    def _register_prompts(self):
        """Register all available prompts with the MCP server."""
        
        @self.mcp.prompt("landscape_analysis")
        async def landscape_analysis_prompt(domain: str = "") -> str:
            """Generate a prompt for comprehensive landscape analysis."""
            base_prompt = """Analyze the grants landscape for the specified domain.
            
Use the following workflow:
1. Search for opportunities using opportunity_discovery tool
2. Analyze agency patterns with agency_landscape tool
3. Identify funding trends with funding_trend_scanner tool
4. Calculate opportunity density for top prospects
5. Generate strategic recommendations"""
            
            if domain:
                return f"{base_prompt}\n\nDomain of focus: {domain}"
            return base_prompt
        
        @self.mcp.prompt("quick_search")
        async def quick_search_prompt(keywords: str = "") -> str:
            """Generate a prompt for quick opportunity search."""
            if keywords:
                return f"Search for grant opportunities related to: {keywords}"
            return "Search for grant opportunities (please specify keywords)"
        
        logger.info("Registered all prompts")
    
    def run_sync(self):
        """Run the MCP server synchronously."""
        try:
            logger.info("Starting MCP server...")
            
            # FastMCP handles its own event loop for stdio transport
            self.mcp.run()
            
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            # Cleanup (sync version)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.api_client.close())
                else:
                    loop.run_until_complete(self.api_client.close())
            except:
                pass  # Best effort cleanup
            logger.info("Server shutdown complete")
    
    async def run(self):
        """Run the MCP server asynchronously (for testing)."""
        try:
            logger.info("Starting MCP server...")
            
            # The FastMCP server handles the stdio transport automatically
            await self.mcp.run()
            
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            # Cleanup
            await self.api_client.close()
            logger.info("Server shutdown complete")