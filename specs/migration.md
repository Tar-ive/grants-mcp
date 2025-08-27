# Migration Guide: TypeScript to Python MCP with FastMCP

## Overview
This document outlines the migration strategy from the current TypeScript-based grants MCP to an enhanced Python-based implementation using FastMCP, with deployment on Cloudflare Workers.

## Current Implementation Analysis

### Existing TypeScript Implementation
- **Framework**: @modelcontextprotocol/sdk (TypeScript)
- **Transport**: StdioServerTransport
- **Tools**: 1 tool (search-grants)
- **Resources**: None
- **Prompts**: None
- **API**: Simpler Grants API v1
- **Features**: Basic grant search with pagination

### Limitations of Current System
1. Single tool with limited functionality
2. No caching mechanism
3. No session management
4. No competitive analysis features
5. No resource tracking
6. No intelligent prompts
7. Limited error handling
8. No deployment infrastructure

## Target Architecture: Python with FastMCP

### Technology Stack
- **Framework**: FastMCP (Python)
- **Language**: Python 3.11+
- **Deployment**: Cloudflare Workers
- **Transport**: SSE (Server-Sent Events) for remote access
- **API Client**: httpx (async)
- **Data Models**: Pydantic v2
- **Caching**: In-memory with TTL
- **Testing**: pytest with async support

### Enhanced Feature Set
- **Tools**: 9 comprehensive tools
- **Resources**: 3 dynamic resources
- **Prompts**: 9+ intelligent workflows
- **Analytics**: Competitive intelligence and pattern analysis
- **Performance**: Smart caching and session management
- **Deployment**: Cloud-native with Cloudflare Workers

## Migration Mapping

### 1. Core Server Migration

#### TypeScript (Current)
```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({
  name: "grantmanship",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {}
  }
});
```

#### Python with FastMCP (Target)
```python
from fastmcp import FastMCP
from fastmcp.server import Context
from typing import Optional, Dict, List, Any
import httpx
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio

# Initialize FastMCP server
mcp = FastMCP(
    name="grantsmanship-mcp",
    version="2.0.0",
    description="Comprehensive grants intelligence platform"
)

# Configure for multiple transports
class GrantsServer:
    def __init__(self):
        self.api_client = httpx.AsyncClient()
        self.cache = {}
        self.session_store = {}
```

### 2. Tool Implementation Migration

#### TypeScript Tool (Current)
```typescript
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "search-grants") {
    // Single tool implementation
  }
});
```

#### Python Tools with FastMCP (Target)
```python
# Tool 1: Enhanced Search (migrated from TypeScript)
@mcp.tool
async def search_grants(
    query: str = Field(..., description="Search query for grants"),
    page: int = Field(1, description="Page number for pagination"),
    grants_per_page: int = Field(10, description="Number of grants per page"),
    filters: Optional[Dict[str, Any]] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Search for government grants with advanced filtering."""
    await ctx.info(f"Searching grants with query: {query}")
    
    # Enhanced implementation with caching
    cache_key = f"search_{query}_{page}_{grants_per_page}"
    if cache_key in server.cache:
        await ctx.info("Returning cached results")
        return server.cache[cache_key]
    
    # API call with error handling
    try:
        response = await server.api_client.post(
            "https://api.simpler.grants.gov/v1/opportunities/search",
            json={
                "query": query,
                "filters": filters or {"opportunity_status": {"one_of": ["forecasted", "posted"]}},
                "pagination": {
                    "page_offset": page,
                    "page_size": grants_per_page,
                    "order_by": "opportunity_id",
                    "sort_direction": "descending"
                }
            },
            headers={"X-Auth": os.getenv("API_KEY")}
        )
        
        # Process and cache results
        results = process_search_results(response.json())
        server.cache[cache_key] = results
        return results
        
    except Exception as e:
        await ctx.error(f"Search failed: {str(e)}")
        raise

# Tool 2: Opportunity Discovery (new)
@mcp.tool
async def discover_opportunities(
    domain: str = Field(..., description="Domain or field of interest"),
    filters: Optional[Dict[str, Any]] = None,
    max_results: int = Field(100, description="Maximum opportunities to retrieve"),
    ctx: Context = None
) -> Dict[str, Any]:
    """Discover funding opportunities with intelligent analysis."""
    await ctx.info(f"Discovering opportunities in domain: {domain}")
    
    # Implementation with summary statistics
    opportunities = await search_with_pagination(domain, filters, max_results, ctx)
    
    return {
        "opportunities": opportunities,
        "total_found": len(opportunities),
        "summary_stats": calculate_summary_stats(opportunities),
        "metadata": {
            "search_time": datetime.now().isoformat(),
            "api_status": "success",
            "cache_used": False
        }
    }

# Tool 3: Agency Landscape Analysis (new)
@mcp.tool
async def analyze_agency_landscape(
    agencies: Optional[List[str]] = None,
    include_opportunities: bool = True,
    focus_area: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Map agencies and their funding focus areas."""
    await ctx.info("Analyzing agency landscape")
    
    # Complex agency analysis
    agency_data = await fetch_agency_data(agencies, ctx)
    
    return {
        "agencies": agency_data,
        "agency_profiles": analyze_agency_profiles(agency_data),
        "cross_agency_analysis": find_cross_agency_patterns(agency_data),
        "funding_landscape": calculate_funding_distribution(agency_data)
    }

# Tool 4: Opportunity Density Calculator (new)
@mcp.tool
async def calculate_opportunity_density(
    opportunity_ids: List[str],
    min_density_threshold: Optional[int] = None,
    include_accessibility: bool = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """Calculate funding density and competition metrics."""
    await ctx.info(f"Calculating density for {len(opportunity_ids)} opportunities")
    
    densities = {}
    for opp_id in opportunity_ids:
        opportunity = await fetch_opportunity(opp_id, ctx)
        density = calculate_density(opportunity)
        accessibility = score_accessibility(opportunity) if include_accessibility else None
        
        densities[opp_id] = {
            "funding_density_score": density,
            "accessibility_score": accessibility,
            "resource_requirements": assess_requirements(opportunity),
            "barrier_analysis": analyze_barriers(opportunity)
        }
    
    return {
        "density_analysis": densities,
        "rankings": rank_opportunities(densities),
        "insights": generate_density_insights(densities)
    }

# Tool 5: Budget Distribution Analyzer (new)
@mcp.tool
async def analyze_budget_distribution(
    category: Optional[str] = None,
    size_focus: Optional[str] = None,
    agency_comparison: bool = False,
    ctx: Context = None
) -> Dict[str, Any]:
    """Analyze funding availability across award size tiers."""
    await ctx.info("Analyzing budget distribution")
    
    # Define funding tiers
    tiers = {
        "micro": (0, 50000),
        "small": (50000, 250000),
        "medium": (250000, 1000000),
        "large": (1000000, 5000000),
        "major": (5000000, float('inf'))
    }
    
    distribution = await analyze_distribution_by_tiers(tiers, category, ctx)
    
    return {
        "distribution_analysis": distribution,
        "strategic_insights": {
            "underserved_tiers": find_underserved_tiers(distribution),
            "oversaturated_tiers": find_oversaturated_tiers(distribution),
            "optimal_sizing": calculate_optimal_sizing(distribution)
        }
    }

# Tool 6: Deadline Clustering (new)
@mcp.tool
async def cluster_deadlines(
    cluster_method: str = Field("monthly", description="Clustering approach"),
    agency_focus: Optional[List[str]] = None,
    identify_gaps: bool = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """Analyze deadline patterns for strategic timing."""
    await ctx.info(f"Clustering deadlines using {cluster_method} method")
    
    opportunities = await fetch_upcoming_opportunities(agency_focus, ctx)
    
    clusters = {
        "monthly": cluster_by_month(opportunities),
        "quarterly": cluster_by_quarter(opportunities),
        "agency": cluster_by_agency(opportunities),
        "category": cluster_by_category(opportunities)
    }.get(cluster_method, cluster_by_month(opportunities))
    
    timing_strategy = {
        "low_competition_windows": find_low_competition_windows(clusters) if identify_gaps else [],
        "high_competition_periods": find_high_competition_periods(clusters),
        "optimal_sequences": calculate_optimal_sequences(clusters)
    }
    
    return {
        "deadline_clusters": clusters,
        "timing_strategy": timing_strategy
    }

# Tool 7: Eligibility Decoder (new)
@mcp.tool
async def decode_eligibility(
    opportunities: List[str],
    complexity_scoring: bool = True,
    institution_type: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Parse and categorize complex eligibility requirements."""
    await ctx.info(f"Decoding eligibility for {len(opportunities)} opportunities")
    
    eligibility_analysis = {}
    
    for opp_id in opportunities:
        opportunity = await fetch_opportunity(opp_id, ctx)
        
        eligibility_analysis[opp_id] = {
            "complexity_score": score_eligibility_complexity(opportunity) if complexity_scoring else None,
            "requirements": parse_requirements(opportunity),
            "barriers": identify_barriers(opportunity),
            "qualifications_needed": extract_qualifications(opportunity)
        }
    
    return {
        "eligibility_analysis": eligibility_analysis,
        "summary": {
            "most_accessible": find_most_accessible(eligibility_analysis),
            "highest_barriers": find_highest_barriers(eligibility_analysis),
            "common_requirements": find_common_requirements(eligibility_analysis)
        }
    }

# Tool 8: Agency Pattern Analyzer (new)
@mcp.tool
async def analyze_agency_patterns(
    agencies: List[str],
    compare_agencies: bool = False,
    focus_area: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """Analyze agency-specific funding behaviors and preferences."""
    await ctx.info(f"Analyzing patterns for {len(agencies)} agencies")
    
    profiles = {}
    
    for agency in agencies:
        opportunities = await fetch_agency_opportunities(agency, ctx)
        
        profiles[agency] = {
            "funding_personality": analyze_funding_personality(opportunities),
            "preferences": {
                "typical_award_range": calculate_typical_range(opportunities),
                "preferred_categories": identify_preferred_categories(opportunities),
                "institution_favorability": analyze_institution_preferences(opportunities),
                "geographic_patterns": analyze_geographic_patterns(opportunities)
            },
            "strategic_insights": generate_agency_insights(opportunities)
        }
    
    result = {"agency_profiles": profiles}
    
    if compare_agencies:
        result["comparative_analysis"] = compare_agency_profiles(profiles)
        result["recommendations"] = generate_recommendations(profiles)
    
    return result

# Tool 9: Opportunity Pattern Identifier (new)
@mcp.tool
async def identify_opportunity_patterns(
    category: Optional[str] = None,
    focus: str = Field("all", description="Analysis focus area"),
    include_agency_patterns: bool = True,
    ctx: Context = None
) -> Dict[str, Any]:
    """Identify patterns in opportunity characteristics."""
    await ctx.info(f"Identifying patterns with focus: {focus}")
    
    opportunities = await fetch_opportunities_by_category(category, ctx)
    
    pattern_analysis = {
        "structural_patterns": analyze_structural_patterns(opportunities),
        "category_patterns": analyze_category_patterns(opportunities),
        "collaboration_patterns": find_collaboration_patterns(opportunities),
        "innovation_indicators": identify_innovation_indicators(opportunities)
    }
    
    if include_agency_patterns:
        pattern_analysis["agency_patterns"] = analyze_agency_specific_patterns(opportunities)
    
    return {
        "pattern_analysis": pattern_analysis,
        "insights": generate_pattern_insights(pattern_analysis),
        "recommendations": generate_pattern_recommendations(pattern_analysis)
    }
```

### 3. Resource Implementation

#### Python Resources with FastMCP
```python
# Resource 1: API Status
@mcp.resource("grants://api/status")
async def get_api_status() -> Dict[str, Any]:
    """Real-time API health and authentication status."""
    return {
        "api_health": {
            "status": await check_api_health(),
            "response_time_ms": server.last_response_time,
            "last_successful_call": server.last_success_timestamp,
            "known_issues": await detect_known_issues()
        },
        "authentication": {
            "token_status": "valid" if os.getenv("API_KEY") else "missing",
            "rate_limit": await get_rate_limit_status()
        },
        "endpoint_status": await check_endpoint_availability()
    }

# Resource 2: Search History
@mcp.resource("grants://search/history/{session_id}")
async def get_search_history(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve search history and parameters."""
    if session_id and session_id in server.session_store:
        return server.session_store[session_id]
    
    return {
        "recent_searches": server.recent_searches[-10:],
        "search_patterns": analyze_search_patterns(server.recent_searches),
        "suggestions": generate_search_suggestions(server.recent_searches)
    }

# Resource 3: Analysis Cache
@mcp.resource("grants://cache/analysis/{cache_key}")
async def get_cached_analysis(cache_key: str) -> Dict[str, Any]:
    """Retrieve cached analysis results."""
    if cache_key in server.cache:
        return {
            "data": server.cache[cache_key],
            "timestamp": server.cache_timestamps.get(cache_key),
            "ttl_remaining": calculate_ttl_remaining(cache_key)
        }
    
    return {"error": "Cache key not found", "available_keys": list(server.cache.keys())}
```

### 4. Prompt System Implementation

#### Python Prompts with FastMCP
```python
# Prompt 1: Landscape Analysis
@mcp.prompt()
async def grant_landscape_exploration(domain: str, budget_range: tuple) -> str:
    """Guide users through grant landscape discovery."""
    return f"""Let's explore the **{domain}** grants landscape together!

I'll help you discover funding opportunities in your budget range of **${budget_range[0]:,} - ${budget_range[1]:,}**.

**Discovery Strategy:**

1. **Initial Search**: I'll search for opportunities matching your domain
   Command: `search_grants('{domain}', filters={{'award_floor': {budget_range[0]}, 'award_ceiling': {budget_range[1]}}})`

2. **Competition Analysis**: We'll assess the competitive landscape
   Command: `calculate_opportunity_density()` on top results

3. **Agency Mapping**: Identify key funding agencies in your space
   Command: `analyze_agency_landscape()` for relevant agencies

4. **Timing Strategy**: Find optimal application windows
   Command: `cluster_deadlines()` to identify strategic timing

Ready to begin your grant discovery journey?"""

# Prompt 2: Agency Intelligence
@mcp.prompt()
async def agency_deep_dive(agency_code: str) -> str:
    """Comprehensive agency analysis workflow."""
    return f"""Let's conduct a deep analysis of **{agency_code}**'s funding patterns.

**Analysis Framework:**

1. **Funding Personality Profile**
   - Typical award ranges
   - Preferred project types
   - Geographic preferences
   - Institution type favorability

2. **Pattern Recognition**
   - Historical funding trends
   - Category specializations
   - Collaboration preferences
   - Innovation vs. established research balance

3. **Strategic Insights**
   - Best approach strategies
   - Common success factors
   - Red flags to avoid
   - Timing considerations

Shall we start with the funding personality analysis?"""

# Additional prompts for all 9 workflow types...
```

## Data Model Migration

### TypeScript Interface to Pydantic Model

#### TypeScript (Current)
```typescript
interface Grant {
  agency: string;
  opportunity_id: number;
  opportunity_title: string;
  summary: {
    award_ceiling?: number;
    award_floor?: number;
    // ...
  };
}
```

#### Python with Pydantic (Target)
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class GrantSummary(BaseModel):
    award_ceiling: Optional[float] = None
    award_floor: Optional[float] = None
    estimated_total_program_funding: Optional[float] = None
    expected_number_of_awards: Optional[int] = None
    post_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    summary_description: Optional[str] = None
    additional_info_url: Optional[str] = None
    agency_contact_description: Optional[str] = None
    agency_email_address: Optional[str] = None
    agency_phone_number: Optional[str] = None
    applicant_eligibility_description: Optional[str] = None

class Grant(BaseModel):
    agency: str
    agency_code: str
    agency_name: str
    opportunity_id: int
    opportunity_number: str
    opportunity_title: str
    opportunity_status: str
    summary: GrantSummary
    category: str
    top_level_agency_name: Optional[str] = None
    
    # Additional fields for enhanced functionality
    density_score: Optional[float] = None
    accessibility_score: Optional[int] = None
    competition_level: Optional[str] = None
```

## Cloudflare Deployment Architecture

### Deployment Configuration

```python
# cloudflare_config.py
import os
from typing import Dict, Any

class CloudflareConfig:
    """Configuration for Cloudflare Workers deployment."""
    
    # Environment variables (stored as Cloudflare secrets)
    API_KEY = os.getenv("API_KEY")
    CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    
    # SSE configuration
    SSE_ENDPOINT = "/sse"
    SSE_KEEPALIVE_INTERVAL = 30  # seconds
    
    # CORS settings for remote access
    CORS_ORIGINS = [
        "https://claude.ai",
        "https://console.anthropic.com",
        "http://localhost:*"
    ]
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # Cache configuration
    CACHE_TTL = 3600  # 1 hour
    MAX_CACHE_SIZE = 100  # MB

# main.py for Cloudflare deployment
from fastmcp import FastMCP
from fastmcp.server import SSEServer
import asyncio

async def create_app():
    """Create and configure the MCP server for Cloudflare."""
    
    # Initialize FastMCP with SSE transport
    mcp = FastMCP(
        name="grantsmanship-mcp",
        version="2.0.0"
    )
    
    # Configure SSE server for Cloudflare Workers
    server = SSEServer(
        mcp,
        endpoint=CloudflareConfig.SSE_ENDPOINT,
        cors_origins=CloudflareConfig.CORS_ORIGINS
    )
    
    # Add middleware for authentication (optional)
    if os.getenv("ENABLE_AUTH"):
        server.add_middleware(AuthMiddleware())
    
    # Add rate limiting
    server.add_middleware(RateLimitMiddleware(
        requests=CloudflareConfig.RATE_LIMIT_REQUESTS,
        window=CloudflareConfig.RATE_LIMIT_WINDOW
    ))
    
    return server

# Export for Cloudflare Workers
app = asyncio.run(create_app())
```

### Wrangler Configuration

```toml
# wrangler.toml
name = "grantsmanship-mcp"
main = "src/main.py"
compatibility_date = "2024-01-01"

[env.production]
workers_dev = false
route = "grantsmanship-mcp.example.com/*"

[env.production.vars]
ENVIRONMENT = "production"
ENABLE_AUTH = "false"

[[env.production.secrets]]
name = "API_KEY"

[env.development]
workers_dev = true

[env.development.vars]
ENVIRONMENT = "development"
ENABLE_AUTH = "false"
```

## Migration Steps

### Phase 1: Environment Setup (Week 1)
1. **Create Python project structure**
   ```bash
   grantsmanship-mcp/
   ├── src/
   │   ├── __init__.py
   │   ├── main.py
   │   ├── server.py
   │   ├── tools/
   │   ├── resources/
   │   ├── prompts/
   │   └── models/
   ├── tests/
   ├── pyproject.toml
   ├── requirements.txt
   └── wrangler.toml
   ```

2. **Install dependencies**
   ```bash
   pip install fastmcp httpx pydantic python-dotenv
   npm install -g wrangler
   ```

3. **Set up development environment**
   - Configure API keys
   - Set up local testing
   - Configure Cloudflare account

### Phase 2: Core Implementation (Week 2-3)
1. **Implement base server with FastMCP**
2. **Migrate search-grants tool**
3. **Add 8 new tools**
4. **Implement resources**
5. **Create prompt system**
6. **Add caching layer**

### Phase 3: Testing (Week 4)
1. **Unit tests for all tools**
2. **Integration tests with API**
3. **Performance testing**
4. **Cache effectiveness testing**
5. **SSE connection testing**

### Phase 4: Deployment (Week 5)
1. **Deploy to Cloudflare Workers (development)**
2. **Test remote connections**
3. **Performance optimization**
4. **Deploy to production**
5. **Monitor and iterate**

## Testing Strategy

### Local Testing
```python
# test_local.py
import pytest
from fastmcp.testing import MCPTestClient
from main import mcp

@pytest.fixture
def client():
    return MCPTestClient(mcp)

async def test_search_grants(client):
    result = await client.call_tool(
        "search_grants",
        {"query": "climate change", "page": 1}
    )
    assert result["opportunities"] is not None
    assert len(result["opportunities"]) > 0

async def test_opportunity_density(client):
    # First get some opportunities
    search_result = await client.call_tool(
        "search_grants",
        {"query": "research", "grants_per_page": 5}
    )
    
    opportunity_ids = [
        opp["opportunity_id"] 
        for opp in search_result["opportunities"]
    ]
    
    # Test density calculation
    density_result = await client.call_tool(
        "calculate_opportunity_density",
        {"opportunity_ids": opportunity_ids}
    )
    
    assert "density_analysis" in density_result
    assert "rankings" in density_result
```

### Cloudflare Testing
```bash
# Local development server
wrangler dev

# Test with MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8787/sse

# Deploy to staging
wrangler publish --env development

# Production deployment
wrangler publish --env production
```

## Performance Optimization

### Caching Strategy
```python
from functools import lru_cache
from typing import Dict, Any
import hashlib
import json

class CacheManager:
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, Any] = {}
        self.timestamps: Dict[str, float] = {}
        self.ttl = ttl
    
    def get_cache_key(self, tool: str, params: Dict) -> str:
        """Generate cache key from tool and parameters."""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{tool}:{param_str}".encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    async def set(self, key: str, value: Any):
        """Set cache value with timestamp."""
        self.cache[key] = value
        self.timestamps[key] = time.time()
        
        # Implement LRU eviction if cache is too large
        if len(self.cache) > 1000:
            oldest_key = min(self.timestamps, key=self.timestamps.get)
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
```

### Connection Pooling
```python
import httpx
from typing import Optional

class APIClient:
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            )
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def post(self, url: str, **kwargs):
        """Make POST request with retry logic."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = await self.client.post(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    raise
        
        raise Exception("Max retries exceeded")
```

## Monitoring and Observability

### Logging Configuration
```python
import logging
from typing import Dict, Any

class MCPLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Add handlers for different environments
        if os.getenv("ENVIRONMENT") == "production":
            # Send to Cloudflare Analytics
            handler = CloudflareHandler()
        else:
            handler = logging.StreamHandler()
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    async def log_tool_call(self, tool: str, params: Dict, result: Any):
        """Log tool invocations for analytics."""
        self.logger.info(f"Tool called: {tool}", extra={
            "tool": tool,
            "params": params,
            "result_size": len(str(result)),
            "timestamp": datetime.now().isoformat()
        })
    
    async def log_error(self, error: Exception, context: Dict):
        """Log errors with context."""
        self.logger.error(f"Error: {str(error)}", extra={
            "error_type": type(error).__name__,
            "context": context,
            "traceback": traceback.format_exc()
        })
```

## Security Considerations

### API Key Management
```python
import os
from typing import Optional

class SecureConfig:
    """Secure configuration management."""
    
    @staticmethod
    def get_api_key() -> Optional[str]:
        """Get API key from environment or Cloudflare secrets."""
        # In Cloudflare Workers, secrets are available as env vars
        api_key = os.getenv("API_KEY")
        
        if not api_key:
            raise ValueError("API_KEY not configured")
        
        # Validate API key format
        if not api_key.startswith("simpler_") or len(api_key) < 20:
            raise ValueError("Invalid API key format")
        
        return api_key
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input to prevent injection."""
        # Remove HTML tags
        import re
        clean_text = re.sub('<.*?>', '', text)
        
        # Limit length
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000]
        
        return clean_text.strip()
```

### Rate Limiting
```python
from collections import defaultdict
from typing import Dict
import time

class RateLimiter:
    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window
        self.clients: Dict[str, list] = defaultdict(list)
    
    async def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        now = time.time()
        
        # Clean old requests
        self.clients[client_id] = [
            timestamp for timestamp in self.clients[client_id]
            if now - timestamp < self.window
        ]
        
        # Check limit
        if len(self.clients[client_id]) >= self.requests:
            return False
        
        # Add current request
        self.clients[client_id].append(now)
        return True
```

## Rollback Plan

### Version Management
1. Tag current TypeScript version: `v1.0.0`
2. Tag Python migration: `v2.0.0`
3. Maintain both versions during transition
4. Gradual rollout with feature flags

### Rollback Steps
1. **Immediate rollback**: Switch Cloudflare route back to v1
2. **Data preservation**: Export cache and session data
3. **Client notification**: Update connection endpoints
4. **Post-mortem**: Analyze issues and iterate

## Success Metrics

### Performance KPIs
- **Response time**: < 500ms for cached requests
- **Cache hit rate**: > 60% for common queries
- **API efficiency**: Reduce API calls by 40%
- **Uptime**: 99.9% availability

### Feature Adoption
- **Tool usage**: All 9 tools actively used
- **Resource utilization**: Resources accessed regularly
- **Prompt engagement**: Users follow guided workflows
- **Session duration**: Increased engagement time

### User Satisfaction
- **Error rate**: < 1% of requests fail
- **Completion rate**: > 80% of workflows completed
- **Feature requests**: Positive feedback on new capabilities
- **Support tickets**: Reduced issues compared to v1

## Conclusion

This migration from TypeScript to Python with FastMCP represents a significant enhancement of the grants MCP system. The new implementation provides:

1. **9x more functionality** with comprehensive tools
2. **Intelligent caching** for performance
3. **Cloud-native deployment** on Cloudflare
4. **Enhanced error handling** and resilience
5. **Production-ready architecture** with monitoring

The migration preserves backward compatibility while adding substantial new capabilities for grants intelligence and analysis.