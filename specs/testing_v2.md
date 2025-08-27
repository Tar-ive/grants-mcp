# Grants Analysis MCP Testing Strategy v2

## Overview
Comprehensive testing strategy for the Python-based Grants Analysis MCP, adapted from proven MCP testing patterns and aligned with the specifications in `mcp_design_spec.md`.

## Testing Philosophy
- **MCP Protocol Compliance**: Ensure all tools, resources, and prompts follow MCP standards
- **API Interaction Testing**: Mock external API calls while testing core functionality
- **Edge Case Coverage**: Comprehensive testing of error conditions and data quality issues
- **Performance Validation**: Test with realistic data volumes and concurrent operations
- **Integration Testing**: Validate complete workflows from discovery to analysis

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                         # Pytest configuration and shared fixtures
├── fixtures/                           # Test data and mock responses
│   ├── __init__.py
│   ├── api_responses.py               # Mock API response fixtures
│   ├── sample_grants.py               # Sample grant data fixtures
│   └── error_responses.py             # Error scenario fixtures
├── unit/                               # Unit tests for individual components
│   ├── __init__.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── test_opportunity_discovery.py
│   │   ├── test_agency_landscape.py
│   │   ├── test_funding_trend_scanner.py
│   │   ├── test_opportunity_density.py
│   │   ├── test_eligibility_decoder.py
│   │   ├── test_budget_distribution.py
│   │   ├── test_deadline_cluster.py
│   │   ├── test_agency_pattern.py
│   │   └── test_opportunity_pattern.py
│   ├── resources/
│   │   ├── __init__.py
│   │   ├── test_api_status_resource.py
│   │   ├── test_search_history_resource.py
│   │   └── test_analysis_cache_resource.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── test_prompt_generation.py
│   │   └── test_prompt_validation.py
│   └── utils/
│       ├── __init__.py
│       ├── test_api_client.py
│       ├── test_data_processors.py
│       ├── test_error_handlers.py
│       └── test_validators.py
├── integration/                        # Integration tests
│   ├── __init__.py
│   ├── test_mcp_server.py            # MCP server integration
│   ├── test_api_integration.py       # Real API interaction tests
│   ├── test_workflow_integration.py  # End-to-end workflows
│   └── test_cache_integration.py     # Cache behavior tests
├── performance/                        # Performance tests
│   ├── __init__.py
│   ├── test_large_datasets.py        # Large result set handling
│   ├── test_concurrent_access.py     # Concurrent operations
│   └── test_memory_usage.py          # Memory consumption tests
└── edge_cases/                        # Edge case tests
    ├── __init__.py
    ├── test_data_quality.py          # Missing/malformed data
    ├── test_network_failures.py      # Network error scenarios
    ├── test_rate_limiting.py         # API rate limit handling
    └── test_boundary_conditions.py   # Extreme input values
```

## Core Testing Components

### 1. Base Test Configuration (`conftest.py`)

```python
"""Test configuration and fixtures for Grants Analysis MCP."""

import pytest
import asyncio
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any
from pathlib import Path

# Add src to Python path for tests
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from mcp_server.server import GrantsAnalysisServer
from mcp_server.config import Settings
from mcp_server.models.grants_schemas import OpportunityV1, AgencyV1
from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient

# Test settings
TEST_API_KEY = "test_api_key_12345"
TEST_SETTINGS = Settings(
    api_key=TEST_API_KEY,
    cache_ttl=60,
    max_cache_size=100,
    rate_limit_requests=10,
    rate_limit_period=1
)


@pytest.fixture
def mcp_server():
    """Get the MCP server instance for testing."""
    server = GrantsAnalysisServer(settings=TEST_SETTINGS)
    return server


@pytest.fixture
def mock_api_client():
    """Create a mock API client with preset responses."""
    client = Mock(spec=SimplerGrantsAPIClient)
    client.search_opportunities = AsyncMock()
    client.search_agencies = AsyncMock()
    client.get_opportunity = AsyncMock()
    return client


@pytest.fixture
def sample_opportunity():
    """Create a sample opportunity for testing."""
    return OpportunityV1(
        opportunity_id=12345,
        opportunity_number="GRANT-2024-001",
        opportunity_title="Research Grant for Climate Science",
        opportunity_status="posted",
        agency_code="NSF",
        agency_name="National Science Foundation",
        summary={
            "award_ceiling": 500000,
            "award_floor": 100000,
            "estimated_total_program_funding": 10000000,
            "expected_number_of_awards": 20,
            "post_date": "2024-01-15",
            "close_date": "2024-03-15",
            "summary_description": "Support for climate research projects",
            "applicant_eligibility_description": "Universities and research institutions"
        },
        category="Science and Technology"
    )


@pytest.fixture
def sample_agency():
    """Create a sample agency for testing."""
    return AgencyV1(
        agency_code="NSF",
        agency_name="National Science Foundation",
        top_level_agency_name="National Science Foundation",
        sub_tier_agency_name=None,
        contact={
            "email": "grants@nsf.gov",
            "phone": "555-0100"
        }
    )


@pytest.fixture
def mock_api_response_success():
    """Mock successful API response."""
    return {
        "data": [],
        "pagination_info": {
            "total_records": 0,
            "page_size": 25,
            "page_number": 1,
            "total_pages": 1
        },
        "facet_counts": {
            "agency": {},
            "category": {}
        }
    }


@pytest.fixture
def mock_api_response_error():
    """Mock API error response."""
    return {
        "error": {
            "code": 422,
            "message": "Validation error",
            "details": {
                "field": "filters.date_range",
                "issue": "Invalid date format"
            }
        }
    }


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    # Clear any cached data
    if hasattr(GrantsAnalysisServer, '_cache'):
        GrantsAnalysisServer._cache.clear()
    yield
    if hasattr(GrantsAnalysisServer, '_cache'):
        GrantsAnalysisServer._cache.clear()


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### 2. Tool Testing Pattern

Based on quick-data-mcp patterns, here's the adapted testing approach for grants MCP tools:

```python
"""Tests for opportunity discovery tool functionality."""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from mcp_server.tools.discovery import opportunity_discovery_tool
from mcp_server.models.grants_schemas import OpportunityV1
from fixtures.api_responses import (
    MOCK_OPPORTUNITIES_FULL,
    MOCK_OPPORTUNITIES_EMPTY,
    MOCK_OPPORTUNITIES_PARTIAL
)


class TestOpportunityDiscovery:
    """Test opportunity discovery tool functionality."""
    
    @pytest.fixture
    def mock_search_response(self):
        """Create mock search response with multiple opportunities."""
        return {
            "data": MOCK_OPPORTUNITIES_FULL,
            "pagination_info": {
                "total_records": 150,
                "page_size": 25,
                "page_number": 1,
                "total_pages": 6
            },
            "facet_counts": {
                "agency": {
                    "NSF": 45,
                    "NIH": 38,
                    "DOE": 27
                },
                "category": {
                    "Science and Technology": 65,
                    "Health": 30,
                    "Education": 15
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_successful_discovery(self, mock_api_client, mock_search_response):
        """Test successful opportunity discovery with filters."""
        mock_api_client.search_opportunities.return_value = mock_search_response
        
        result = await opportunity_discovery_tool.discover(
            domain="climate change",
            filters={
                "agency": "NSF",
                "opportunity_status": "posted"
            },
            max_results=50,
            api_client=mock_api_client
        )
        
        assert result["total_found"] == 150
        assert len(result["opportunities"]) <= 50
        assert "summary_stats" in result
        assert result["summary_stats"]["agencies"]["NSF"] == 45
        assert result["metadata"]["api_status"] == "success"
        assert not result["metadata"]["cache_used"]
        
        # Verify API was called with correct parameters
        mock_api_client.search_opportunities.assert_called_once()
        call_args = mock_api_client.search_opportunities.call_args
        assert call_args.kwargs["query"] == "climate change"
        assert call_args.kwargs["filters"]["agency"] == "NSF"
    
    @pytest.mark.asyncio
    async def test_empty_results_handling(self, mock_api_client):
        """Test handling of empty search results."""
        mock_api_client.search_opportunities.return_value = {
            "data": [],
            "pagination_info": {"total_records": 0},
            "facet_counts": {}
        }
        
        result = await opportunity_discovery_tool.discover(
            domain="nonexistent topic",
            api_client=mock_api_client
        )
        
        assert result["total_found"] == 0
        assert result["opportunities"] == []
        assert result["metadata"]["api_status"] == "success"
        assert "No opportunities found" in result.get("suggestions", [""])[0]
    
    @pytest.mark.asyncio
    async def test_api_timeout_recovery(self, mock_api_client):
        """Test recovery from API timeouts with retry logic."""
        # First call times out, second succeeds
        mock_api_client.search_opportunities.side_effect = [
            TimeoutError("API request timed out"),
            {"data": MOCK_OPPORTUNITIES_PARTIAL, "pagination_info": {"total_records": 5}}
        ]
        
        result = await opportunity_discovery_tool.discover(
            domain="test",
            api_client=mock_api_client
        )
        
        assert result["total_found"] == 5
        assert mock_api_client.search_opportunities.call_count == 2
        assert result["metadata"]["api_status"] == "recovered"
    
    @pytest.mark.asyncio
    async def test_invalid_filter_validation(self, mock_api_client):
        """Test validation of invalid filter parameters."""
        result = await opportunity_discovery_tool.discover(
            filters={
                "invalid_field": "value",
                "date_range": "invalid_date"
            },
            api_client=mock_api_client
        )
        
        assert "error" in result
        assert result["error"]["type"] == "validation_error"
        assert "invalid_field" in result["error"]["details"]["field"]
        assert len(result["error"]["recovery_options"]) > 0
    
    @pytest.mark.asyncio
    async def test_pagination_handling(self, mock_api_client):
        """Test handling of paginated results."""
        # Mock multiple pages of results
        page1 = {"data": MOCK_OPPORTUNITIES_FULL[:25], "pagination_info": {"total_records": 75, "page_number": 1, "total_pages": 3}}
        page2 = {"data": MOCK_OPPORTUNITIES_FULL[25:50], "pagination_info": {"total_records": 75, "page_number": 2, "total_pages": 3}}
        page3 = {"data": MOCK_OPPORTUNITIES_FULL[50:75], "pagination_info": {"total_records": 75, "page_number": 3, "total_pages": 3}}
        
        mock_api_client.search_opportunities.side_effect = [page1, page2, page3]
        
        result = await opportunity_discovery_tool.discover(
            max_results=100,
            api_client=mock_api_client
        )
        
        assert len(result["opportunities"]) == 75
        assert mock_api_client.search_opportunities.call_count == 3
    
    @pytest.mark.asyncio
    async def test_date_range_edge_cases(self, mock_api_client):
        """Test handling of various date range scenarios."""
        # Test future dates
        future_date = datetime.now() + timedelta(days=365)
        result = await opportunity_discovery_tool.discover(
            filters={
                "close_date_after": future_date.isoformat()
            },
            api_client=mock_api_client
        )
        
        assert "warning" in result
        assert "Future date detected" in result["warning"]
        
        # Test invalid date range (start after end)
        result = await opportunity_discovery_tool.discover(
            filters={
                "post_date_after": "2024-12-31",
                "post_date_before": "2024-01-01"
            },
            api_client=mock_api_client
        )
        
        assert "error" in result
        assert "Invalid date range" in result["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_malformed_api_response(self, mock_api_client):
        """Test handling of malformed API responses."""
        mock_api_client.search_opportunities.return_value = {
            "unexpected_field": "value",
            # Missing required fields
        }
        
        result = await opportunity_discovery_tool.discover(
            api_client=mock_api_client
        )
        
        assert "error" in result
        assert result["error"]["type"] == "api_error"
        assert "Malformed response" in result["error"]["message"]
        assert result.get("partial_results") is not None
    
    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, mock_api_client):
        """Test handling of API rate limiting."""
        mock_api_client.search_opportunities.side_effect = [
            {"error": {"code": 429, "message": "Rate limit exceeded", "retry_after": 60}}
        ]
        
        result = await opportunity_discovery_tool.discover(
            api_client=mock_api_client
        )
        
        assert result["metadata"]["api_status"] == "rate_limited"
        assert "retry_after" in result["metadata"]
        assert result["metadata"]["retry_after"] == 60
```

### 3. Resource Testing Pattern

```python
"""Tests for API status resource functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from mcp_server.resources import api_status_resource


class TestAPIStatusResource:
    """Test API status resource functionality."""
    
    @pytest.mark.asyncio
    async def test_healthy_api_status(self, mcp_server):
        """Test retrieving status when API is healthy."""
        with patch('mcp_server.resources.api_status_resource.check_api_health') as mock_check:
            mock_check.return_value = {
                "status": "healthy",
                "response_time_ms": 125.5,
                "last_successful_call": datetime.now()
            }
            
            result = await mcp_server.get_resource("grants://api/status")
            
            assert result["api_health"]["status"] == "healthy"
            assert result["api_health"]["response_time_ms"] == 125.5
            assert "authentication" in result
            assert "endpoint_status" in result
    
    @pytest.mark.asyncio
    async def test_degraded_api_detection(self, mcp_server):
        """Test detection of degraded API performance."""
        with patch('mcp_server.resources.api_status_resource.check_api_health') as mock_check:
            mock_check.return_value = {
                "status": "degraded",
                "response_time_ms": 2500.0,
                "known_issues": ["High latency detected", "Some endpoints slow"]
            }
            
            result = await mcp_server.get_resource("grants://api/status")
            
            assert result["api_health"]["status"] == "degraded"
            assert len(result["api_health"]["known_issues"]) == 2
            assert result["api_health"]["response_time_ms"] > 2000
    
    @pytest.mark.asyncio
    async def test_token_expiration_warning(self, mcp_server):
        """Test proactive warning for token expiration."""
        expires_soon = datetime.now() + timedelta(hours=1)
        
        with patch('mcp_server.resources.api_status_resource.get_token_status') as mock_token:
            mock_token.return_value = {
                "token_status": "valid",
                "token_expires": expires_soon,
                "warning": "Token expires in less than 2 hours"
            }
            
            result = await mcp_server.get_resource("grants://api/status")
            
            assert result["authentication"]["token_status"] == "valid"
            assert "warning" in result["authentication"]
            assert "expires in less than" in result["authentication"]["warning"]
    
    @pytest.mark.asyncio
    async def test_rate_limit_tracking(self, mcp_server):
        """Test accurate rate limit tracking."""
        reset_time = datetime.now() + timedelta(minutes=15)
        
        with patch('mcp_server.resources.api_status_resource.get_rate_limit_status') as mock_rate:
            mock_rate.return_value = {
                "remaining_calls": 42,
                "reset_time": reset_time,
                "quota_limit": 100
            }
            
            result = await mcp_server.get_resource("grants://api/status")
            
            assert result["authentication"]["rate_limit"]["remaining_calls"] == 42
            assert result["authentication"]["rate_limit"]["quota_limit"] == 100
            assert result["authentication"]["rate_limit"]["reset_time"] == reset_time
    
    @pytest.mark.asyncio
    async def test_endpoint_availability_check(self, mcp_server):
        """Test individual endpoint availability checking."""
        with patch('mcp_server.resources.api_status_resource.check_endpoints') as mock_endpoints:
            mock_endpoints.return_value = {
                "/v1/opportunities/search": "available",
                "/v1/agencies/search": "limited",
                "/v1/opportunities/{id}": "unavailable"
            }
            
            result = await mcp_server.get_resource("grants://api/status")
            
            assert result["endpoint_status"]["/v1/opportunities/search"] == "available"
            assert result["endpoint_status"]["/v1/agencies/search"] == "limited"
            assert result["endpoint_status"]["/v1/opportunities/{id}"] == "unavailable"
```

### 4. Integration Testing Pattern

```python
"""Tests for MCP server integration."""

import pytest
from mcp import Server, InMemoryTransport
from unittest.mock import patch, AsyncMock

from mcp_server.server import GrantsAnalysisServer


class TestMCPServerIntegration:
    """Test MCP server integration and protocol compliance."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initializes with correct capabilities."""
        server = GrantsAnalysisServer()
        
        assert server.name == "grants-analysis-mcp"
        assert server.version == "1.0.0"
        assert "tools" in server.capabilities
        assert "resources" in server.capabilities
        assert "prompts" in server.capabilities
    
    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test all tools are properly registered."""
        server = GrantsAnalysisServer()
        tools = await server.list_tools()
        
        expected_tools = [
            "opportunity_discovery",
            "agency_landscape",
            "funding_trend_scanner",
            "opportunity_density",
            "budget_distribution",
            "deadline_cluster",
            "eligibility_decoder",
            "agency_pattern",
            "opportunity_pattern"
        ]
        
        tool_names = [tool.name for tool in tools]
        for expected in expected_tools:
            assert expected in tool_names
    
    @pytest.mark.asyncio
    async def test_resource_registration(self):
        """Test all resources are properly registered."""
        server = GrantsAnalysisServer()
        resources = await server.list_resources()
        
        expected_resources = [
            "grants://api/status",
            "grants://search/history",
            "grants://cache/analysis"
        ]
        
        resource_uris = [resource.uri for resource in resources]
        for expected in expected_resources:
            assert any(expected in uri for uri in resource_uris)
    
    @pytest.mark.asyncio
    async def test_prompt_registration(self):
        """Test all prompts are properly registered."""
        server = GrantsAnalysisServer()
        prompts = await server.list_prompts()
        
        expected_prompts = [
            "landscape_analysis",
            "agency_intelligence",
            "competition_assessment",
            "funding_pattern_analysis",
            "deadline_opportunity_analysis"
        ]
        
        prompt_names = [prompt.name for prompt in prompts]
        for expected in expected_prompts:
            assert expected in prompt_names
    
    @pytest.mark.asyncio
    async def test_tool_invocation_through_mcp(self):
        """Test tool invocation through MCP protocol."""
        server = GrantsAnalysisServer()
        
        # Create in-memory transport for testing
        client_transport, server_transport = InMemoryTransport.create_pair()
        await server.connect(server_transport)
        
        # Mock API response
        with patch('mcp_server.tools.discovery.opportunity_discovery_tool.discover') as mock_discover:
            mock_discover.return_value = {
                "opportunities": [],
                "total_found": 0,
                "metadata": {"api_status": "success"}
            }
            
            # Invoke tool through MCP protocol
            result = await client_transport.call_tool(
                "opportunity_discovery",
                {"domain": "test search"}
            )
            
            assert result["total_found"] == 0
            assert result["metadata"]["api_status"] == "success"
            mock_discover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """Test handling of concurrent tool invocations."""
        server = GrantsAnalysisServer()
        
        async def call_tool(tool_name, params):
            return await server.call_tool(tool_name, params)
        
        # Simulate concurrent calls
        import asyncio
        tasks = [
            call_tool("opportunity_discovery", {"domain": f"search_{i}"})
            for i in range(5)
        ]
        
        with patch('mcp_server.tools.discovery.opportunity_discovery_tool.discover') as mock_discover:
            mock_discover.return_value = {"opportunities": [], "total_found": 0}
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert mock_discover.call_count == 5
```

### 5. Edge Case Testing Pattern

```python
"""Tests for edge cases and error conditions."""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime

from mcp_server.tools.analysis import opportunity_density_tool


class TestEdgeCases:
    """Test edge cases and unusual conditions."""
    
    @pytest.mark.asyncio
    async def test_missing_funding_data(self, sample_opportunity):
        """Test handling of opportunities with missing funding information."""
        # Remove funding data
        opportunity = sample_opportunity.copy()
        opportunity.summary["estimated_total_program_funding"] = None
        opportunity.summary["expected_number_of_awards"] = None
        
        result = await opportunity_density_tool.analyze([opportunity])
        
        assert opportunity.opportunity_id in result["density_analysis"]
        analysis = result["density_analysis"][opportunity.opportunity_id]
        assert analysis["funding_density_score"] == 0  # Or appropriate default
        assert "Missing funding data" in analysis["data_quality_issues"]
    
    @pytest.mark.asyncio
    async def test_zero_expected_awards(self, sample_opportunity):
        """Test handling of opportunities with zero expected awards."""
        opportunity = sample_opportunity.copy()
        opportunity.summary["expected_number_of_awards"] = 0
        
        result = await opportunity_density_tool.analyze([opportunity])
        
        analysis = result["density_analysis"][opportunity.opportunity_id]
        assert analysis["funding_density_score"] == float('inf')  # Or flag as unlimited
        assert "unlimited" in analysis.get("notes", "").lower()
    
    @pytest.mark.asyncio
    async def test_conflicting_award_data(self, sample_opportunity):
        """Test handling of conflicting award floor/ceiling data."""
        opportunity = sample_opportunity.copy()
        opportunity.summary["award_floor"] = 500000
        opportunity.summary["award_ceiling"] = 100000  # Floor > Ceiling
        
        result = await opportunity_density_tool.analyze([opportunity])
        
        analysis = result["density_analysis"][opportunity.opportunity_id]
        assert "data_conflict" in analysis
        assert analysis["data_conflict"]["type"] == "award_range"
        assert analysis["data_conflict"]["resolution"] == "used_most_restrictive"
    
    @pytest.mark.asyncio
    async def test_extremely_long_description(self, sample_opportunity):
        """Test handling of extremely long eligibility descriptions."""
        opportunity = sample_opportunity.copy()
        # Create a 50KB description
        opportunity.summary["applicant_eligibility_description"] = "A" * 50000
        
        from mcp_server.tools.analysis import eligibility_decoder_tool
        result = await eligibility_decoder_tool.analyze([opportunity])
        
        analysis = result["eligibility_analysis"][opportunity.opportunity_id]
        assert len(analysis["requirements"]["summary"]) < 5000  # Summarized
        assert analysis["complexity_score"] >= 7  # High complexity due to length
    
    @pytest.mark.asyncio
    async def test_malformed_date_formats(self):
        """Test handling of various malformed date formats."""
        test_dates = [
            "2024-13-45",  # Invalid month/day
            "12/31/2024",  # Wrong format
            "Dec 31, 2024",  # Text format
            "2024",  # Year only
            "",  # Empty
            None,  # None
        ]
        
        from mcp_server.tools.utils.validators import normalize_date
        
        for date_str in test_dates:
            result = normalize_date(date_str)
            # Should either return valid date or None with warning
            assert result is None or isinstance(result, datetime)
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, sample_opportunity):
        """Test handling of unicode and special characters in data."""
        opportunity = sample_opportunity.copy()
        opportunity.opportunity_title = "Research Grant 研究補助金 €500K"
        opportunity.summary["summary_description"] = "Support for • bullet points\n→ arrows\n© copyright"
        
        result = await opportunity_density_tool.analyze([opportunity])
        
        assert opportunity.opportunity_id in result["density_analysis"]
        # Should handle unicode without errors
        assert result["density_analysis"][opportunity.opportunity_id] is not None
```

### 6. Performance Testing Pattern

```python
"""Tests for performance with large datasets."""

import pytest
import time
import psutil
import asyncio
from unittest.mock import patch

from mcp_server.tools.discovery import opportunity_discovery_tool


class TestPerformance:
    """Test performance characteristics and limits."""
    
    @pytest.mark.asyncio
    async def test_large_result_set_handling(self, mock_api_client):
        """Test handling of 1000+ opportunities."""
        # Create 1000 mock opportunities
        large_dataset = [
            {
                "opportunity_id": i,
                "opportunity_title": f"Grant {i}",
                "opportunity_number": f"GRANT-{i:05d}",
                "agency_code": f"AGENCY{i % 10}",
                "summary": {"award_ceiling": i * 1000}
            }
            for i in range(1000)
        ]
        
        mock_api_client.search_opportunities.return_value = {
            "data": large_dataset,
            "pagination_info": {"total_records": 1000}
        }
        
        start_time = time.time()
        result = await opportunity_discovery_tool.discover(
            max_results=1000,
            api_client=mock_api_client
        )
        execution_time = time.time() - start_time
        
        assert len(result["opportunities"]) == 1000
        assert execution_time < 5.0  # Should complete within 5 seconds
        assert result["metadata"]["processing_time"] < 5000  # milliseconds
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, mock_api_client):
        """Test memory consumption with large datasets."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        large_dataset = [
            {
                "opportunity_id": i,
                "opportunity_title": f"Grant {i}" * 100,  # Long titles
                "summary": {"description": "X" * 10000}  # Large descriptions
            }
            for i in range(500)
        ]
        
        mock_api_client.search_opportunities.return_value = {
            "data": large_dataset,
            "pagination_info": {"total_records": 500}
        }
        
        result = await opportunity_discovery_tool.discover(
            max_results=500,
            api_client=mock_api_client
        )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 100  # Should not use more than 100MB
        assert len(result["opportunities"]) == 500
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_api_client):
        """Test multiple simultaneous tool invocations."""
        mock_api_client.search_opportunities.return_value = {
            "data": [],
            "pagination_info": {"total_records": 0}
        }
        
        async def run_discovery(index):
            return await opportunity_discovery_tool.discover(
                domain=f"search_{index}",
                api_client=mock_api_client
            )
        
        # Run 20 concurrent discoveries
        start_time = time.time()
        tasks = [run_discovery(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        execution_time = time.time() - start_time
        
        assert len(results) == 20
        assert all(r["metadata"]["api_status"] == "success" for r in results)
        assert execution_time < 10.0  # Should handle concurrent requests efficiently
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, mcp_server):
        """Test cache hit performance improvement."""
        with patch('mcp_server.tools.discovery.opportunity_discovery_tool.discover') as mock_discover:
            mock_discover.return_value = {"opportunities": [], "total_found": 0}
            
            # First call - cache miss
            start_time = time.time()
            result1 = await mcp_server.call_tool("opportunity_discovery", {"domain": "test"})
            first_call_time = time.time() - start_time
            
            # Second call - cache hit
            start_time = time.time()
            result2 = await mcp_server.call_tool("opportunity_discovery", {"domain": "test"})
            second_call_time = time.time() - start_time
            
            assert mock_discover.call_count == 1  # Only called once due to cache
            assert second_call_time < first_call_time * 0.1  # Cache hit should be 10x faster
```

## Test Fixtures

### API Response Fixtures (`fixtures/api_responses.py`)

```python
"""Mock API response fixtures for testing."""

from datetime import datetime, timedelta

# Complete opportunity response
MOCK_OPPORTUNITIES_FULL = [
    {
        "opportunity_id": 12345,
        "opportunity_number": "NSF-2024-001",
        "opportunity_title": "Climate Research Initiative",
        "opportunity_status": "posted",
        "agency_code": "NSF",
        "agency_name": "National Science Foundation",
        "summary": {
            "award_ceiling": 500000,
            "award_floor": 100000,
            "estimated_total_program_funding": 10000000,
            "expected_number_of_awards": 20,
            "post_date": "2024-01-15",
            "close_date": "2024-03-15",
            "summary_description": "Support for climate research",
            "applicant_eligibility_description": "Universities"
        },
        "category": "Science and Technology"
    },
    # Add more mock opportunities...
]

# Opportunity with missing fields
MOCK_OPPORTUNITIES_PARTIAL = [
    {
        "opportunity_id": 67890,
        "opportunity_number": "DOE-2024-002",
        "opportunity_title": "Energy Research",
        "agency_code": "DOE",
        # Missing summary fields
        "summary": {
            "post_date": "2024-02-01",
            # Missing award information
        }
    }
]

# Empty result
MOCK_OPPORTUNITIES_EMPTY = []

# Error responses
MOCK_ERROR_RESPONSES = {
    "validation_error": {
        "error": {
            "code": 422,
            "message": "Validation failed",
            "details": {
                "field": "filters.date_range",
                "issue": "Invalid date format"
            }
        }
    },
    "rate_limit": {
        "error": {
            "code": 429,
            "message": "Rate limit exceeded",
            "retry_after": 60
        }
    },
    "server_error": {
        "error": {
            "code": 503,
            "message": "Service temporarily unavailable"
        }
    }
}
```

## Test Execution Strategy

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=mcp_server --cov-report=html

# Run specific test categories
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest tests/edge_cases/        # Edge case tests only
pytest tests/performance/       # Performance tests only

# Run tests matching pattern
pytest tests/ -k "api"          # Run all API-related tests
pytest tests/ -k "discovery"    # Run discovery tool tests

# Run with markers
pytest tests/ -m "slow"         # Run slow tests
pytest tests/ -m "not slow"     # Skip slow tests

# Parallel execution
pytest tests/ -n 4              # Run with 4 parallel workers
```

### Test Markers

```python
# In test files, mark tests appropriately:

@pytest.mark.slow
async def test_large_dataset_processing():
    """This test takes more than 1 second."""
    pass

@pytest.mark.integration
async def test_real_api_call():
    """This test requires API access."""
    pass

@pytest.mark.critical
async def test_core_functionality():
    """This test must pass for release."""
    pass
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run unit tests
      run: pytest tests/unit/ --cov=mcp_server
    
    - name: Run integration tests
      run: pytest tests/integration/ -m "not slow"
    
    - name: Run edge case tests
      run: pytest tests/edge_cases/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Quality Assurance Checklist

### Pre-Release Testing

- [ ] **Unit Tests**: All individual components tested
  - [ ] 100% coverage for critical paths
  - [ ] All error conditions tested
  - [ ] Mock API responses validated

- [ ] **Integration Tests**: Complete workflows tested
  - [ ] MCP protocol compliance verified
  - [ ] Tool registration confirmed
  - [ ] Resource access validated
  - [ ] Prompt generation tested

- [ ] **Edge Cases**: All known edge cases handled
  - [ ] Missing data scenarios
  - [ ] Malformed responses
  - [ ] Network failures
  - [ ] Rate limiting
  - [ ] Data conflicts

- [ ] **Performance**: Acceptable performance verified
  - [ ] Large dataset handling (1000+ items)
  - [ ] Memory usage under 100MB for typical operations
  - [ ] Concurrent operations supported
  - [ ] Cache effectiveness confirmed

- [ ] **API Interaction**: External API properly mocked/tested
  - [ ] All endpoints covered
  - [ ] Error responses handled
  - [ ] Retry logic verified
  - [ ] Rate limiting respected

### Test Coverage Goals

- **Overall Coverage**: Minimum 85%
- **Critical Paths**: 100% coverage
- **Error Handlers**: 100% coverage
- **Edge Cases**: Explicit tests for all identified cases
- **Performance**: Benchmarks established and maintained

## Best Practices Applied

1. **From quick-data-mcp**:
   - Fixture-based test data management
   - Clear test class organization
   - Comprehensive async testing
   - State cleanup between tests
   - Mock API responses for reliability

2. **MCP-Specific**:
   - Protocol compliance testing
   - Tool/Resource/Prompt registration validation
   - Server lifecycle testing
   - Transport layer testing

3. **API Testing**:
   - Complete mock response sets
   - Error scenario coverage
   - Rate limit simulation
   - Network failure handling

4. **Performance**:
   - Memory usage monitoring
   - Execution time benchmarks
   - Concurrent operation testing
   - Cache effectiveness validation

This comprehensive testing strategy ensures your Grants Analysis MCP is robust, reliable, and ready for production use while maintaining compliance with MCP standards and handling real-world API interactions gracefully.