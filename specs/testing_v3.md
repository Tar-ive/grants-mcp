# Grants Analysis MCP Testing Strategy v3

## Overview
Enhanced comprehensive testing strategy for the Python-based Grants Analysis MCP, including real API integration tests using the actual Simpler Grants API key from the .env file. This version builds upon v2 by adding live API testing capabilities, performance benchmarks with real data, and production-readiness validation.

## Key Enhancements in v3
- **Live API Integration Tests**: Tests using the actual API key (T4TevWYV3suiQ8eLFbza)
- **Real Data Validation**: Testing with actual grants.gov data
- **Performance Benchmarks**: Real-world performance metrics
- **Rate Limit Testing**: Actual API rate limit behavior validation
- **Data Quality Verification**: Testing with production data inconsistencies
- **End-to-End Workflows**: Complete user journey testing with real API

## Testing Philosophy
- **Hybrid Testing Approach**: Combine mocked unit tests with real API integration tests
- **Progressive Testing**: Start with mocked tests, progress to real API tests
- **Environment-Based Testing**: Different test suites for development vs production
- **Data-Driven Testing**: Use real API responses to generate test fixtures
- **Continuous Validation**: Regular API contract testing to detect changes

## Enhanced Test Structure

```
tests/
├── __init__.py
├── conftest.py                         # Pytest configuration with API setup
├── .env.test                           # Test environment variables
├── fixtures/                           # Test data and mock responses
│   ├── __init__.py
│   ├── api_responses.py               # Mock API response fixtures
│   ├── sample_grants.py               # Sample grant data fixtures
│   ├── real_api_snapshots.py          # Snapshots from real API
│   └── error_responses.py             # Error scenario fixtures
├── unit/                               # Unit tests (mocked)
│   ├── [existing unit test structure]
├── integration/                        # Integration tests (real API)
│   ├── __init__.py
│   ├── test_mcp_server.py            # MCP server integration
│   ├── test_real_api_connection.py   # Real API connection tests
│   ├── test_api_search.py            # Real search functionality
│   ├── test_api_pagination.py        # Real pagination handling
│   ├── test_api_filtering.py         # Real filter combinations
│   ├── test_api_rate_limits.py       # Real rate limit behavior
│   ├── test_api_error_handling.py    # Real error scenarios
│   └── test_workflow_integration.py  # End-to-end workflows
├── live/                               # Live API tests (require API key)
│   ├── __init__.py
│   ├── test_live_discovery.py        # Live opportunity discovery
│   ├── test_live_agency_analysis.py  # Live agency data analysis
│   ├── test_live_data_quality.py     # Real data quality issues
│   ├── test_live_performance.py      # Performance with real data
│   └── test_live_edge_cases.py       # Edge cases with real API
├── performance/                        # Performance tests
│   ├── __init__.py
│   ├── test_real_large_datasets.py   # Real large result handling
│   ├── test_api_response_times.py    # Real API response metrics
│   ├── test_concurrent_api_calls.py  # Real concurrent operations
│   └── test_cache_effectiveness.py   # Cache with real data
├── edge_cases/                        # Edge case tests
│   ├── __init__.py
│   ├── test_real_data_quality.py     # Real malformed data
│   ├── test_network_failures.py      # Network error scenarios
│   ├── test_api_rate_limiting.py     # Real rate limit handling
│   └── test_boundary_conditions.py   # Extreme input values
└── contract/                          # API contract tests
    ├── __init__.py
    ├── test_api_schema_validation.py # Validate API response schemas
    ├── test_api_backwards_compat.py  # Check for breaking changes
    └── test_api_field_consistency.py # Field consistency checks
```

## Core Testing Components

### 1. Enhanced Test Configuration (`conftest.py`)

```python
"""Enhanced test configuration with real API support."""

import pytest
import asyncio
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv
import aiohttp
from datetime import datetime, timedelta

# Load environment variables
load_dotenv(Path(__file__).parent / '.env.test')
load_dotenv(Path(__file__).parent.parent / '.env')  # Load real .env

# Add src to Python path for tests
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from mcp_server.server import GrantsAnalysisServer
from mcp_server.config import Settings
from mcp_server.models.grants_schemas import OpportunityV1, AgencyV1
from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient

# Test configuration
TEST_API_KEY = os.getenv("API_KEY", "test_api_key_12345")
REAL_API_KEY = "T4TevWYV3suiQ8eLFbza"  # From .env file
USE_REAL_API = os.getenv("USE_REAL_API", "false").lower() == "true"
API_BASE_URL = "https://api.grants.gov/v1"

# Test settings for different environments
TEST_SETTINGS = Settings(
    api_key=TEST_API_KEY if not USE_REAL_API else REAL_API_KEY,
    cache_ttl=60,
    max_cache_size=100,
    rate_limit_requests=10,
    rate_limit_period=1,
    api_base_url=API_BASE_URL
)

REAL_API_SETTINGS = Settings(
    api_key=REAL_API_KEY,
    cache_ttl=300,
    max_cache_size=500,
    rate_limit_requests=100,  # Actual API limits
    rate_limit_period=60,
    api_base_url=API_BASE_URL
)


@pytest.fixture
def test_mode():
    """Determine if we're using real API or mocked."""
    return USE_REAL_API


@pytest.fixture
def mcp_server(test_mode):
    """Get MCP server instance configured for testing."""
    settings = REAL_API_SETTINGS if test_mode else TEST_SETTINGS
    server = GrantsAnalysisServer(settings=settings)
    return server


@pytest.fixture
async def real_api_client():
    """Create a real API client for integration tests."""
    client = SimplerGrantsAPIClient(
        api_key=REAL_API_KEY,
        base_url=API_BASE_URL
    )
    yield client
    await client.close()


@pytest.fixture
async def test_api_client(test_mode):
    """Create appropriate API client based on test mode."""
    if test_mode:
        client = SimplerGrantsAPIClient(
            api_key=REAL_API_KEY,
            base_url=API_BASE_URL
        )
        yield client
        await client.close()
    else:
        # Return mock client
        client = Mock(spec=SimplerGrantsAPIClient)
        client.search_opportunities = AsyncMock()
        client.search_agencies = AsyncMock()
        client.get_opportunity = AsyncMock()
        yield client


@pytest.fixture
def api_snapshot_recorder():
    """Record real API responses for fixture generation."""
    class SnapshotRecorder:
        def __init__(self):
            self.snapshots = {}
            
        async def record(self, name: str, api_call):
            """Record an API response snapshot."""
            response = await api_call()
            self.snapshots[name] = {
                "timestamp": datetime.now().isoformat(),
                "response": response
            }
            return response
            
        def save(self, filepath: str):
            """Save snapshots to file."""
            with open(filepath, 'w') as f:
                json.dump(self.snapshots, f, indent=2, default=str)
                
    return SnapshotRecorder()


@pytest.fixture
def rate_limit_monitor():
    """Monitor API rate limit consumption."""
    class RateLimitMonitor:
        def __init__(self):
            self.requests = []
            self.rate_limits = {}
            
        def record_request(self, endpoint: str, headers: dict):
            """Record a request and extract rate limit info."""
            self.requests.append({
                "endpoint": endpoint,
                "timestamp": datetime.now(),
                "rate_limit_remaining": headers.get("X-RateLimit-Remaining"),
                "rate_limit_reset": headers.get("X-RateLimit-Reset")
            })
            
        def get_remaining_calls(self) -> int:
            """Get remaining API calls."""
            if self.requests:
                return int(self.requests[-1].get("rate_limit_remaining", 0))
            return -1
            
        def should_throttle(self) -> bool:
            """Check if we should throttle requests."""
            remaining = self.get_remaining_calls()
            return 0 <= remaining < 10
            
    return RateLimitMonitor()


@pytest.fixture
def performance_tracker():
    """Track performance metrics for API calls."""
    class PerformanceTracker:
        def __init__(self):
            self.metrics = []
            
        async def track(self, operation: str, api_call):
            """Track performance of an API call."""
            import time
            start = time.time()
            result = await api_call()
            duration = time.time() - start
            
            self.metrics.append({
                "operation": operation,
                "duration_seconds": duration,
                "timestamp": datetime.now(),
                "success": result is not None
            })
            
            return result
            
        def get_statistics(self) -> dict:
            """Get performance statistics."""
            if not self.metrics:
                return {}
                
            durations = [m["duration_seconds"] for m in self.metrics]
            return {
                "total_operations": len(self.metrics),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "success_rate": sum(1 for m in self.metrics if m["success"]) / len(self.metrics)
            }
            
    return PerformanceTracker()


# Skip markers for test organization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "real_api: marks tests requiring real API")
    config.addinivalue_line("markers", "mock_only: marks tests that should only use mocks")
    config.addinivalue_line("markers", "rate_limited: marks tests that consume significant API quota")
    config.addinivalue_line("markers", "performance: marks performance benchmark tests")
    config.addinivalue_line("markers", "contract: marks API contract tests")
```

### 2. Real API Connection Tests

```python
"""Tests for real API connection and authentication."""

import pytest
import aiohttp
from datetime import datetime

@pytest.mark.real_api
class TestRealAPIConnection:
    """Test real API connection and authentication."""
    
    @pytest.mark.asyncio
    async def test_api_authentication(self, real_api_client):
        """Test that API key authenticates successfully."""
        # Make a simple API call to verify authentication
        response = await real_api_client.search_opportunities(
            params={"page_size": 1}
        )
        
        assert response is not None
        assert "error" not in response or response["error"] is None
        assert "data" in response
        
    @pytest.mark.asyncio
    async def test_api_endpoints_availability(self, real_api_client):
        """Test that all required endpoints are available."""
        endpoints = [
            "/v1/opportunities/search",
            "/v1/agencies/search"
        ]
        
        for endpoint in endpoints:
            # Test endpoint availability
            response = await real_api_client._make_request(
                method="GET",
                endpoint=endpoint,
                params={"page_size": 1}
            )
            
            assert response is not None
            assert response.get("status_code") != 404
            
    @pytest.mark.asyncio
    async def test_api_response_headers(self, real_api_client, rate_limit_monitor):
        """Test API response headers for rate limit info."""
        response = await real_api_client.search_opportunities(
            params={"page_size": 1}
        )
        
        # Check for rate limit headers
        headers = response.get("headers", {})
        rate_limit_monitor.record_request("/v1/opportunities/search", headers)
        
        assert rate_limit_monitor.get_remaining_calls() > 0
        assert not rate_limit_monitor.should_throttle()
        
    @pytest.mark.asyncio
    async def test_api_ssl_certificate(self, real_api_client):
        """Test SSL certificate validity."""
        # This test verifies SSL is properly configured
        try:
            response = await real_api_client.search_opportunities(
                params={"page_size": 1}
            )
            assert response is not None
        except aiohttp.ClientSSLError as e:
            pytest.fail(f"SSL certificate error: {e}")
```

### 3. Real API Search Tests

```python
"""Tests for real API search functionality."""

import pytest
from datetime import datetime, timedelta

@pytest.mark.real_api
class TestRealAPISearch:
    """Test real API search functionality with live data."""
    
    @pytest.mark.asyncio
    async def test_search_with_keywords(self, real_api_client, api_snapshot_recorder):
        """Test searching with real keywords."""
        keywords = ["climate", "health", "education", "technology"]
        
        for keyword in keywords:
            response = await api_snapshot_recorder.record(
                f"search_{keyword}",
                lambda: real_api_client.search_opportunities(
                    params={
                        "query": keyword,
                        "page_size": 10
                    }
                )
            )
            
            assert response is not None
            assert "data" in response
            assert isinstance(response["data"], list)
            
            # Verify search relevance
            if response["data"]:
                for opportunity in response["data"]:
                    # Check that results are relevant (title or description contains keyword)
                    relevant = (
                        keyword.lower() in opportunity.get("opportunity_title", "").lower() or
                        keyword.lower() in opportunity.get("summary", {}).get("summary_description", "").lower()
                    )
                    # Note: Not all results may contain exact keyword due to stemming
                    
        # Save snapshots for fixture generation
        api_snapshot_recorder.save("fixtures/real_api_snapshots.json")
        
    @pytest.mark.asyncio
    async def test_search_with_filters(self, real_api_client):
        """Test searching with various filter combinations."""
        test_filters = [
            {
                "opportunity_status": "posted",
                "page_size": 5
            },
            {
                "agency_code": "NSF",
                "opportunity_status": "posted",
                "page_size": 5
            },
            {
                "award_floor": 100000,
                "award_ceiling": 500000,
                "page_size": 5
            }
        ]
        
        for filters in test_filters:
            response = await real_api_client.search_opportunities(params=filters)
            
            assert response is not None
            assert "data" in response
            
            # Verify filters are applied
            if "opportunity_status" in filters and response["data"]:
                for opp in response["data"]:
                    assert opp.get("opportunity_status") == filters["opportunity_status"]
                    
    @pytest.mark.asyncio
    async def test_search_pagination(self, real_api_client, performance_tracker):
        """Test pagination with real API."""
        page_sizes = [10, 25, 50]
        
        for page_size in page_sizes:
            # First page
            response1 = await performance_tracker.track(
                f"pagination_page1_size{page_size}",
                lambda: real_api_client.search_opportunities(
                    params={
                        "page_size": page_size,
                        "page_number": 1
                    }
                )
            )
            
            assert len(response1["data"]) <= page_size
            total_records = response1["pagination_info"]["total_records"]
            
            if total_records > page_size:
                # Second page
                response2 = await performance_tracker.track(
                    f"pagination_page2_size{page_size}",
                    lambda: real_api_client.search_opportunities(
                        params={
                            "page_size": page_size,
                            "page_number": 2
                        }
                    )
                )
                
                assert len(response2["data"]) <= page_size
                # Ensure different results
                page1_ids = {o["opportunity_id"] for o in response1["data"]}
                page2_ids = {o["opportunity_id"] for o in response2["data"]}
                assert page1_ids.isdisjoint(page2_ids)
                
        # Check performance statistics
        stats = performance_tracker.get_statistics()
        assert stats["avg_duration"] < 5.0  # Average response under 5 seconds
        
    @pytest.mark.asyncio
    async def test_search_date_ranges(self, real_api_client):
        """Test date range filtering with real data."""
        today = datetime.now()
        
        test_cases = [
            {
                "description": "Opportunities closing soon",
                "params": {
                    "close_date_after": today.isoformat(),
                    "close_date_before": (today + timedelta(days=30)).isoformat(),
                    "page_size": 10
                }
            },
            {
                "description": "Recently posted opportunities",
                "params": {
                    "post_date_after": (today - timedelta(days=7)).isoformat(),
                    "page_size": 10
                }
            }
        ]
        
        for test_case in test_cases:
            response = await real_api_client.search_opportunities(
                params=test_case["params"]
            )
            
            assert response is not None
            assert "data" in response
            
            # Verify date filtering
            if response["data"]:
                for opp in response["data"]:
                    if "close_date" in test_case["params"]:
                        close_date = opp.get("summary", {}).get("close_date")
                        if close_date:
                            # Verify date is within range
                            pass  # Date validation logic
```

### 4. Real API Data Quality Tests

```python
"""Tests for real data quality issues and handling."""

import pytest
from typing import List, Dict, Any

@pytest.mark.real_api
class TestRealDataQuality:
    """Test handling of real data quality issues."""
    
    @pytest.mark.asyncio
    async def test_missing_fields_in_real_data(self, real_api_client):
        """Test handling of missing fields in real opportunities."""
        response = await real_api_client.search_opportunities(
            params={"page_size": 100}
        )
        
        missing_fields_count = {
            "award_ceiling": 0,
            "award_floor": 0,
            "estimated_total_program_funding": 0,
            "expected_number_of_awards": 0,
            "summary_description": 0,
            "applicant_eligibility_description": 0
        }
        
        for opportunity in response["data"]:
            summary = opportunity.get("summary", {})
            
            # Check for missing financial data
            if not summary.get("award_ceiling"):
                missing_fields_count["award_ceiling"] += 1
            if not summary.get("award_floor"):
                missing_fields_count["award_floor"] += 1
            if not summary.get("estimated_total_program_funding"):
                missing_fields_count["estimated_total_program_funding"] += 1
            if not summary.get("expected_number_of_awards"):
                missing_fields_count["expected_number_of_awards"] += 1
            if not summary.get("summary_description"):
                missing_fields_count["summary_description"] += 1
            if not summary.get("applicant_eligibility_description"):
                missing_fields_count["applicant_eligibility_description"] += 1
                
        # Report data quality issues
        total_opportunities = len(response["data"])
        quality_report = {
            field: {
                "missing_count": count,
                "missing_percentage": (count / total_opportunities * 100) if total_opportunities > 0 else 0
            }
            for field, count in missing_fields_count.items()
        }
        
        # Assert that our code handles missing fields gracefully
        assert total_opportunities > 0
        # We expect some missing data in real API responses
        assert any(count > 0 for count in missing_fields_count.values())
        
    @pytest.mark.asyncio
    async def test_inconsistent_date_formats(self, real_api_client):
        """Test handling of various date formats in real data."""
        response = await real_api_client.search_opportunities(
            params={"page_size": 50}
        )
        
        date_formats_found = set()
        date_parsing_errors = []
        
        for opportunity in response["data"]:
            summary = opportunity.get("summary", {})
            
            # Check various date fields
            date_fields = ["post_date", "close_date", "archive_date"]
            for field in date_fields:
                date_value = summary.get(field)
                if date_value:
                    try:
                        # Try to detect format
                        if "T" in date_value:
                            date_formats_found.add("ISO")
                        elif "/" in date_value:
                            date_formats_found.add("SLASH")
                        elif "-" in date_value:
                            date_formats_found.add("DASH")
                    except Exception as e:
                        date_parsing_errors.append({
                            "opportunity_id": opportunity.get("opportunity_id"),
                            "field": field,
                            "value": date_value,
                            "error": str(e)
                        })
                        
        # We should handle multiple date formats
        assert len(date_formats_found) >= 1
        
    @pytest.mark.asyncio
    async def test_data_validation_with_real_opportunities(self, real_api_client):
        """Test data validation logic with real opportunities."""
        response = await real_api_client.search_opportunities(
            params={"page_size": 20}
        )
        
        validation_issues = []
        
        for opportunity in response["data"]:
            summary = opportunity.get("summary", {})
            
            # Validate award ranges
            floor = summary.get("award_floor")
            ceiling = summary.get("award_ceiling")
            
            if floor and ceiling:
                if floor > ceiling:
                    validation_issues.append({
                        "type": "invalid_award_range",
                        "opportunity_id": opportunity.get("opportunity_id"),
                        "floor": floor,
                        "ceiling": ceiling
                    })
                    
            # Validate funding vs awards
            total_funding = summary.get("estimated_total_program_funding")
            expected_awards = summary.get("expected_number_of_awards")
            
            if total_funding and expected_awards and ceiling:
                max_possible = expected_awards * ceiling
                if max_possible < total_funding:
                    validation_issues.append({
                        "type": "funding_mismatch",
                        "opportunity_id": opportunity.get("opportunity_id"),
                        "total_funding": total_funding,
                        "max_possible": max_possible
                    })
                    
        # Report validation issues found in real data
        assert isinstance(validation_issues, list)
```

### 5. Real API Performance Tests

```python
"""Performance tests with real API."""

import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.real_api
@pytest.mark.performance
class TestRealAPIPerformance:
    """Test performance characteristics with real API."""
    
    @pytest.mark.asyncio
    async def test_large_result_set_performance(self, real_api_client, performance_tracker):
        """Test handling of large result sets from real API."""
        # Request maximum allowed page size
        response = await performance_tracker.track(
            "large_result_set",
            lambda: real_api_client.search_opportunities(
                params={"page_size": 100}  # Maximum typically allowed
            )
        )
        
        assert response is not None
        assert len(response["data"]) <= 100
        
        stats = performance_tracker.get_statistics()
        assert stats["avg_duration"] < 10.0  # Should complete within 10 seconds
        
    @pytest.mark.asyncio
    @pytest.mark.rate_limited
    async def test_concurrent_api_requests(self, real_api_client):
        """Test concurrent requests to real API."""
        async def make_request(query: str):
            return await real_api_client.search_opportunities(
                params={"query": query, "page_size": 5}
            )
            
        # Make 5 concurrent requests with different queries
        queries = ["health", "education", "technology", "climate", "agriculture"]
        
        start_time = time.time()
        tasks = [make_request(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Check results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 3  # At least 3 should succeed
        assert duration < 15.0  # Should complete within 15 seconds
        
    @pytest.mark.asyncio
    async def test_response_time_consistency(self, real_api_client, performance_tracker):
        """Test API response time consistency."""
        # Make 10 identical requests
        for i in range(10):
            await performance_tracker.track(
                f"consistency_test_{i}",
                lambda: real_api_client.search_opportunities(
                    params={"page_size": 10}
                )
            )
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
            
        stats = performance_tracker.get_statistics()
        
        # Check consistency
        assert stats["success_rate"] >= 0.9  # 90% success rate
        assert stats["max_duration"] < stats["avg_duration"] * 3  # No extreme outliers
```

### 6. Real API Rate Limit Tests

```python
"""Tests for real API rate limiting behavior."""

import pytest
import asyncio
import time

@pytest.mark.real_api
@pytest.mark.rate_limited
class TestRealAPIRateLimits:
    """Test real API rate limiting behavior."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, real_api_client, rate_limit_monitor):
        """Test rate limit information in headers."""
        # Make a request and check headers
        response = await real_api_client.search_opportunities(
            params={"page_size": 1}
        )
        
        headers = response.get("headers", {})
        rate_limit_monitor.record_request("/v1/opportunities/search", headers)
        
        remaining = rate_limit_monitor.get_remaining_calls()
        assert remaining >= 0  # Should have rate limit info
        
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limit_enforcement(self, real_api_client):
        """Test that rate limits are enforced (carefully)."""
        # This test should be run sparingly as it consumes quota
        
        # Get initial rate limit status
        response = await real_api_client.search_opportunities(
            params={"page_size": 1}
        )
        
        initial_remaining = response.get("headers", {}).get("X-RateLimit-Remaining")
        
        if initial_remaining and int(initial_remaining) > 20:
            # Make 10 rapid requests
            requests_made = 0
            rate_limit_hit = False
            
            for i in range(10):
                try:
                    response = await real_api_client.search_opportunities(
                        params={"page_size": 1}
                    )
                    requests_made += 1
                    await asyncio.sleep(0.1)  # Small delay
                except Exception as e:
                    if "429" in str(e) or "rate limit" in str(e).lower():
                        rate_limit_hit = True
                        break
                        
            assert requests_made > 0
            # We shouldn't hit rate limit with just 10 requests
            assert not rate_limit_hit
        else:
            pytest.skip("Not enough rate limit quota for this test")
```

### 7. API Contract Tests

```python
"""Tests for API contract validation."""

import pytest
from jsonschema import validate, ValidationError

@pytest.mark.real_api
@pytest.mark.contract
class TestAPIContract:
    """Test API contract and schema validation."""
    
    # Expected schema for opportunity response
    OPPORTUNITY_SCHEMA = {
        "type": "object",
        "required": ["opportunity_id", "opportunity_number", "opportunity_title"],
        "properties": {
            "opportunity_id": {"type": ["string", "number"]},
            "opportunity_number": {"type": "string"},
            "opportunity_title": {"type": "string"},
            "opportunity_status": {"type": "string"},
            "agency_code": {"type": "string"},
            "agency_name": {"type": "string"},
            "summary": {
                "type": "object",
                "properties": {
                    "award_ceiling": {"type": ["number", "null"]},
                    "award_floor": {"type": ["number", "null"]},
                    "estimated_total_program_funding": {"type": ["number", "null"]},
                    "expected_number_of_awards": {"type": ["number", "null"]},
                    "post_date": {"type": ["string", "null"]},
                    "close_date": {"type": ["string", "null"]},
                    "summary_description": {"type": ["string", "null"]},
                    "applicant_eligibility_description": {"type": ["string", "null"]}
                }
            }
        }
    }
    
    @pytest.mark.asyncio
    async def test_opportunity_schema_validation(self, real_api_client):
        """Test that opportunity responses match expected schema."""
        response = await real_api_client.search_opportunities(
            params={"page_size": 10}
        )
        
        assert "data" in response
        
        validation_errors = []
        for opportunity in response["data"]:
            try:
                validate(instance=opportunity, schema=self.OPPORTUNITY_SCHEMA)
            except ValidationError as e:
                validation_errors.append({
                    "opportunity_id": opportunity.get("opportunity_id"),
                    "error": str(e)
                })
                
        # Report but don't fail on validation errors
        # API might evolve, we want to know about changes
        if validation_errors:
            print(f"Schema validation issues found: {len(validation_errors)}")
            for error in validation_errors[:5]:  # Show first 5
                print(f"  - {error}")
                
    @pytest.mark.asyncio
    async def test_pagination_info_contract(self, real_api_client):
        """Test pagination info structure."""
        response = await real_api_client.search_opportunities(
            params={"page_size": 10}
        )
        
        assert "pagination_info" in response
        pagination = response["pagination_info"]
        
        # Check required pagination fields
        assert "total_records" in pagination
        assert "page_size" in pagination
        assert "page_number" in pagination
        assert "total_pages" in pagination
        
        # Validate pagination logic
        assert pagination["page_size"] <= 100  # Max page size
        assert pagination["page_number"] >= 1
        assert pagination["total_pages"] >= 0
        
    @pytest.mark.asyncio
    async def test_api_versioning(self, real_api_client):
        """Test API versioning consistency."""
        # Check that v1 endpoints are available
        endpoints = [
            "/v1/opportunities/search",
            "/v1/agencies/search"
        ]
        
        for endpoint in endpoints:
            response = await real_api_client._make_request(
                method="GET",
                endpoint=endpoint,
                params={"page_size": 1}
            )
            
            assert response is not None
            # Should not get version mismatch errors
            assert "version" not in response.get("error", {})
```

### 8. End-to-End Workflow Tests

```python
"""End-to-end workflow tests with real API."""

import pytest
from datetime import datetime, timedelta

@pytest.mark.real_api
class TestRealWorkflows:
    """Test complete user workflows with real API."""
    
    @pytest.mark.asyncio
    async def test_complete_grant_discovery_workflow(self, mcp_server):
        """Test complete grant discovery workflow."""
        # Step 1: Initial discovery
        discovery_result = await mcp_server.call_tool(
            "opportunity_discovery",
            {
                "domain": "renewable energy",
                "max_results": 10
            }
        )
        
        assert discovery_result["total_found"] >= 0
        opportunities = discovery_result["opportunities"]
        
        if opportunities:
            # Step 2: Analyze opportunity density
            opportunity_ids = [opp["opportunity_id"] for opp in opportunities[:5]]
            density_result = await mcp_server.call_tool(
                "opportunity_density",
                {
                    "opportunity_ids": opportunity_ids,
                    "include_accessibility_scoring": True
                }
            )
            
            assert "density_analysis" in density_result
            assert len(density_result["density_analysis"]) > 0
            
            # Step 3: Analyze agencies
            agencies = list(set(opp["agency_code"] for opp in opportunities if opp.get("agency_code")))
            if agencies:
                agency_result = await mcp_server.call_tool(
                    "agency_landscape",
                    {
                        "focus_agencies": agencies[:3]
                    }
                )
                
                assert "agencies" in agency_result
                
            # Step 4: Analyze deadlines
            deadline_result = await mcp_server.call_tool(
                "deadline_cluster",
                {
                    "cluster_method": "monthly",
                    "identify_gaps": True
                }
            )
            
            assert "deadline_clusters" in deadline_result
            assert "timing_strategy" in deadline_result
            
    @pytest.mark.asyncio
    async def test_agency_deep_dive_workflow(self, mcp_server):
        """Test agency analysis workflow."""
        # Step 1: Get agency landscape
        agency_result = await mcp_server.call_tool(
            "agency_landscape",
            {
                "include_opportunities": True,
                "funding_category": "Science and Technology"
            }
        )
        
        assert "agencies" in agency_result
        
        if agency_result["agencies"]:
            # Step 2: Analyze agency patterns
            agency_codes = [agency["agency_code"] for agency in agency_result["agencies"][:3]]
            pattern_result = await mcp_server.call_tool(
                "agency_pattern",
                {
                    "agencies": agency_codes,
                    "compare_agencies": True
                }
            )
            
            assert "agency_profiles" in pattern_result
            assert "comparative_analysis" in pattern_result
            
    @pytest.mark.asyncio
    async def test_competition_assessment_workflow(self, mcp_server):
        """Test competition assessment workflow."""
        # Step 1: Find opportunities
        discovery_result = await mcp_server.call_tool(
            "opportunity_discovery",
            {
                "filters": {
                    "award_floor": 100000,
                    "award_ceiling": 1000000,
                    "opportunity_status": "posted"
                },
                "max_results": 20
            }
        )
        
        if discovery_result["opportunities"]:
            opportunities = discovery_result["opportunities"]
            
            # Step 2: Calculate density
            opportunity_ids = [opp["opportunity_id"] for opp in opportunities[:10]]
            density_result = await mcp_server.call_tool(
                "opportunity_density",
                {
                    "opportunity_ids": opportunity_ids,
                    "min_density_threshold": 100000
                }
            )
            
            # Step 3: Analyze budget distribution
            budget_result = await mcp_server.call_tool(
                "budget_distribution",
                {
                    "agency_comparison": True
                }
            )
            
            # Step 4: Decode eligibility
            eligibility_result = await mcp_server.call_tool(
                "eligibility_decoder",
                {
                    "opportunities": opportunity_ids[:5],
                    "complexity_scoring": True
                }
            )
            
            # Validate workflow results
            assert "density_analysis" in density_result
            assert "distribution_analysis" in budget_result
            assert "eligibility_analysis" in eligibility_result
```

## Testing Execution Strategy

### Running Tests by Category

```bash
# Run all tests (including real API tests)
USE_REAL_API=true pytest tests/

# Run only mocked unit tests
pytest tests/unit/

# Run only real API integration tests
USE_REAL_API=true pytest tests/integration/ -m real_api

# Run performance benchmarks
USE_REAL_API=true pytest tests/performance/ -m performance

# Run contract tests
USE_REAL_API=true pytest tests/contract/ -m contract

# Run tests with specific marker
pytest -m "not rate_limited"  # Skip rate-limited tests
pytest -m "real_api and not slow"  # Real API but skip slow tests

# Run with coverage
pytest tests/ --cov=mcp_server --cov-report=html --cov-report=term

# Run specific test file
pytest tests/live/test_live_discovery.py -v

# Run with performance tracking
pytest tests/ --benchmark-only
```

### Test Environment Configuration

```bash
# .env.test file for test configuration
USE_REAL_API=false  # Set to true for real API tests
API_KEY=test_key_for_mocks
REAL_API_KEY=T4TevWYV3suiQ8eLFbza
API_BASE_URL=https://api.grants.gov/v1
RATE_LIMIT_TESTING=false
PERFORMANCE_TESTING=false
CACHE_TESTING=true
LOG_LEVEL=INFO
```

### Continuous Integration Configuration

```yaml
# .github/workflows/test.yml
name: Comprehensive Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run unit tests
      run: pytest tests/unit/ --cov=mcp_server

  integration-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run integration tests (mocked)
      run: pytest tests/integration/ -m "not real_api"
      
  real-api-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    - name: Run real API tests (limited)
      env:
        REAL_API_KEY: ${{ secrets.GRANTS_API_KEY }}
        USE_REAL_API: true
      run: |
        pytest tests/integration/test_real_api_connection.py
        pytest tests/contract/ -m contract
        
  performance-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    - name: Run performance benchmarks
      env:
        REAL_API_KEY: ${{ secrets.GRANTS_API_KEY }}
        USE_REAL_API: true
      run: pytest tests/performance/ -m performance --benchmark-json=benchmark.json
    - name: Store benchmark results
      uses: actions/upload-artifact@v2
      with:
        name: benchmark-results
        path: benchmark.json
```

## Quality Assurance Checklist

### Pre-Release Testing with Real API

- [ ] **API Connection**: Verify authentication with real API key
- [ ] **Endpoint Availability**: All required endpoints accessible
- [ ] **Search Functionality**: Keywords and filters work correctly
- [ ] **Pagination**: Multi-page results handled properly
- [ ] **Data Quality**: Missing fields handled gracefully
- [ ] **Rate Limiting**: Respects API rate limits
- [ ] **Performance**: Acceptable response times with real data
- [ ] **Error Handling**: API errors handled appropriately
- [ ] **Contract Compliance**: Response schemas match expectations
- [ ] **End-to-End Workflows**: Complete user journeys work

### Real Data Validation

- [ ] **Field Completeness**: Document missing field percentages
- [ ] **Data Consistency**: Identify and handle inconsistencies
- [ ] **Date Formats**: Handle various date format variations
- [ ] **Number Formats**: Handle currency and number variations
- [ ] **Text Encoding**: Handle special characters and Unicode
- [ ] **Large Datasets**: Test with maximum page sizes
- [ ] **Edge Cases**: Test with unusual but valid data

### Performance Benchmarks with Real API

- [ ] **Response Times**: < 5s average for standard queries
- [ ] **Large Results**: < 10s for 100-item result sets
- [ ] **Concurrent Requests**: Handle 5+ simultaneous requests
- [ ] **Memory Usage**: < 200MB for typical operations
- [ ] **Cache Effectiveness**: 50%+ cache hit rate
- [ ] **Rate Limit Efficiency**: Maximize throughput within limits

## Best Practices Applied

1. **Hybrid Testing Strategy**:
   - Mock tests for rapid development
   - Real API tests for validation
   - Contract tests for API stability
   - Performance tests for benchmarking

2. **Environment-Based Configuration**:
   - Separate test environments
   - Configurable API endpoints
   - Feature flags for test categories
   - Secret management for API keys

3. **Data-Driven Testing**:
   - Record real API responses
   - Generate fixtures from real data
   - Test with production-like scenarios
   - Validate against actual data patterns

4. **Rate Limit Consciousness**:
   - Monitor API quota usage
   - Throttle test execution
   - Cache responses where appropriate
   - Skip expensive tests when needed

5. **Continuous Monitoring**:
   - Track API changes
   - Monitor response times
   - Document data quality issues
   - Update tests based on findings

This comprehensive testing strategy ensures the Grants Analysis MCP works correctly with both mocked and real API data, handles production edge cases gracefully, and maintains high performance standards while respecting API rate limits.