#!/usr/bin/env python3
"""Basic test to verify the Python MCP implementation works."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from mcp_server.config.settings import Settings
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient


async def test_basic_functionality():
    """Test basic components work."""
    print("Testing Grants MCP Python Implementation...")
    print("=" * 50)
    
    # Load environment
    load_dotenv()
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        print("❌ API_KEY not found in .env file")
        print("   Please create a .env file with: API_KEY=your_key")
        return False
    
    print("✅ Environment loaded")
    
    # Test cache
    print("\nTesting Cache...")
    cache = InMemoryCache(ttl=60, max_size=10)
    cache.set("test_key", {"data": "test_value"})
    result = cache.get("test_key")
    
    if result == {"data": "test_value"}:
        print("✅ Cache working correctly")
    else:
        print("❌ Cache test failed")
        return False
    
    # Test cache statistics
    stats = cache.get_stats()
    print(f"   Cache stats: {stats}")
    
    # Test API client (if API key is real)
    print("\nTesting API Client...")
    client = SimplerGrantsAPIClient(api_key=api_key)
    
    try:
        # Check health
        health = await client.check_health()
        print(f"✅ API health check: {health['status']}")
        
        # Try a minimal search
        print("\nTesting API Search...")
        response = await client.search_opportunities(
            query="technology",
            pagination={"page_size": 2, "page_offset": 1}
        )
        
        if response and "data" in response:
            count = len(response["data"])
            total = response.get("pagination_info", {}).get("total_records", 0)
            print(f"✅ API search successful: Found {count} results (total: {total})")
            
            # Show first result if available
            if response["data"]:
                first = response["data"][0]
                print(f"\n   First result:")
                print(f"   - Title: {first.get('opportunity_title', 'N/A')}")
                print(f"   - Number: {first.get('opportunity_number', 'N/A')}")
                print(f"   - Agency: {first.get('agency_name', 'N/A')}")
                print(f"   - Status: {first.get('opportunity_status', 'N/A')}")
        else:
            print("⚠️  API returned no data (might be rate limited or invalid key)")
    
    except Exception as e:
        print(f"⚠️  API test failed: {e}")
        print("   This might be expected if using a test API key")
    
    finally:
        await client.close()
    
    print("\n" + "=" * 50)
    print("Basic functionality tests completed!")
    print("\nNext steps:")
    print("1. Run unit tests: make test-unit")
    print("2. Run integration tests: make test-integration")
    print("3. Run live API tests: make test-live")
    print("4. Start the server: make run")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    sys.exit(0 if success else 1)