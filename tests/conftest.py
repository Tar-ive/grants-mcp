"""Test configuration following testing_v3.md specifications."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Add src to Python path for tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server.config.settings import Settings
from mcp_server.models.grants_schemas import AgencyV1, OpportunityV1
from mcp_server.server import GrantsAnalysisServer
from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from mcp_server.tools.utils.cache_manager import InMemoryCache

# Load environment variables
load_dotenv(Path(__file__).parent / ".env.test", override=True)
load_dotenv(Path(__file__).parent.parent / ".env")

# Test configuration
TEST_API_KEY = os.getenv("API_KEY", "test_api_key_12345")
REAL_API_KEY = os.getenv("API_KEY", "test_key")  # Will use real key from .env
USE_REAL_API = os.getenv("USE_REAL_API", "false").lower() == "true"
API_BASE_URL = "https://api.simpler.grants.gov/v1"

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
    rate_limit_requests=100,
    rate_limit_period=60,
    api_base_url=API_BASE_URL
)


@pytest.fixture
def test_mode():
    """Determine if we're using real API or mocked."""
    return USE_REAL_API


@pytest.fixture
def test_settings(test_mode):
    """Get appropriate test settings."""
    return REAL_API_SETTINGS if test_mode else TEST_SETTINGS


@pytest.fixture
def cache():
    """Create a fresh cache instance for testing."""
    return InMemoryCache(ttl=60, max_size=100)


@pytest_asyncio.fixture
async def mcp_server(test_settings):
    """Get MCP server instance configured for testing."""
    server = GrantsAnalysisServer(settings=test_settings)
    yield server
    await server.api_client.close()


@pytest_asyncio.fixture
async def real_api_client():
    """Create a real API client for integration tests."""
    client = SimplerGrantsAPIClient(
        api_key=REAL_API_KEY,
        base_url=API_BASE_URL
    )
    yield client
    await client.close()


@pytest_asyncio.fixture
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
        client.check_health = AsyncMock()
        client.close = AsyncMock()
        yield client


@pytest.fixture
def sample_opportunity():
    """Create a sample opportunity for testing."""
    return {
        "opportunity_id": 12345,
        "opportunity_number": "TEST-2024-001",
        "opportunity_title": "Test Grant Opportunity",
        "opportunity_status": "posted",
        "agency": "TEST",
        "agency_code": "TST",
        "agency_name": "Test Agency",
        "category": "Science and Technology",
        "summary": {
            "award_ceiling": 500000,
            "award_floor": 100000,
            "estimated_total_program_funding": 5000000,
            "expected_number_of_awards": 10,
            "post_date": "2024-01-01",
            "close_date": "2024-03-31",
            "summary_description": "Test grant for research projects",
            "applicant_eligibility_description": "Universities and research institutions",
            "additional_info_url": "https://example.com/grant-info",
            "agency_email_address": "grants@test.gov",
            "agency_phone_number": "555-0100"
        }
    }


@pytest.fixture
def sample_api_response(sample_opportunity):
    """Create a sample API response for testing."""
    return {
        "data": [sample_opportunity],
        "pagination_info": {
            "page_size": 25,
            "page_number": 1,
            "total_records": 1,
            "total_pages": 1
        },
        "facet_counts": {
            "agency": {"TST": 1}
        }
    }


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


# Register custom markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "real_api: marks tests requiring real API")
    config.addinivalue_line("markers", "mock_only: marks tests that should only use mocks")
    config.addinivalue_line("markers", "rate_limited: marks tests that consume significant API quota")
    config.addinivalue_line("markers", "performance: marks performance benchmark tests")
    config.addinivalue_line("markers", "contract: marks API contract tests")
    config.addinivalue_line("markers", "slow: marks tests that take a long time to run")