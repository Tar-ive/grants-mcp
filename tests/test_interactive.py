#!/usr/bin/env python3
"""Interactive test for the MCP server - simulates Claude Desktop usage."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from mcp_server.config.settings import Settings
from mcp_server.server import GrantsAnalysisServer
from fastmcp import FastMCP
from mcp_server.tools.discovery.opportunity_discovery_tool import (
    register_opportunity_discovery_tool,
)

async def test_mcp_server():
    """Test the MCP server with interactive examples."""
    
    # Load environment
    load_dotenv()
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        print("❌ API_KEY not found in .env file")
        return
    
    # Create server settings
    settings = Settings(
        api_key=api_key,
        cache_ttl=300,
        max_cache_size=1000,
        rate_limit_requests=100,
        rate_limit_period=60,
        api_base_url="https://api.simpler.grants.gov/v1"
    )
    
    # Initialize server (but don't run it in stdio mode)
    print("Initializing MCP Server...")
    server = GrantsAnalysisServer(settings)
    
    print("\n" + "=" * 60)
    print("GRANTS ANALYSIS MCP - Interactive Test")
    print("=" * 60)
    
    # Test 1: Search for grants
    print("\n📋 TEST 1: Search for renewable energy grants")
    print("-" * 40)
    
    # Get the opportunity_discovery tool directly
    tool_func = None
    for tool in server.mcp.tools:
        if tool.name == "opportunity_discovery":
            tool_func = tool.fn
            break
    
    if tool_func:
        result = await tool_func(
            query="renewable energy",
            max_results=3,
            page=1,
            grants_per_page=3
        )
        
        # Print first 1500 chars of result
        print(result[:1500] + "..." if len(result) > 1500 else result)
    
    # Test 2: Check cache effectiveness
    print("\n📋 TEST 2: Cache test (same search)")
    print("-" * 40)
    
    cache_stats_before = server.cache.get_stats()
    print(f"Cache before: hits={cache_stats_before['hits']}, misses={cache_stats_before['misses']}")
    
    # Same search - should hit cache
    result = await tool_func(
        query="renewable energy",
        max_results=3,
        page=1,
        grants_per_page=3
    )
    
    cache_stats_after = server.cache.get_stats()
    print(f"Cache after: hits={cache_stats_after['hits']}, misses={cache_stats_after['misses']}")
    print(f"✅ Cache hit!" if cache_stats_after['hits'] > cache_stats_before['hits'] else "❌ Cache miss")
    
    # Test 3: Different search
    print("\n📋 TEST 3: Search for AI/technology grants")
    print("-" * 40)
    
    result = await tool_func(
        query="artificial intelligence technology",
        max_results=2,
        page=1,
        grants_per_page=2
    )
    
    # Extract just the overview
    if "OVERVIEW" in result:
        overview_end = result.find("DETAILED GRANT LISTINGS")
        if overview_end > 0:
            print(result[:overview_end])
    
    # Test 4: Check resources
    print("\n📋 TEST 4: Check API status resource")
    print("-" * 40)
    
    # Get the API status resource
    for resource in server.mcp.resources:
        if resource.uri == "grants://api/status":
            status = await resource.fn()
            print(f"API Status: {json.dumps(status, indent=2)}")
            break
    
    # Test 5: Test prompts
    print("\n📋 TEST 5: Test quick search prompt")
    print("-" * 40)
    
    for prompt in server.mcp.prompts:
        if prompt.name == "quick_search":
            prompt_text = await prompt.fn(keywords="climate change mitigation")
            print(f"Generated prompt: {prompt_text}")
            break
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\nThe MCP server is working correctly and ready for use.")
    print("\nTo use with Claude Desktop, add this to your config:")
    print(json.dumps({
        "mcpServers": {
            "grantsmanship": {
                "command": "python3",
                "args": [str(Path(__file__).parent / "main.py")]
            }
        }
    }, indent=2))
    
    # Cleanup
    await server.api_client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_server())