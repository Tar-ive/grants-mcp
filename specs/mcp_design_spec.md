# Grants Discovery & Analysis MCP Specification

## Overview
A Model Context Protocol (MCP) server that provides comprehensive analysis of the U.S. government grants ecosystem using the Simpler Grants API. This system focuses on data-driven discovery and evaluation without making assumptions about user profiles or preferences.

## Project Structure

```
grants-analysis-mcp/
├── main.py                           # Entry point
├── pyproject.toml                    # Dependencies and project config
├── .python-version                   # Python version specification
├── .mcp.json.sample                 # Sample MCP client configuration
├── README.md                        # Documentation
├── src/
│   └── mcp_server/
│       ├── __init__.py
│       ├── server.py                # Main MCP server implementation
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py          # Configuration management
│       │   └── api_config.py        # Simpler Grants API configuration
│       ├── models/
│       │   ├── __init__.py
│       │   ├── grants_schemas.py    # Pydantic models for API responses
│       │   ├── analysis_models.py   # Internal analysis data models
│       │   └── error_models.py      # Error handling models
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── landscape_analysis_prompt.py
│       │   ├── agency_intelligence_prompt.py
│       │   ├── competition_assessment_prompt.py
│       │   ├── funding_pattern_analysis_prompt.py
│       │   ├── deadline_opportunity_analysis_prompt.py
│       │   ├── eligibility_matrix_prompt.py
│       │   ├── budget_landscape_prompt.py
│       │   ├── trend_identification_prompt.py
│       │   └── opportunity_pattern_prompt.py
│       ├── resources/
│       │   ├── __init__.py
│       │   ├── api_status_resource.py
│       │   ├── search_history_resource.py
│       │   └── analysis_cache_resource.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── discovery/
│       │   │   ├── __init__.py
│       │   │   ├── opportunity_discovery_tool.py
│       │   │   ├── agency_landscape_tool.py
│       │   │   └── funding_trend_scanner_tool.py
│       │   ├── analysis/
│       │   │   ├── __init__.py
│       │   │   ├── opportunity_density_tool.py
│       │   │   ├── eligibility_decoder_tool.py
│       │   │   ├── budget_distribution_tool.py
│       │   │   └── deadline_cluster_tool.py
│       │   ├── intelligence/
│       │   │   ├── __init__.py
│       │   │   ├── agency_pattern_tool.py
│       │   │   └── opportunity_pattern_tool.py
│       │   └── utils/
│       │       ├── __init__.py
│       │       ├── api_client.py      # Simpler Grants API client
│       │       ├── data_processors.py # Data transformation utilities
│       │       ├── error_handlers.py  # Centralized error handling
│       │       └── validators.py      # Input validation utilities
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Pytest configuration and fixtures
    ├── test_api_client.py            # API client tests
    ├── test_discovery_tools.py       # Discovery tool tests
    ├── test_analysis_tools.py        # Analysis tool tests
    ├── test_intelligence_tools.py    # Intelligence tool tests
    ├── test_prompts.py               # Prompt generation tests
    ├── test_resources.py             # Resource tests
    ├── test_error_handling.py        # Error handling tests
    ├── test_edge_cases.py            # Edge case handling tests
    ├── fixtures/
    │   ├── __init__.py
    │   ├── api_responses.py          # Mock API response fixtures
    │   └── sample_data.py            # Sample data for testing
    └── integration/
        ├── __init__.py
        ├── test_api_integration.py   # API integration tests
        └── test_workflow_integration.py # End-to-end workflow tests
```

## Core Components

### 1. Resources

#### api_status_resource.py

Purpose: Provides real-time API status, health information, and authentication status
URI Pattern: grants://api/status
Data:
```python
{
    "api_health": {
        "status": "healthy|degraded|down",
        "response_time_ms": float,
        "last_successful_call": datetime,
        "known_issues": List[str]
    },
    "authentication": {
        "token_type": "jwt|api_key|user_key",
        "token_status": "valid|expired|invalid|missing",
        "token_expires": datetime,
        "permissions": List[str],
        "rate_limit": {
            "remaining_calls": int,
            "reset_time": datetime,
            "quota_limit": int
        },
        "last_auth_check": datetime
    },
    "endpoint_status": {
        "/v1/opportunities/search": "available|limited|unavailable",
        "/v1/agencies/search": "available|limited|unavailable",
        # ... other endpoints
    }
}
```

Edge Cases:

API downtime (503 responses): Cache last known good status
Rate limiting status: Track remaining quota and reset times
Partial service degradation: Monitor individual endpoint availability
Token expiration: Proactive warning before expiration
Token refresh failures: Handle refresh token flow issues
Permission changes: Detect when token permissions are reduced
Network connectivity: Distinguish between network vs API issues

#### `search_history_resource.py`
- **Purpose**: Maintains history of recent searches and their parameters
- **URI Pattern**: `grants://search/history/{session_id?}`
- **Data**: Search parameters, result counts, timestamps
- **Edge Cases**:
  - Session expiration
  - Memory limitations for long sessions
  - Concurrent session handling

#### `analysis_cache_resource.py`
- **Purpose**: Caches analysis results to avoid redundant API calls
- **URI Pattern**: `grants://cache/analysis/{cache_key}`
- **Data**: Cached opportunity analyses, agency patterns, deadline clusters
- **Edge Cases**:
  - Cache invalidation when data changes
  - Memory pressure handling
  - Stale data detection

### 2. Discovery Tools

#### `opportunity_discovery_tool.py`
**Function**: Search and filter opportunities using API parameters
**API Endpoint**: `/v1/opportunities/search`

**Parameters**:
- `domain` (str, optional): Search keywords
- `filters` (dict, optional): Filter parameters matching API schema
- `max_results` (int, default=100): Maximum opportunities to retrieve

**Returns**:
```python
{
    "opportunities": List[OpportunityV1],
    "total_found": int,
    "search_parameters": dict,
    "summary_stats": {
        "agencies": dict,
        "funding_ranges": dict,
        "deadline_distribution": dict,
        "category_breakdown": dict
    },
    "metadata": {
        "search_time": float,
        "api_status": str,
        "cache_used": bool
    }
}
```

**Edge Cases**:
- Empty result sets (return structured empty response)
- Invalid filter combinations (validate before API call)
- API timeout (implement retry logic with exponential backoff)
- Malformed API responses (robust parsing with defaults)
- Rate limiting (queue requests and throttle)
- Network failures (graceful degradation)

**Error Handling**:
- 422 Validation errors: Parse and present field-specific issues
- 503 Service unavailable: Return cached data if available
- Network timeouts: Retry with smaller page sizes
- Invalid date ranges: Suggest valid alternatives

#### `agency_landscape_tool.py`
**Function**: Map agencies and their funding focus areas
**API Endpoints**: `/v1/agencies/search`, `/v1/opportunities/search`

**Parameters**:
- `include_opportunities` (bool, default=True): Include opportunity analysis
- `focus_agencies` (List[str], optional): Specific agency codes to analyze
- `funding_category` (str, optional): Filter by category

**Returns**:
```python
{
    "agencies": List[AgencyV1],
    "agency_profiles": dict,  # Per-agency analysis
    "cross_agency_analysis": {
        "overlap_areas": List[str],
        "unique_specializations": dict,
        "collaboration_patterns": dict
    },
    "funding_landscape": {
        "total_active_agencies": int,
        "funding_distribution": dict,
        "category_specialization": dict
    }
}
```

**Edge Cases**:
- Agency with no current opportunities (include in list with zero counts)
- Agency API data inconsistencies (normalize agency codes)
- Missing agency metadata (use defaults and flag issues)

#### `funding_trend_scanner_tool.py`
**Function**: Compare current vs forecasted opportunities (limited trend analysis)
**API Limitation**: Cannot access historical data - only current pipeline analysis

**Parameters**:
- `include_forecasted` (bool, default=True): Include forecasted opportunities
- `agency_focus` (str, optional): Focus on specific agency
- `time_analysis` (bool, default=True): Analyze timing patterns

**Returns**:
```python
{
    "current_vs_forecast": {
        "posted_count": int,
        "forecasted_count": int,
        "transition_analysis": dict
    },
    "pipeline_indicators": {
        "emerging_categories": List[str],
        "agency_activity_changes": dict,
        "seasonal_patterns": dict
    },
    "limitations": {
        "no_historical_data": bool,
        "analysis_scope": str
    }
}
```

**Edge Cases**:
- No forecasted opportunities available
- Inconsistent date formatting in forecasted vs posted
- Missing fiscal year information

### 3. Analysis Tools

#### `opportunity_density_tool.py`
**Function**: Calculate funding density and accessibility metrics
**Formula**: `Density = estimated_total_program_funding ÷ expected_number_of_awards`

**Parameters**:
- `opportunity_ids` (List[str]): Specific opportunities to analyze
- `min_density_threshold` (int, optional): Minimum density filter
- `include_accessibility_scoring` (bool, default=True): Include barrier analysis

**Returns**:
```python
{
    "density_analysis": {
        "opportunity_id": {
            "funding_density_score": float,
            "accessibility_score": int,  # 1-10 scale
            "resource_requirements": dict,
            "barrier_analysis": dict
        }
    },
    "rankings": {
        "by_density": List[str],
        "by_accessibility": List[str]
    },
    "insights": List[str]
}
```

**Edge Cases**:
- Missing `estimated_total_program_funding` (use award ceiling * expected awards)
- Zero expected awards (flag as unlimited/unknown)
- Missing eligibility descriptions (score as medium complexity)
- Conflicting award floor/ceiling data (use most restrictive)

**Industry Best Practices for Competition Analysis**:
- **Funding Density**: Higher density typically indicates better value/opportunity ratio
- **Accessibility Scoring**: Based on eligibility complexity, geographic restrictions, institutional requirements
- **Resource Requirements**: Assessment of matching funds, facilities, personnel needs

#### `budget_distribution_tool.py`
**Function**: Analyze funding availability across award size tiers
**API Data**: `award_ceiling`, `award_floor`, `estimated_total_program_funding`

**Parameters**:
- `category` (str, optional): Filter by funding category
- `size_focus` (str, optional): Focus on specific size tier
- `agency_comparison` (bool, default=False): Compare across agencies

**Funding Tiers**:
- Micro: < $50K
- Small: $50K - $250K
- Medium: $250K - $1M
- Large: $1M - $5M
- Major: > $5M

**Returns**:
```python
{
    "distribution_analysis": {
        "tier_name": {
            "total_funding": int,
            "opportunity_count": int,
            "average_award": float,
            "agencies": List[str]
        }
    },
    "strategic_insights": {
        "underserved_tiers": List[str],
        "oversaturated_tiers": List[str],
        "optimal_sizing": dict
    }
}
```

**Edge Cases**:
- Opportunities with only floor or ceiling specified (estimate missing value)
- Zero or negative award amounts (flag as data quality issues)
- Missing total program funding (calculate from award range * expected awards)

#### `deadline_cluster_tool.py`
**Function**: Analyze deadline patterns and identify timing strategies
**Industry Best Practices**:
- **Monthly clustering**: Government fiscal year (Oct-Sep) creates seasonal patterns
- **Agency timing**: Each agency has preferred announcement cycles
- **Competitive timing**: Some periods have higher application volumes

**Parameters**:
- `cluster_method` (str, default="monthly"): Clustering approach
- `agency_focus` (List[str], optional): Focus on specific agencies
- `identify_gaps` (bool, default=True): Find low-competition windows

**Clustering Methods**:
- **Monthly**: Group by calendar month
- **Quarterly**: Group by fiscal/calendar quarters  
- **Agency**: Group by agency-specific patterns
- **Category**: Group by funding category timing

**Returns**:
```python
{
    "deadline_clusters": {
        "cluster_name": {
            "opportunities": List[str],
            "deadline_range": dict,
            "estimated_competition": str,  # high/medium/low
            "preparation_time": dict
        }
    },
    "timing_strategy": {
        "low_competition_windows": List[dict],
        "high_competition_periods": List[dict],
        "optimal_sequences": List[dict]
    }
}
```

**Edge Cases**:
- Missing deadline information (use forecasted dates)
- Past deadlines still in API (filter out automatically)
- Inconsistent date formats (normalize all dates)
- Rolling deadlines (mark as continuous opportunity)

#### `eligibility_decoder_tool.py`
**Function**: Parse and categorize complex eligibility requirements
**API Data**: `applicant_types`, `applicant_eligibility_description`

**Parameters**:
- `opportunities` (List[str]): Opportunities to analyze
- `complexity_scoring` (bool, default=True): Score requirement complexity
- `institution_type` (str, optional): Filter for specific institution types

**Complexity Scoring**:
- Simple (1-3): Basic institution type requirements
- Moderate (4-6): Multiple requirements, some restrictions
- Complex (7-10): Extensive requirements, multiple barriers

**Returns**:
```python
{
    "eligibility_analysis": {
        "opportunity_id": {
            "complexity_score": int,
            "requirements": {
                "institution_types": List[str],
                "geographic_restrictions": List[str],
                "experience_requirements": List[str],
                "collaboration_mandates": List[str]
            },
            "barriers": List[str],
            "qualifications_needed": List[str]
        }
    },
    "summary": {
        "most_accessible": List[str],
        "highest_barriers": List[str],
        "common_requirements": dict
    }
}
```

**Edge Cases**:
- Missing eligibility descriptions (flag for manual review)
- Contradictory applicant types vs description (highlight conflicts)
- Extremely long descriptions (summarize key points)
- Legal language complexity (simplify where possible)

### 4. Intelligence Tools

#### `agency_pattern_tool.py`
**Function**: Analyze agency-specific funding behaviors
**Analysis Approach**: Statistical pattern recognition in current opportunity portfolios

**Parameters**:
- `agencies` (List[str]): Agencies to analyze
- `compare_agencies` (bool, default=False): Comparative analysis
- `focus_area` (str, optional): Specific analysis focus

**Analysis Dimensions**:
- Funding preferences (amounts, duration, categories)
- Geographic distribution patterns
- Institution type preferences
- Collaboration vs individual project preferences
- Innovation vs established research balance

**Returns**:
```python
{
    "agency_profiles": {
        "agency_code": {
            "funding_personality": dict,
            "preferences": {
                "typical_award_range": tuple,
                "preferred_categories": List[str],
                "institution_favorability": dict,
                "geographic_patterns": dict
            },
            "strategic_insights": List[str]
        }
    },
    "comparative_analysis": dict,
    "recommendations": dict
}
```

#### `opportunity_pattern_tool.py`
**Function**: Identify patterns in current opportunity characteristics
**Limitation**: Can only analyze current opportunities, not historical success patterns

**Parameters**:
- `category` (str, optional): Focus on specific category
- `focus` (str, default="all"): Analysis focus area
- `include_agency_patterns` (bool, default=True): Include agency analysis

**Pattern Types**:
- Structural patterns (duration, team requirements, budget structures)
- Category-specific trends
- Cross-agency collaboration indicators
- Innovation vs traditional research balance

**Returns**:
```python
{
    "pattern_analysis": {
        "structural_patterns": dict,
        "category_patterns": dict,
        "collaboration_patterns": dict,
        "innovation_indicators": dict
    },
    "insights": List[str],
    "recommendations": List[str]
}
```

## Prompts

### Prompt Specifications

Each prompt should:
1. **Set Clear Objectives**: Specific, measurable goals for the analysis
2. **Provide Context**: Explain what data is available and limitations
3. **Offer Commands**: Specific tool invocations with examples
4. **Address Edge Cases**: Mention potential data quality issues
5. **Guide Next Steps**: Progressive workflow recommendations

#### Key Prompt Features:
- **Limitation Awareness**: Clearly state API constraints
- **Edge Case Handling**: Address common data issues
- **Progressive Workflow**: Guide users through analysis steps
- **Actionable Intelligence**: Focus on specific insights
- **Error Recovery**: Suggest alternatives when primary data unavailable

## Error Handling Strategy

### API Error Classification

#### **Network/Connection Errors**
```python
class NetworkErrorHandler:
    @staticmethod
    async def handle_timeout(operation: str, retry_count: int = 3):
        # Exponential backoff retry logic
        # Graceful degradation to cached data
        # User notification of delays
```

#### **API Response Errors**
- **422 Validation**: Parse field-specific errors and suggest corrections
- **503 Service Unavailable**: Use cached data, notify about freshness
- **404 Not Found**: Handle deleted opportunities gracefully
- **429 Rate Limited**: Implement request queuing and throttling

#### **Data Quality Issues**
- **Missing Fields**: Provide defaults and flag data quality concerns
- **Inconsistent Data**: Normalize and highlight conflicts
- **Invalid Dates**: Parse various formats, suggest corrections
- **Malformed Numbers**: Handle string/number conversion errors

### Edge Cases and Error Patterns

#### **Search & Filtering Edge Cases**
- **Empty Results**: Return structured response with suggestions
- **Invalid Filter Combinations**: Pre-validate filters
- **Date Range Issues**: Handle future dates, invalid ranges
- **Complex Queries**: Break down into simpler searches

#### **Data Consistency Edge Cases**
- **Deleted Opportunities**: Handle 404s gracefully during multi-step operations
- **Changed Data**: Detect stale cached data
- **Race Conditions**: Handle concurrent access properly

### Robust Error Response Format
```python
{
    "error": {
        "type": "validation_error",
        "message": "User-friendly error description",
        "details": {
            "field": "specific_field_name",
            "value": "problematic_value",
            "suggestion": "corrective_action"
        },
        "recovery_options": List[str],
        "partial_results": dict  # Include any successful data
    }
}
```

## Testing Strategy

### Test Categories

#### **Unit Tests**
- **Tool Function Tests**: Each tool with various input combinations
- **Error Handling Tests**: Every error condition and recovery path
- **Data Processing Tests**: Validation, transformation, analysis logic
- **Mock API Tests**: All API interactions with various response scenarios

#### **Integration Tests**
- **API Client Tests**: Real API interaction tests (rate-limited)
- **Workflow Tests**: Complete analysis workflows
- **Performance Tests**: Large dataset handling, memory usage
- **Cache Tests**: Cache hit/miss scenarios, invalidation

#### **Edge Case Tests**
- **Data Quality Tests**: Missing fields, malformed data, empty responses
- **Network Tests**: Timeouts, intermittent failures, rate limiting
- **Boundary Tests**: Maximum result sets, extreme filter combinations
- **Concurrent Access Tests**: Multiple simultaneous requests

### Test Structure Pattern

```python
class TestOpportunityDiscovery:
    """Test opportunity discovery tool functionality."""
    
    @pytest.fixture
    def mock_api_response(self):
        """Mock API response fixture."""
        return {
            "data": [...],
            "pagination_info": {...},
            "status_code": 200
        }
    
    @pytest.mark.asyncio
    async def test_successful_discovery(self, mock_api_response):
        """Test successful opportunity discovery."""
        # Test implementation
        
    @pytest.mark.asyncio  
    async def test_empty_results_handling(self):
        """Test handling of empty search results."""
        # Test implementation
        
    @pytest.mark.asyncio
    async def test_api_timeout_recovery(self):
        """Test recovery from API timeouts."""
        # Test implementation
        
    @pytest.mark.asyncio
    async def test_invalid_filter_validation(self):
        """Test validation of invalid filter parameters."""
        # Test implementation
```

### Mock Data Strategy

#### **API Response Mocks**
- **Complete Response Sets**: Full opportunity, agency, and error response examples
- **Partial Data Scenarios**: Missing fields, incomplete objects
- **Edge Case Responses**: Empty lists, malformed data, error conditions
- **Large Dataset Mocks**: Performance testing scenarios

#### **Fixture Management**
```python
# fixtures/api_responses.py
MOCK_OPPORTUNITIES = {
    "complete": {...},
    "missing_fields": {...},
    "empty_result": {...},
    "error_response": {...}
}

MOCK_AGENCIES = {
    "standard": {...},
    "no_opportunities": {...},
    "incomplete_data": {...}
}
```

### Performance Testing
- **Large Result Set Handling**: Test with 1000+ opportunities
- **Memory Usage**: Monitor memory consumption during analysis
- **API Rate Limiting**: Test throttling and queuing behavior
- **Concurrent Operations**: Multiple simultaneous analyses

### Quality Assurance Checklist

#### **Before Release**
- [ ] All edge cases have explicit tests
- [ ] Error messages are user-friendly and actionable
- [ ] API rate limiting is properly handled
- [ ] Memory usage is reasonable for large datasets
- [ ] All network failures are handled gracefully
- [ ] Data quality issues are flagged appropriately
- [ ] Performance is acceptable for typical use cases
- [ ] Documentation matches implementation

## Production Considerations

### Configuration Management
- **API Keys**: Secure storage and rotation
- **Rate Limits**: Configurable throttling parameters
- **Cache Settings**: TTL configuration, size limits
- **Logging**: Structured logging for debugging and monitoring

### Monitoring and Observability
- **API Health Monitoring**: Track response times, error rates
- **Usage Analytics**: Tool usage patterns, popular searches
- **Performance Metrics**: Memory usage, response times
- **Error Tracking**: Categorized error reporting

### Scalability Considerations
- **Request Queuing**: Handle burst traffic patterns
- **Cache Strategy**: Intelligent caching with appropriate invalidation
- **Memory Management**: Efficient data structures, cleanup procedures
- **Concurrent Access**: Thread-safe operations, resource locking

This specification provides a comprehensive foundation for building a production-ready grants analysis MCP that handles real-world complexities and edge cases while providing valuable intelligence about the government grants ecosystem.

## Cloudflare Deployment

### Overview
The Grants Analysis MCP is designed for deployment on Cloudflare Workers, providing global edge computing, automatic scaling, and built-in security features. This section outlines the deployment architecture, configuration, and best practices for running the MCP on Cloudflare's infrastructure.

### Architecture

#### Deployment Model
- **Runtime**: Cloudflare Workers (V8 isolates)
- **Language**: Python via Pyodide or Python Workers (Beta)
- **Transport**: Server-Sent Events (SSE) for real-time streaming
- **Storage**: Cloudflare KV for persistent caching
- **Secrets**: Cloudflare Secrets for API keys

#### System Components
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Claude Desktop │────▶│ Cloudflare Edge  │────▶│ Simpler Grants  │
│  /AI Playground │ SSE │     (Worker)      │ API │      API        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │ Cloudflare KV │
                        │   (Cache)     │
                        └──────────────┘
```

### Configuration

#### Wrangler Configuration
```toml
# wrangler.toml
name = "grantsmanship-mcp"
main = "src/main.py"
compatibility_date = "2024-01-01"
workers_dev = true

# Python Workers configuration
[build]
command = "pip install -r requirements.txt"

[env.production]
workers_dev = false
routes = [
    { pattern = "grantsmanship-mcp.example.com/*", zone_name = "example.com" }
]
kv_namespaces = [
    { binding = "GRANTS_CACHE", id = "your-kv-namespace-id" }
]

[env.production.vars]
ENVIRONMENT = "production"
ENABLE_AUTH = "false"
SSE_ENDPOINT = "/sse"
CORS_ALLOWED_ORIGINS = "https://claude.ai,https://console.anthropic.com"

[[env.production.secrets]]
name = "API_KEY"

[env.development]
workers_dev = true
kv_namespaces = [
    { binding = "GRANTS_CACHE", id = "dev-kv-namespace-id", preview_id = "preview-id" }
]

[env.development.vars]
ENVIRONMENT = "development"
ENABLE_AUTH = "false"
DEBUG = "true"
```

#### SSE Server Implementation
```python
# src/cloudflare_server.py
from fastmcp import FastMCP
from js import Response, Headers
import json
import asyncio

class CloudflareSSEServer:
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        self.connections = set()
    
    async def handle_sse(self, request, env, ctx):
        """Handle SSE connections for MCP communication."""
        headers = Headers.new({
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": self.get_allowed_origin(request)
        })
        
        # Create readable/writable stream pair
        readable, writable = self.create_stream_pair()
        
        # Handle MCP messages
        asyncio.create_task(self.process_mcp_messages(request, writable, env))
        
        return Response.new(readable, headers=headers)
    
    async def process_mcp_messages(self, request, writer, env):
        """Process incoming MCP messages and send responses."""
        try:
            async for message in self.read_client_messages(request):
                response = await self.mcp.process_message(message)
                await self.send_sse_message(writer, response)
        except Exception as e:
            await self.send_sse_error(writer, str(e))
        finally:
            await writer.close()
    
    def get_allowed_origin(self, request):
        """Validate and return allowed CORS origin."""
        origin = request.headers.get("Origin", "")
        allowed = env.CORS_ALLOWED_ORIGINS.split(",")
        
        if origin in allowed or "localhost" in origin:
            return origin
        return allowed[0]  # Default to first allowed origin
```

### Security Configuration

#### Authentication Options

##### 1. Authless (Public) Mode
```python
# For development and public tools
class AuthlessMiddleware:
    async def process(self, request, handler):
        # No authentication required
        return await handler(request)
```

##### 2. OAuth Authentication
```python
# For production with GitHub OAuth
class OAuthMiddleware:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def process(self, request, handler):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if not token:
            return Response.new("Unauthorized", status=401)
        
        # Verify OAuth token
        user = await self.verify_github_token(token)
        if not user:
            return Response.new("Invalid token", status=403)
        
        request.user = user
        return await handler(request)
    
    async def verify_github_token(self, token):
        # Verify with GitHub API
        response = await fetch(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status == 200:
            return await response.json()
        return None
```

##### 3. API Key Authentication
```python
# Simple API key authentication
class APIKeyMiddleware:
    async def process(self, request, handler):
        api_key = request.headers.get("X-API-Key")
        
        if api_key != env.MCP_API_KEY:
            return Response.new("Invalid API key", status=403)
        
        return await handler(request)
```

### Performance Optimization

#### Cloudflare KV Caching
```python
class CloudflareCache:
    def __init__(self, kv_namespace):
        self.kv = kv_namespace
    
    async def get(self, key: str):
        """Get value from KV store."""
        value = await self.kv.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in KV store with TTL."""
        await self.kv.put(
            key,
            json.dumps(value),
            expirationTtl=ttl
        )
    
    async def delete(self, key: str):
        """Delete value from KV store."""
        await self.kv.delete(key)
```

#### Edge Caching Strategy
```python
class EdgeCacheManager:
    def __init__(self, cache: CloudflareCache):
        self.cache = cache
        self.memory_cache = {}  # In-memory cache for current request
    
    async def get_with_cache(self, key: str, fetch_func, ttl: int = 3600):
        """Get data with multi-level caching."""
        
        # Check memory cache first
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # Check KV cache
        cached = await self.cache.get(key)
        if cached:
            self.memory_cache[key] = cached
            return cached
        
        # Fetch fresh data
        data = await fetch_func()
        
        # Store in both caches
        self.memory_cache[key] = data
        await self.cache.set(key, data, ttl)
        
        return data
```

### Rate Limiting

```python
class CloudflareRateLimiter:
    def __init__(self, kv_namespace):
        self.kv = kv_namespace
    
    async def check_rate_limit(self, client_id: str, limit: int = 100, window: int = 60):
        """Check if client has exceeded rate limit."""
        key = f"rate_limit:{client_id}"
        
        # Get current count
        count_str = await self.kv.get(key)
        count = int(count_str) if count_str else 0
        
        if count >= limit:
            return False
        
        # Increment counter with expiration
        await self.kv.put(key, str(count + 1), expirationTtl=window)
        return True
```

### Deployment Process

#### 1. Local Development
```bash
# Install dependencies
pip install -r requirements.txt
npm install -g wrangler

# Run local development server
wrangler dev

# Test SSE endpoint
curl -N http://localhost:8787/sse

# Test with MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8787/sse
```

#### 2. Staging Deployment
```bash
# Deploy to staging environment
wrangler publish --env development

# Test staging deployment
curl -N https://grantsmanship-mcp.dev.workers.dev/sse

# View logs
wrangler tail --env development
```

#### 3. Production Deployment
```bash
# Set production secrets
wrangler secret put API_KEY --env production

# Deploy to production
wrangler publish --env production

# Monitor production
wrangler tail --env production
```

### Connection Configuration

#### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "grantsmanship": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/mcp-client-proxy",
        "connect",
        "https://grantsmanship-mcp.example.com/sse"
      ]
    }
  }
}
```

#### Direct SSE Connection
```javascript
// JavaScript client example
const eventSource = new EventSource('https://grantsmanship-mcp.example.com/sse');

eventSource.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('MCP Message:', message);
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
};
```

### Monitoring and Observability

#### Cloudflare Analytics Integration
```python
class CloudflareAnalytics:
    async def log_request(self, request, response, duration):
        """Log request to Cloudflare Analytics."""
        await self.kv.put(
            f"analytics:{datetime.now().isoformat()}",
            json.dumps({
                "path": request.url,
                "method": request.method,
                "status": response.status,
                "duration_ms": duration,
                "user_agent": request.headers.get("User-Agent"),
                "timestamp": datetime.now().isoformat()
            }),
            expirationTtl=86400  # 24 hours
        )
```

#### Error Tracking
```python
class CloudflareErrorTracker:
    async def log_error(self, error: Exception, context: Dict):
        """Log errors to Cloudflare KV for analysis."""
        error_data = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "stack_trace": traceback.format_exc()
        }
        
        await self.kv.put(
            f"errors:{datetime.now().isoformat()}",
            json.dumps(error_data),
            expirationTtl=604800  # 7 days
        )
```

### Environment Variables

Required environment variables for Cloudflare deployment:

```bash
# API Configuration
API_KEY=your_simpler_grants_api_key

# Cloudflare Configuration
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token

# MCP Configuration
MCP_API_KEY=optional_mcp_api_key
ENABLE_AUTH=false|true
SSE_ENDPOINT=/sse

# CORS Settings
CORS_ALLOWED_ORIGINS=https://claude.ai,https://console.anthropic.com

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Cache Settings
CACHE_TTL=3600
MAX_CACHE_SIZE_MB=100
```

### Performance Considerations

#### Worker Limits
- **CPU Time**: 50ms per request (Bundled plan), 30s (Unbound plan)
- **Memory**: 128MB per worker
- **Subrequests**: 50 per request (Bundled), 1000 (Unbound)
- **KV Operations**: 1000 reads/day (Free), unlimited (Paid)

#### Optimization Strategies
1. **Use KV for persistent caching** to reduce API calls
2. **Implement request coalescing** for duplicate concurrent requests
3. **Stream responses** using SSE for better perceived performance
4. **Batch API requests** when possible
5. **Use Cloudflare's edge cache** for static resources

### Cost Estimation

#### Cloudflare Workers Pricing
- **Bundled Plan**: $5/month
  - 10M requests included
  - $0.50 per additional million requests

- **Unbound Plan**: Pay-as-you-go
  - $0.50 per million requests
  - $0.02 per million KV reads
  - $0.60 per million KV writes

#### Example Monthly Costs (1M requests)
- Workers requests: $0.50
- KV reads (2M): $0.04
- KV writes (200K): $0.12
- **Total**: ~$0.66/month

### Troubleshooting

#### Common Issues

1. **SSE Connection Drops**
   - Implement reconnection logic in client
   - Add keep-alive messages every 30 seconds
   - Check Cloudflare timeout settings

2. **CORS Errors**
   - Verify allowed origins configuration
   - Check preflight request handling
   - Ensure headers are properly set

3. **Rate Limiting**
   - Monitor KV usage for rate limit tracking
   - Implement exponential backoff
   - Consider per-user vs per-IP limiting

4. **Cache Invalidation**
   - Use versioned cache keys
   - Implement TTL-based expiration
   - Add manual cache purge endpoint

### Security Best Practices

1. **Never expose API keys in client-side code**
2. **Use Cloudflare Secrets for sensitive data**
3. **Implement proper CORS policies**
4. **Enable rate limiting for all endpoints**
5. **Log security events for monitoring**
6. **Use OAuth for production deployments**
7. **Regularly rotate API keys**
8. **Implement request validation**

This Cloudflare deployment configuration ensures the Grants Analysis MCP is production-ready, scalable, and secure while maintaining excellent performance at the edge.