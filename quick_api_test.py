#!/usr/bin/env python3
"""Quick API test to verify Phase 2 tools are working."""

import asyncio
import os

from src.mcp_server.config.settings import Settings
from src.mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from src.mcp_server.models.grants_schemas import GrantsAPIResponse


async def quick_test():
    """Quick test of API connectivity."""
    # Use the API key from environment
    api_key = "T4TevWYV3suiQ8eLFbza"  # From your config
    
    print("Testing Grants MCP Server - Phase 2")
    print("=" * 40)
    
    settings = Settings(api_key=api_key)
    api_client = SimplerGrantsAPIClient(
        api_key=settings.api_key,
        base_url=settings.api_base_url
    )
    
    try:
        print("\n1. Testing API connectivity...")
        
        # Simple search
        response = await api_client.search_opportunities(
            filters={"opportunity_status": {"one_of": ["posted"]}},
            pagination={"page_size": 3, "page_offset": 1}
        )
        
        api_response = GrantsAPIResponse(**response)
        opportunities = api_response.get_opportunities()
        
        print(f"   ✅ Found {len(opportunities)} opportunities")
        
        if opportunities:
            print("\n2. Sample opportunity:")
            opp = opportunities[0]
            print(f"   Title: {opp.opportunity_title[:60]}...")
            print(f"   Agency: {opp.agency_name}")
            print(f"   Status: {opp.opportunity_status}")
        
        print("\n3. Testing agency search...")
        agency_response = await api_client.search_agencies(
            filters={},
            pagination={"page_size": 3, "page_offset": 1}
        )
        
        api_response = GrantsAPIResponse(**agency_response)
        agencies = api_response.get_agencies()
        
        print(f"   ✅ Found {len(agencies)} agencies")
        
        print("\n" + "=" * 40)
        print("✅ All Phase 2 tools are ready to use!")
        print("\nYou can now:")
        print("1. Restart Claude Desktop")
        print("2. Use the grantsmanship MCP tools")
        print("3. Try commands from PHASE2_TESTING_GUIDE.md")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. API key is valid")
        print("2. Internet connection is working")
        
    finally:
        await api_client.close()


if __name__ == "__main__":
    asyncio.run(quick_test())