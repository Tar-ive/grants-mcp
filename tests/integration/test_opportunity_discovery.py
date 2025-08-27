"""Integration tests for opportunity discovery tool."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.models.grants_schemas import GrantsAPIResponse, OpportunityV1
from mcp_server.tools.discovery.opportunity_discovery_tool import (
    calculate_summary_statistics,
    create_summary,
    format_grant_details,
    register_opportunity_discovery_tool,
)


class TestOpportunityDiscovery:
    """Test opportunity discovery tool functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.mock_only
    async def test_discovery_with_mock_api(self, mcp_server, sample_api_response):
        """Test opportunity discovery with mocked API response."""
        # Mock the API client
        with patch.object(
            mcp_server.api_client,
            'search_opportunities',
            new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = sample_api_response
            
            # Register the tool
            from fastmcp import FastMCP
            mcp = FastMCP("test")
            context = {
                "cache": mcp_server.cache,
                "api_client": mcp_server.api_client,
                "settings": mcp_server.settings,
                "search_history": []
            }
            register_opportunity_discovery_tool(mcp, context)
            
            # Get the tool function
            tool_func = None
            for tool in mcp.tools:
                if tool.name == "opportunity_discovery":
                    tool_func = tool.fn
                    break
            
            assert tool_func is not None
            
            # Call the tool
            result = await tool_func(
                query="climate change",
                max_results=10
            )
            
            # Verify result
            assert "Search Results for \"climate change\"" in result
            assert "Total Grants Found: 1" in result
            assert "Test Grant Opportunity" in result
            assert mock_search.called
    
    @pytest.mark.asyncio
    async def test_discovery_uses_cache(self, mcp_server):
        """Test that discovery tool uses cache effectively."""
        # First call - should hit API
        with patch.object(
            mcp_server.api_client,
            'search_opportunities',
            new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = {
                "data": [],
                "pagination_info": {
                    "page_size": 25,
                    "page_number": 1,
                    "total_records": 0,
                    "total_pages": 0
                }
            }
            
            # Register the tool
            from fastmcp import FastMCP
            mcp = FastMCP("test")
            context = {
                "cache": mcp_server.cache,
                "api_client": mcp_server.api_client,
                "settings": mcp_server.settings,
                "search_history": []
            }
            register_opportunity_discovery_tool(mcp, context)
            
            # Get the tool function
            tool_func = None
            for tool in mcp.tools:
                if tool.name == "opportunity_discovery":
                    tool_func = tool.fn
                    break
            
            # First call
            result1 = await tool_func(query="test", max_results=10)
            assert mock_search.call_count == 1
            
            # Second call with same parameters - should use cache
            result2 = await tool_func(query="test", max_results=10)
            assert mock_search.call_count == 1  # Still 1, not 2
            
            # Results should be identical
            assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_discovery_handles_api_error(self, mcp_server):
        """Test error handling in discovery tool."""
        from mcp_server.tools.utils.api_client import APIError
        
        # Mock API to raise error
        with patch.object(
            mcp_server.api_client,
            'search_opportunities',
            new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = APIError(500, "Internal Server Error")
            
            # Register the tool
            from fastmcp import FastMCP
            mcp = FastMCP("test")
            context = {
                "cache": mcp_server.cache,
                "api_client": mcp_server.api_client,
                "settings": mcp_server.settings,
                "search_history": []
            }
            register_opportunity_discovery_tool(mcp, context)
            
            # Get the tool function
            tool_func = None
            for tool in mcp.tools:
                if tool.name == "opportunity_discovery":
                    tool_func = tool.fn
                    break
            
            # Call should not raise but return error message
            result = await tool_func(query="test")
            assert "Error searching for opportunities" in result
    
    def test_format_grant_details(self, sample_opportunity):
        """Test grant formatting function."""
        opportunity = OpportunityV1(**sample_opportunity)
        formatted = format_grant_details(opportunity)
        
        assert "Test Grant Opportunity" in formatted
        assert "TEST-2024-001" in formatted
        assert "Test Agency" in formatted
        assert "$100,000" in formatted or "100000" in formatted
        assert "$500,000" in formatted or "500000" in formatted
        assert "2024-03-31" in formatted
        assert "grants@test.gov" in formatted
    
    def test_create_summary(self, sample_opportunity):
        """Test summary creation."""
        opportunity = OpportunityV1(**sample_opportunity)
        summary = create_summary(
            [opportunity],
            "test search",
            page=1,
            grants_per_page=3,
            total_found=1
        )
        
        assert "Search Results for \"test search\"" in summary
        assert "Total Grants Found: 1" in summary
        assert "Page 1 of 1" in summary
        assert "DETAILED GRANT LISTINGS" in summary
    
    def test_calculate_summary_statistics(self, sample_opportunity):
        """Test summary statistics calculation."""
        opportunity = OpportunityV1(**sample_opportunity)
        stats = calculate_summary_statistics([opportunity])
        
        assert stats["agencies"]["TST"] == 1
        assert stats["category_breakdown"]["Science and Technology"] == 1
        assert stats["status_breakdown"]["posted"] == 1
        assert stats["funding_ranges"]["min_floor"] == 100000
        assert stats["funding_ranges"]["max_ceiling"] == 500000
        assert stats["funding_ranges"]["avg_award"] == 500000


class TestOpportunityDiscoveryEdgeCases:
    """Test edge cases in opportunity discovery."""
    
    @pytest.mark.asyncio
    async def test_discovery_with_empty_results(self, mcp_server):
        """Test handling of empty search results."""
        with patch.object(
            mcp_server.api_client,
            'search_opportunities',
            new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = {
                "data": [],
                "pagination_info": {
                    "page_size": 25,
                    "page_number": 1,
                    "total_records": 0,
                    "total_pages": 0
                }
            }
            
            from fastmcp import FastMCP
            mcp = FastMCP("test")
            context = {
                "cache": mcp_server.cache,
                "api_client": mcp_server.api_client,
                "settings": mcp_server.settings,
                "search_history": []
            }
            register_opportunity_discovery_tool(mcp, context)
            
            tool_func = None
            for tool in mcp.tools:
                if tool.name == "opportunity_discovery":
                    tool_func = tool.fn
                    break
            
            result = await tool_func(query="nonexistent")
            assert "Total Grants Found: 0" in result
    
    @pytest.mark.asyncio
    async def test_discovery_with_malformed_data(self, mcp_server):
        """Test handling of malformed API data."""
        with patch.object(
            mcp_server.api_client,
            'search_opportunities',
            new_callable=AsyncMock
        ) as mock_search:
            # Return data with missing required fields
            mock_search.return_value = {
                "data": [
                    {
                        "opportunity_id": 999,
                        # Missing other required fields
                    }
                ],
                "pagination_info": {
                    "page_size": 25,
                    "page_number": 1,
                    "total_records": 1,
                    "total_pages": 1
                }
            }
            
            from fastmcp import FastMCP
            mcp = FastMCP("test")
            context = {
                "cache": mcp_server.cache,
                "api_client": mcp_server.api_client,
                "settings": mcp_server.settings,
                "search_history": []
            }
            register_opportunity_discovery_tool(mcp, context)
            
            tool_func = None
            for tool in mcp.tools:
                if tool.name == "opportunity_discovery":
                    tool_func = tool.fn
                    break
            
            # Should handle gracefully
            result = await tool_func(query="test")
            # Result should still be formatted, even if data is incomplete
            assert "Search Results" in result
    
    def test_statistics_with_missing_fields(self):
        """Test statistics calculation with missing data fields."""
        opportunities = [
            OpportunityV1(
                opportunity_id=1,
                opportunity_number="TEST-001",
                opportunity_title="Test 1",
                opportunity_status="posted",
                agency="TEST",
                agency_code="TST",
                agency_name="Test Agency",
                summary={"award_ceiling": None, "award_floor": None}
            ),
            OpportunityV1(
                opportunity_id=2,
                opportunity_number="TEST-002",
                opportunity_title="Test 2",
                opportunity_status="forecasted",
                agency="TEST",
                agency_code="TST",
                agency_name="Test Agency",
                summary={"award_ceiling": 100000, "award_floor": 50000}
            )
        ]
        
        stats = calculate_summary_statistics(opportunities)
        
        assert stats["agencies"]["TST"] == 2
        assert stats["funding_ranges"]["min_floor"] == 50000
        assert stats["funding_ranges"]["max_ceiling"] == 100000
        assert stats["status_breakdown"]["posted"] == 1
        assert stats["status_breakdown"]["forecasted"] == 1