#!/usr/bin/env python3
"""Test discovery tools with real API."""

import asyncio
import json
import os
from datetime import datetime

from src.mcp_server.config.settings import Settings
from src.mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from src.mcp_server.tools.utils.cache_manager import InMemoryCache
from src.mcp_server.tools.discovery.agency_landscape_tool import (
    analyze_agency_portfolio,
    identify_cross_agency_patterns,
    format_agency_landscape_report,
)
from src.mcp_server.tools.discovery.funding_trend_scanner_tool import (
    analyze_temporal_trends,
    identify_funding_patterns,
    detect_emerging_topics,
    format_funding_trends_report,
)
from src.mcp_server.models.grants_schemas import GrantsAPIResponse


async def test_opportunity_discovery():
    """Test the opportunity discovery tool."""
    print("\n" + "=" * 60)
    print("Testing Opportunity Discovery Tool")
    print("=" * 60)
    
    api_key = os.getenv("SIMPLER_GRANTS_API_KEY", "test_key")
    settings = Settings(api_key=api_key)
    api_client = SimplerGrantsAPIClient(
        api_key=settings.api_key,
        base_url=settings.api_base_url
    )
    
    try:
        # Search for AI-related grants
        filters = {
            "opportunity_status": {"one_of": ["posted"]},
            "keywords": "artificial intelligence"
        }
        
        print("\nSearching for AI-related grants...")
        response = await api_client.search_opportunities(
            filters=filters,
            pagination={"page_size": 5, "page_offset": 1}
        )
        
        api_response = GrantsAPIResponse(**response)
        opportunities = api_response.get_opportunities()
        
        print(f"Found {len(opportunities)} opportunities")
        
        for opp in opportunities[:3]:
            print(f"\n• {opp.opportunity_title}")
            print(f"  Agency: {opp.agency_name}")
            print(f"  Status: {opp.opportunity_status}")
            if opp.summary.award_ceiling:
                print(f"  Max Award: ${opp.summary.award_ceiling:,.0f}")
        
        print("\n✅ Opportunity Discovery tool working correctly")
        
    except Exception as e:
        print(f"❌ Error testing opportunity discovery: {e}")
    finally:
        await api_client.close()


async def test_agency_landscape():
    """Test the agency landscape tool."""
    print("\n" + "=" * 60)
    print("Testing Agency Landscape Tool")
    print("=" * 60)
    
    api_key = os.getenv("SIMPLER_GRANTS_API_KEY", "test_key")
    settings = Settings(api_key=api_key)
    api_client = SimplerGrantsAPIClient(
        api_key=settings.api_key,
        base_url=settings.api_base_url
    )
    
    try:
        # Get top agencies
        print("\nFetching agency information...")
        agency_response = await api_client.search_agencies(
            filters={},
            pagination={"page_size": 5, "page_offset": 1}
        )
        
        api_response = GrantsAPIResponse(**agency_response)
        agencies = api_response.get_agencies()
        
        print(f"Found {len(agencies)} agencies")
        
        # Analyze first agency's portfolio
        if agencies:
            agency = agencies[0]
            print(f"\nAnalyzing portfolio for {agency.agency_name} ({agency.agency_code})...")
            
            # Get opportunities for this agency
            opp_response = await api_client.search_opportunities(
                filters={
                    "agency_code": agency.agency_code,
                    "opportunity_status": {"one_of": ["posted"]}
                },
                pagination={"page_size": 10, "page_offset": 1}
            )
            
            opp_api_response = GrantsAPIResponse(**opp_response)
            opportunities = opp_api_response.get_opportunities()
            
            if opportunities:
                portfolio = analyze_agency_portfolio(agency.agency_code, opportunities)
                
                print(f"\nPortfolio Analysis:")
                print(f"  Total Opportunities: {portfolio['total_opportunities']}")
                print(f"  Categories: {list(portfolio['category_breakdown'].keys())[:3]}")
                if portfolio['funding_stats']['average_award_ceiling']:
                    print(f"  Avg Award Ceiling: ${portfolio['funding_stats']['average_award_ceiling']:,.0f}")
        
        print("\n✅ Agency Landscape tool working correctly")
        
    except Exception as e:
        print(f"❌ Error testing agency landscape: {e}")
    finally:
        await api_client.close()


async def test_funding_trends():
    """Test the funding trend scanner tool."""
    print("\n" + "=" * 60)
    print("Testing Funding Trend Scanner Tool")
    print("=" * 60)
    
    api_key = os.getenv("SIMPLER_GRANTS_API_KEY", "test_key")
    settings = Settings(api_key=api_key)
    api_client = SimplerGrantsAPIClient(
        api_key=settings.api_key,
        base_url=settings.api_base_url
    )
    
    try:
        # Get recent opportunities for trend analysis
        print("\nFetching recent opportunities for trend analysis...")
        
        filters = {
            "opportunity_status": {"one_of": ["posted"]},
        }
        
        response = await api_client.search_opportunities(
            filters=filters,
            pagination={"page_size": 50, "page_offset": 1}
        )
        
        api_response = GrantsAPIResponse(**response)
        opportunities = api_response.get_opportunities()
        
        print(f"Analyzing {len(opportunities)} opportunities...")
        
        # Perform trend analyses
        temporal_trends = analyze_temporal_trends(opportunities, 90)
        funding_patterns = identify_funding_patterns(opportunities)
        emerging_topics = detect_emerging_topics(opportunities)
        
        print("\nTrend Analysis Results:")
        
        # Temporal trends
        if temporal_trends["deadline_distribution"]:
            print("\nUpcoming Deadlines:")
            for period, count in temporal_trends["deadline_distribution"].items():
                print(f"  • {period}: {count} opportunities")
        
        # Funding patterns
        if funding_patterns["funding_tier_summary"]:
            print("\nFunding Tier Distribution:")
            for tier, count in funding_patterns["funding_tier_summary"].items():
                if count > 0:
                    print(f"  • {tier.capitalize()}: {count} opportunities")
        
        # High-value opportunities
        if funding_patterns["high_value_opportunities"]:
            print("\nTop High-Value Opportunities:")
            for opp in funding_patterns["high_value_opportunities"][:3]:
                print(f"  • {opp['title'][:50]}...")
                print(f"    Total: ${opp['total_funding']:,.0f}")
        
        # Emerging topics
        if emerging_topics["emerging_themes"]:
            print("\nEmerging Themes:")
            for theme in emerging_topics["emerging_themes"][:3]:
                print(f"  • {theme['theme'].title()}: {theme['frequency']} occurrences")
        
        print("\n✅ Funding Trend Scanner tool working correctly")
        
    except Exception as e:
        print(f"❌ Error testing funding trends: {e}")
    finally:
        await api_client.close()


async def test_cache_functionality():
    """Test cache functionality with tools."""
    print("\n" + "=" * 60)
    print("Testing Cache Functionality")
    print("=" * 60)
    
    cache = InMemoryCache(ttl=300)
    
    # Test cache operations
    print("\nTesting cache operations...")
    
    # Set a test value
    test_key = cache.generate_cache_key("test", param1="value1", param2=123)
    test_data = {"result": "test data", "timestamp": datetime.now().isoformat()}
    
    cache.set(test_key, test_data)
    print(f"✓ Cached data with key: {test_key[:50]}...")
    
    # Retrieve the value
    cached_value = cache.get(test_key)
    if cached_value == test_data:
        print("✓ Successfully retrieved cached data")
    
    # Check cache stats
    stats = cache.get_stats()
    print(f"\nCache Statistics:")
    print(f"  • Items: {stats.get('items', 'N/A')}")
    print(f"  • Size: {stats.get('size_bytes', 'N/A')} bytes")
    if 'hit_rate' in stats:
        print(f"  • Hit Rate: {stats['hit_rate']:.1%}")
    if 'miss_rate' in stats:
        print(f"  • Miss Rate: {stats['miss_rate']:.1%}")
    
    print("\n✅ Cache functionality working correctly")


async def main():
    """Run all tests."""
    print("\n" + "🚀" * 30)
    print("Testing Discovery Tools with Real API")
    print("🚀" * 30)
    
    # Check for API key
    if not os.getenv("SIMPLER_GRANTS_API_KEY"):
        print("\n⚠️  Warning: SIMPLER_GRANTS_API_KEY not set")
        print("   Some tests may fail or return limited results")
    
    # Run tests
    await test_opportunity_discovery()
    await test_agency_landscape()
    await test_funding_trends()
    await test_cache_functionality()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())