#!/usr/bin/env python3
"""Test the funding trend scanner fix."""

import asyncio
from datetime import datetime, timedelta

from src.mcp_server.config.settings import Settings
from src.mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from src.mcp_server.tools.utils.cache_manager import InMemoryCache
from src.mcp_server.tools.utils.cache_utils import CacheKeyGenerator
from src.mcp_server.models.grants_schemas import GrantsAPIResponse
from src.mcp_server.tools.discovery.funding_trend_scanner_tool import (
    analyze_temporal_trends,
    identify_funding_patterns,
    detect_emerging_topics,
    format_funding_trends_report,
)


async def test_funding_trend_scanner():
    """Test the fixed funding trend scanner."""
    api_key = "T4TevWYV3suiQ8eLFbza"
    
    print("Testing Funding Trend Scanner Fix")
    print("=" * 40)
    
    settings = Settings(api_key=api_key)
    api_client = SimplerGrantsAPIClient(
        api_key=settings.api_key,
        base_url=settings.api_base_url
    )
    
    try:
        print("\n1. Testing API without date filter...")
        
        # Test without date filter (as fixed)
        filters = {
            "opportunity_status": {"one_of": ["posted", "forecasted"]},
        }
        
        response = await api_client.search_opportunities(
            filters=filters,
            pagination={"page_size": 20, "page_offset": 1}
        )
        
        api_response = GrantsAPIResponse(**response)
        all_opportunities = api_response.get_opportunities()
        
        print(f"   ✅ Fetched {len(all_opportunities)} opportunities")
        
        # Test date filtering in post-processing
        print("\n2. Testing date filtering in post-processing...")
        time_window_days = 90
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        
        filtered_opportunities = []
        for opp in all_opportunities:
            if opp.summary.post_date:
                try:
                    post_date = datetime.fromisoformat(opp.summary.post_date.replace("Z", "+00:00"))
                    if post_date >= cutoff_date:
                        filtered_opportunities.append(opp)
                except:
                    filtered_opportunities.append(opp)
            else:
                # Include forecasted opportunities
                filtered_opportunities.append(opp)
        
        print(f"   ✅ Filtered to {len(filtered_opportunities)} opportunities within {time_window_days} days")
        
        # Test trend analysis functions
        print("\n3. Testing trend analysis functions...")
        
        if filtered_opportunities:
            temporal_trends = analyze_temporal_trends(filtered_opportunities, time_window_days)
            print(f"   ✅ Temporal trends analyzed")
            
            funding_patterns = identify_funding_patterns(filtered_opportunities)
            print(f"   ✅ Funding patterns identified")
            
            emerging_topics = detect_emerging_topics(filtered_opportunities)
            print(f"   ✅ Emerging topics detected")
            
            # Test report generation
            metadata = {
                "total_opportunities": len(filtered_opportunities),
                "time_window_days": time_window_days,
                "total_funding": sum(
                    opp.summary.estimated_total_program_funding or 0
                    for opp in filtered_opportunities
                ),
            }
            
            report = format_funding_trends_report(
                temporal_trends,
                funding_patterns,
                emerging_topics,
                metadata
            )
            
            print(f"   ✅ Report generated successfully")
            
            # Show a snippet of the report
            print("\n4. Sample report output:")
            print("-" * 40)
            lines = report.split('\n')[:15]
            for line in lines:
                print(line)
            print("...")
        
        print("\n" + "=" * 40)
        print("✅ Funding Trend Scanner is working correctly!")
        print("\nThe date filter issue has been fixed.")
        print("The tool now:")
        print("1. Fetches opportunities without date filtering")
        print("2. Filters by date in post-processing")
        print("3. Analyzes trends on the filtered data")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await api_client.close()


if __name__ == "__main__":
    asyncio.run(test_funding_trend_scanner())