"""Live API tests for opportunity discovery (following testing_v3.md)."""

import os

import pytest

from mcp_server.models.grants_schemas import GrantsAPIResponse


@pytest.mark.real_api
class TestLiveDiscovery:
    """Test opportunity discovery with real Simpler Grants API."""
    
    @pytest.mark.asyncio
    async def test_real_api_connection(self, real_api_client):
        """Test that we can connect to the real API."""
        # Check health
        health = await real_api_client.check_health()
        
        assert health["status"] in ["healthy", "degraded"]
        assert "response_time" in health
    
    @pytest.mark.asyncio
    async def test_real_opportunity_search(self, real_api_client, api_snapshot_recorder):
        """Test searching with real API and snapshot results."""
        # Search for renewable energy grants
        response = await api_snapshot_recorder.record(
            "search_renewable_energy",
            lambda: real_api_client.search_opportunities(
                query="renewable energy",
                pagination={"page_size": 5}
            )
        )
        
        assert response is not None
        assert "data" in response
        assert "pagination_info" in response
        
        # Parse response
        api_response = GrantsAPIResponse(**response)
        opportunities = api_response.get_opportunities()
        
        # Verify we got results (may vary based on actual data)
        assert len(opportunities) <= 5
        
        # Save snapshot for future use
        api_snapshot_recorder.save("tests/fixtures/real_api_snapshots.json")
    
    @pytest.mark.asyncio
    async def test_real_api_with_filters(self, real_api_client):
        """Test searching with filters on real API."""
        response = await real_api_client.search_opportunities(
            filters={
                "opportunity_status": {
                    "one_of": ["posted"]
                }
            },
            pagination={"page_size": 3}
        )
        
        assert response is not None
        assert "data" in response
        
        # Verify filter was applied
        for opportunity in response["data"]:
            assert opportunity.get("opportunity_status") == "posted"
    
    @pytest.mark.asyncio
    async def test_real_api_pagination(self, real_api_client):
        """Test pagination with real API."""
        # Get first page
        page1 = await real_api_client.search_opportunities(
            pagination={
                "page_size": 5,
                "page_offset": 1
            }
        )
        
        assert page1 is not None
        total_records = page1["pagination_info"]["total_records"]
        
        if total_records > 5:
            # Get second page
            page2 = await real_api_client.search_opportunities(
                pagination={
                    "page_size": 5,
                    "page_offset": 2
                }
            )
            
            # Verify different results
            page1_ids = {o["opportunity_id"] for o in page1["data"]}
            page2_ids = {o["opportunity_id"] for o in page2["data"]}
            
            # Pages should have different opportunities
            assert page1_ids.isdisjoint(page2_ids)
    
    @pytest.mark.asyncio
    async def test_real_api_rate_limits(self, real_api_client, rate_limit_monitor):
        """Test rate limit tracking with real API."""
        # Make a request
        response = await real_api_client.search_opportunities(
            pagination={"page_size": 1}
        )
        
        # Check rate limit info
        assert real_api_client.rate_limit_remaining is not None
        
        # We should have remaining calls
        assert real_api_client.rate_limit_remaining > 0
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_real_api_performance(self, real_api_client, performance_tracker):
        """Test API response times with real data."""
        # Track multiple requests
        for i in range(3):
            await performance_tracker.track(
                f"search_{i}",
                lambda: real_api_client.search_opportunities(
                    query="technology",
                    pagination={"page_size": 10}
                )
            )
        
        stats = performance_tracker.get_statistics()
        
        # Real API should respond within reasonable time
        assert stats["avg_duration"] < 5.0  # Less than 5 seconds average
        assert stats["success_rate"] >= 0.9  # At least 90% success


@pytest.mark.real_api
class TestLiveDataQuality:
    """Test handling of real data quality issues."""
    
    @pytest.mark.asyncio
    async def test_missing_fields_in_real_data(self, real_api_client):
        """Test that we handle missing fields in real opportunities."""
        response = await real_api_client.search_opportunities(
            pagination={"page_size": 20}
        )
        
        missing_fields = {
            "award_ceiling": 0,
            "award_floor": 0,
            "summary_description": 0,
            "applicant_eligibility_description": 0,
        }
        
        for opportunity in response["data"]:
            summary = opportunity.get("summary", {})
            
            if not summary.get("award_ceiling"):
                missing_fields["award_ceiling"] += 1
            if not summary.get("award_floor"):
                missing_fields["award_floor"] += 1
            if not summary.get("summary_description"):
                missing_fields["summary_description"] += 1
            if not summary.get("applicant_eligibility_description"):
                missing_fields["applicant_eligibility_description"] += 1
        
        # Log data quality findings
        total = len(response["data"])
        print("\nData Quality Report:")
        for field, count in missing_fields.items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {field}: {count}/{total} missing ({percentage:.1f}%)")
        
        # We expect some missing data in real API
        assert total > 0