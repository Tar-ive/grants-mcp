"""Tests for discovery tools."""

import asyncio
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.mcp_server.models.grants_schemas import (
    AgencyV1,
    GrantsAPIResponse,
    OpportunitySummary,
    OpportunityV1,
    PaginationInfo,
)
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
from src.mcp_server.tools.utils.cache_manager import InMemoryCache


class TestAgencyLandscapeTool(unittest.TestCase):
    """Test suite for agency landscape analysis tool."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_agencies = [
            AgencyV1(
                agency_code="NSF",
                agency_name="National Science Foundation",
            ),
            AgencyV1(
                agency_code="NIH",
                agency_name="National Institutes of Health",
            ),
        ]
        
        self.sample_opportunities = [
            OpportunityV1(
                opportunity_id="123",
                opportunity_number="NSF-2024-001",
                opportunity_title="AI Research Grant",
                opportunity_status="posted",
                agency="NSF",
                agency_code="NSF",
                agency_name="National Science Foundation",
                category="Science",
                summary=OpportunitySummary(
                    award_ceiling=500000,
                    award_floor=100000,
                    estimated_total_program_funding=5000000,
                    expected_number_of_awards=10,
                    applicant_types=["Universities", "Nonprofits"],
                    close_date="2024-12-31",
                )
            ),
            OpportunityV1(
                opportunity_id="124",
                opportunity_number="NSF-2024-002",
                opportunity_title="Climate Research",
                opportunity_status="forecasted",
                agency="NSF",
                agency_code="NSF",
                agency_name="National Science Foundation",
                category="Environment",
                summary=OpportunitySummary(
                    award_ceiling=1000000,
                    award_floor=250000,
                    estimated_total_program_funding=10000000,
                    applicant_types=["Universities"],
                    close_date="2024-11-30",
                )
            ),
        ]
    
    def test_analyze_agency_portfolio(self):
        """Test agency portfolio analysis."""
        portfolio = analyze_agency_portfolio("NSF", self.sample_opportunities)
        
        self.assertEqual(portfolio["agency_code"], "NSF")
        self.assertEqual(portfolio["total_opportunities"], 2)
        self.assertEqual(portfolio["status_breakdown"]["posted"], 1)
        self.assertEqual(portfolio["status_breakdown"]["forecasted"], 1)
        self.assertEqual(portfolio["category_breakdown"]["Science"], 1)
        self.assertEqual(portfolio["category_breakdown"]["Environment"], 1)
        
        # Check funding stats
        self.assertEqual(portfolio["funding_stats"]["total_estimated_funding"], 15000000)
        self.assertEqual(portfolio["funding_stats"]["max_award"], 1000000)
        self.assertEqual(portfolio["funding_stats"]["min_award"], 100000)
    
    def test_identify_cross_agency_patterns(self):
        """Test cross-agency pattern identification."""
        agency_profiles = {
            "NSF": {
                "category_breakdown": {"Science": 5, "Technology": 3},
                "funding_stats": {"average_award_ceiling": 500000},
                "total_opportunities": 8,
            },
            "NIH": {
                "category_breakdown": {"Health": 10, "Science": 2},
                "funding_stats": {"average_award_ceiling": 750000},
                "total_opportunities": 12,
            },
            "DOE": {
                "category_breakdown": {"Energy": 6, "Science": 1},
                "funding_stats": {"average_award_ceiling": 1000000},
                "total_opportunities": 7,
            },
        }
        
        patterns = identify_cross_agency_patterns(agency_profiles)
        
        # Check overlap areas
        science_overlap = next(
            (o for o in patterns["overlap_areas"] if o["category"] == "Science"),
            None
        )
        self.assertIsNotNone(science_overlap)
        self.assertEqual(len(science_overlap["agencies"]), 3)
        
        # Check unique specializations
        self.assertIn("Technology", patterns["unique_specializations"].get("NSF", []))
        self.assertIn("Health", patterns["unique_specializations"].get("NIH", []))
        self.assertIn("Energy", patterns["unique_specializations"].get("DOE", []))
    
    def test_format_agency_landscape_report(self):
        """Test report formatting."""
        agency_profiles = {
            "NSF": {
                "agency_code": "NSF",
                "agency_name": "National Science Foundation",
                "total_opportunities": 10,
                "category_breakdown": {"Science": 5, "Technology": 5},
                "funding_stats": {
                    "average_award_ceiling": 500000,
                    "total_estimated_funding": 5000000,
                },
            },
        }
        
        cross_agency_analysis = {
            "overlap_areas": [],
            "unique_specializations": {"NSF": ["Technology"]},
            "funding_comparison": {"NSF": {"average_ceiling": 500000}},
        }
        
        funding_landscape = {
            "total_active_agencies": 1,
            "category_specialization": {"Science": 5, "Technology": 5},
        }
        
        report = format_agency_landscape_report(
            self.sample_agencies[:1],
            agency_profiles,
            cross_agency_analysis,
            funding_landscape
        )
        
        self.assertIn("AGENCY LANDSCAPE ANALYSIS", report)
        self.assertIn("Total Active Agencies: 1", report)
        self.assertIn("NSF: National Science Foundation", report)
        self.assertIn("Opportunities: 10", report)


class TestFundingTrendScannerTool(unittest.TestCase):
    """Test suite for funding trend scanner tool."""
    
    def setUp(self):
        """Set up test fixtures."""
        now = datetime.now()
        self.sample_opportunities = [
            OpportunityV1(
                opportunity_id="125",
                opportunity_number="GRANT-2024-001",
                opportunity_title="Artificial Intelligence Research Grant",
                opportunity_status="posted",
                agency="NSF",
                agency_code="NSF",
                agency_name="National Science Foundation",
                category="Technology",
                category_explanation="AI and ML research",
                summary=OpportunitySummary(
                    award_ceiling=500000,
                    award_floor=100000,
                    estimated_total_program_funding=5000000,
                    expected_number_of_awards=10,
                    post_date=(now - timedelta(days=10)).isoformat(),
                    close_date=(now + timedelta(days=30)).isoformat(),
                    summary_description="Support for AI research",
                )
            ),
            OpportunityV1(
                opportunity_id="126",
                opportunity_number="GRANT-2024-002",
                opportunity_title="Climate Change Mitigation",
                opportunity_status="posted",
                agency="EPA",
                agency_code="EPA",
                agency_name="Environmental Protection Agency",
                category="Environment",
                summary=OpportunitySummary(
                    award_ceiling=1000000,
                    award_floor=250000,
                    estimated_total_program_funding=20000000,
                    expected_number_of_awards=20,
                    post_date=(now - timedelta(days=60)).isoformat(),
                    close_date=(now + timedelta(days=60)).isoformat(),
                    summary_description="Climate resilience and sustainability",
                )
            ),
            OpportunityV1(
                opportunity_id="127",
                opportunity_number="GRANT-2024-003",
                opportunity_title="Quantum Computing Initiative",
                opportunity_status="posted",
                agency="DOE",
                agency_code="DOE",
                agency_name="Department of Energy",
                category="Technology",
                summary=OpportunitySummary(
                    award_ceiling=10000000,
                    award_floor=1000000,
                    estimated_total_program_funding=100000000,
                    expected_number_of_awards=3,
                    post_date=(now - timedelta(days=5)).isoformat(),
                    close_date=(now + timedelta(days=90)).isoformat(),
                    summary_description="Quantum computing research",
                    funding_instrument="Cooperative Agreement",
                )
            ),
        ]
    
    def test_analyze_temporal_trends(self):
        """Test temporal trend analysis."""
        trends = analyze_temporal_trends(self.sample_opportunities, 90)
        
        # Check posting frequency
        self.assertIn("posting_frequency", trends)
        self.assertTrue(any("week_" in k for k in trends["posting_frequency"].keys()))
        
        # Check funding velocity
        self.assertIn("funding_velocity", trends)
        self.assertGreater(trends["funding_velocity"]["recent"], 0)
        
        # Check deadline distribution
        self.assertIn("deadline_distribution", trends)
        self.assertGreater(trends["deadline_distribution"].get("30_days", 0), 0)
    
    def test_identify_funding_patterns(self):
        """Test funding pattern identification."""
        patterns = identify_funding_patterns(self.sample_opportunities)
        
        # Check funding tiers
        self.assertEqual(len(patterns["funding_tiers"]["small"]), 1)  # $500K ceiling
        self.assertEqual(len(patterns["funding_tiers"]["medium"]), 1)  # $1M ceiling
        self.assertEqual(len(patterns["funding_tiers"]["mega"]), 1)  # $10M ceiling
        
        # Check high-value opportunities
        self.assertGreater(len(patterns["high_value_opportunities"]), 0)
        
        # Check ROI opportunities
        self.assertGreater(len(patterns["best_roi_opportunities"]), 0)
        quantum_grant = patterns["best_roi_opportunities"][0]
        self.assertIn("Quantum", quantum_grant["title"])
    
    def test_detect_emerging_topics(self):
        """Test emerging topic detection."""
        topics = detect_emerging_topics(self.sample_opportunities)
        
        # Check keyword frequency
        self.assertIn("keyword_frequency", topics)
        self.assertGreater(topics["keyword_frequency"].get("artificial intelligence", 0), 0)
        self.assertGreater(topics["keyword_frequency"].get("climate", 0), 0)
        self.assertGreater(topics["keyword_frequency"].get("quantum", 0), 0)
        
        # Check emerging themes
        self.assertIn("emerging_themes", topics)
    
    def test_format_funding_trends_report(self):
        """Test trend report formatting."""
        temporal_trends = {
            "posting_frequency": {"week_0": 2, "week_1": 1},
            "funding_velocity": {"recent": 105000000, "older": 20000000, "acceleration": 425},
            "deadline_distribution": {"30_days": 1, "60_days": 1, "90_days": 1},
            "seasonal_patterns": {},
        }
        
        funding_patterns = {
            "funding_tier_summary": {"micro": 0, "small": 1, "medium": 1, "mega": 1},
            "high_value_opportunities": [
                {
                    "title": "Quantum Computing Initiative",
                    "total_funding": 100000000,
                    "close_date": "2024-12-31",
                }
            ],
            "best_roi_opportunities": [],
            "funding_instruments": {"Cooperative Agreement": 1},
            "award_size_trends": {},
        }
        
        emerging_topics = {
            "emerging_themes": [
                {"theme": "quantum", "frequency": 1, "percentage": 33.3}
            ],
            "cross_cutting_themes": [],
            "keyword_frequency": {},
            "category_combinations": {},
        }
        
        metadata = {
            "total_opportunities": 3,
            "time_window_days": 90,
            "total_funding": 125000000,
        }
        
        report = format_funding_trends_report(
            temporal_trends,
            funding_patterns,
            emerging_topics,
            metadata
        )
        
        self.assertIn("FUNDING TRENDS ANALYSIS REPORT", report)
        self.assertIn("Opportunities Analyzed: 3", report)
        self.assertIn("Total Funding Available: $125,000,000", report)
        self.assertIn("Funding is accelerating", report)
        self.assertIn("Quantum Computing Initiative", report)


class TestDiscoveryToolsIntegration(unittest.TestCase):
    """Integration tests for discovery tools."""
    
    @patch('src.mcp_server.tools.utils.api_client.SimplerGrantsAPIClient')
    async def test_agency_landscape_tool_integration(self, mock_api_client_class):
        """Test agency landscape tool integration."""
        from fastmcp import FastMCP
        from src.mcp_server.tools.discovery.agency_landscape_tool import (
            register_agency_landscape_tool
        )
        
        # Set up mock API client
        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        
        # Mock API responses
        mock_api_client.search_agencies.return_value = {
            "data": [
                {
                    "agency_code": "NSF",
                    "agency_name": "National Science Foundation",
                }
            ],
            "pagination_info": {
                "page_size": 100,
                "page_offset": 1,
                "total_records": 1,
            }
        }
        
        mock_api_client.search_opportunities.return_value = {
            "data": [
                {
                    "opportunity_id": "123",
                    "opportunity_number": "NSF-2024-001",
                    "opportunity_title": "Test Grant",
                    "opportunity_status": "posted",
                    "agency": "NSF",
                    "agency_code": "NSF",
                    "agency_name": "National Science Foundation",
                    "category": "Science",
                    "summary": {
                        "award_ceiling": 500000,
                        "award_floor": 100000,
                    }
                }
            ],
            "pagination_info": {
                "page_size": 50,
                "page_offset": 1,
                "total_records": 1,
            }
        }
        
        # Create MCP server and register tool
        mcp = FastMCP("test_server")
        cache = InMemoryCache()
        context = {"cache": cache, "api_client": mock_api_client}
        
        register_agency_landscape_tool(mcp, context)
        
        # Test tool execution
        tool = mcp._tools["agency_landscape"]
        result = await tool.func(
            include_opportunities=True,
            max_agencies=1
        )
        
        self.assertIn("AGENCY LANDSCAPE ANALYSIS", result)
        self.assertIn("NSF", result)
    
    @patch('src.mcp_server.tools.utils.api_client.SimplerGrantsAPIClient')
    async def test_funding_trend_scanner_integration(self, mock_api_client_class):
        """Test funding trend scanner tool integration."""
        from fastmcp import FastMCP
        from src.mcp_server.tools.discovery.funding_trend_scanner_tool import (
            register_funding_trend_scanner_tool
        )
        
        # Set up mock API client
        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        
        # Mock API response with trends data
        now = datetime.now()
        mock_api_client.search_opportunities.return_value = {
            "data": [
                {
                    "opportunity_id": "123",
                    "opportunity_number": "GRANT-2024-001",
                    "opportunity_title": "AI Research",
                    "opportunity_status": "posted",
                    "agency": "NSF",
                    "agency_code": "NSF",
                    "agency_name": "National Science Foundation",
                    "category": "Technology",
                    "summary": {
                        "award_ceiling": 500000,
                        "post_date": (now - timedelta(days=10)).isoformat(),
                        "close_date": (now + timedelta(days=30)).isoformat(),
                        "summary_description": "artificial intelligence research",
                    }
                }
            ],
            "pagination_info": {
                "page_size": 100,
                "page_offset": 1,
                "total_records": 1,
            }
        }
        
        # Create MCP server and register tool
        mcp = FastMCP("test_server")
        cache = InMemoryCache()
        context = {"cache": cache, "api_client": mock_api_client}
        
        register_funding_trend_scanner_tool(mcp, context)
        
        # Test tool execution
        tool = mcp._tools["funding_trend_scanner"]
        result = await tool.func(
            time_window_days=30,
            include_forecasted=False
        )
        
        self.assertIn("FUNDING TRENDS ANALYSIS REPORT", result)
        self.assertIn("TEMPORAL TRENDS", result)


def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


if __name__ == "__main__":
    unittest.main()