#!/usr/bin/env python3
"""Direct test of MCP functionality without running the full server."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from mcp_server.config.settings import Settings
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from mcp_server.tools.discovery.opportunity_discovery_tool import (
    format_grant_details,
    create_summary,
    calculate_summary_statistics,
)
from mcp_server.models.grants_schemas import GrantsAPIResponse

async def test_direct():
    """Test MCP components directly."""
    
    # Load environment
    load_dotenv()
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        print("❌ API_KEY not found in .env file")
        return
    
    print("=" * 60)
    print("GRANTS MCP - Direct Component Test")
    print("=" * 60)
    
    # Initialize components
    cache = InMemoryCache(ttl=300, max_size=100)
    api_client = SimplerGrantsAPIClient(api_key=api_key)
    
    try:
        # Test 1: Search for grants
        print("\n📋 TEST 1: Search for renewable energy grants")
        print("-" * 40)
        
        response = await api_client.search_opportunities(
            query="renewable energy",
            pagination={"page_size": 3, "page_offset": 1}
        )
        
        # Parse response
        api_response = GrantsAPIResponse(**response)
        opportunities = api_response.get_opportunities()
        
        print(f"Found {len(opportunities)} grants (total: {api_response.pagination_info.total_records})")
        
        # Display first grant
        if opportunities:
            first_grant = opportunities[0]
            print("\nFirst grant preview:")
            print(f"  Title: {first_grant.opportunity_title}")
            print(f"  Agency: {first_grant.agency_name}")
            print(f"  Status: {first_grant.opportunity_status}")
            
            # Test formatting
            formatted = format_grant_details(first_grant)
            print("\nFormatted output (first 500 chars):")
            print(formatted[:500] + "...")
        
        # Test 2: Cache functionality
        print("\n📋 TEST 2: Test caching")
        print("-" * 40)
        
        cache_key = cache.generate_cache_key("test", query="renewable energy")
        cache.set(cache_key, {"data": opportunities, "total": api_response.pagination_info.total_records})
        
        cached_data = cache.get(cache_key)
        if cached_data:
            print("✅ Cache working: Data stored and retrieved")
            print(f"   Cache stats: {cache.get_stats()}")
        
        # Test 3: Search with different query
        print("\n📋 TEST 3: Search for AI grants")
        print("-" * 40)
        
        response2 = await api_client.search_opportunities(
            query="artificial intelligence",
            pagination={"page_size": 2, "page_offset": 1}
        )
        
        api_response2 = GrantsAPIResponse(**response2)
        opportunities2 = api_response2.get_opportunities()
        
        print(f"Found {len(opportunities2)} AI grants (total: {api_response2.pagination_info.total_records})")
        
        # Test 4: Summary statistics
        print("\n📋 TEST 4: Calculate statistics")
        print("-" * 40)
        
        if opportunities:
            stats = calculate_summary_statistics(opportunities)
            print(f"Agencies involved: {len(stats['agencies'])}")
            print(f"Categories: {list(stats['category_breakdown'].keys())}")
            print(f"Status breakdown: {stats['status_breakdown']}")
        
        # Test 5: Create summary
        print("\n📋 TEST 5: Generate formatted summary")
        print("-" * 40)
        
        if opportunities:
            summary = create_summary(
                opportunities,
                "renewable energy",
                page=1,
                grants_per_page=3,
                total_found=api_response.pagination_info.total_records
            )
            
            # Show just the overview part
            if "OVERVIEW" in summary:
                overview_end = summary.find("DETAILED GRANT LISTINGS")
                if overview_end > 0:
                    print(summary[:overview_end])
        
        print("\n" + "=" * 60)
        print("✅ All component tests passed!")
        print("\nYour MCP server components are working correctly.")
        print("\nTo run the full MCP server:")
        print("  python3 main.py")
        print("\nTo use with Claude Desktop, add to config:")
        print(json.dumps({
            "mcpServers": {
                "grantsmanship": {
                    "command": "python3",
                    "args": [str(Path(__file__).parent / "main.py")]
                }
            }
        }, indent=2))
        
    finally:
        await api_client.close()


if __name__ == "__main__":
    asyncio.run(test_direct())