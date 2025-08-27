# Resource Workaround for Tool-Only MCP Clients

## Problem Statement

Some MCP clients may not fully support the **Resource** protocol, which limits their ability to access the rich contextual data our grants analysis server provides through 13 dynamic resources. This creates a compatibility gap where tool-only clients cannot access API status, search history, cached analyses, and other critical read-only intelligence data.

## Solution Overview

Implement **Resource Mirror Tools** - a parallel set of tools with `resource_*` prefixes that provide identical functionality to our existing resources. This approach ensures 100% compatibility with tool-only clients while maintaining our existing resource architecture for clients that support it.

## Architecture Strategy

### Dual Access Pattern
```
Resource-Enabled Clients:              Tool-Only Clients:
├── @mcp.resource()                   ├── @mcp.tool() 
├── grants://api/status               ├── resource_api_status()
├── grants://search/history           ├── resource_search_history()
└── grants://cache/analysis/{key}     └── resource_cache_analysis(key)
```

### Benefits
- ✅ **Universal Compatibility** - Works with any MCP client regardless of resource support
- ✅ **Identical Data Access** - Same information available through both patterns  
- ✅ **Zero Breaking Changes** - Existing resource-enabled clients continue working unchanged
- ✅ **Consistent API** - Resource tools use same parameters and return formats
- ✅ **Easy Migration** - Tool-only clients can switch to resources when support is added

## Resource Mapping Strategy

### 1. API & System Resources → Tools

| Resource URI | Tool Function | Parameters | Description |
|--------------|---------------|------------|-------------|
| `grants://api/status` | `resource_api_status()` | None | API health and authentication |
| `grants://api/endpoints` | `resource_api_endpoints()` | None | Available endpoints info |
| `grants://api/usage` | `resource_api_usage()` | None | Usage stats and quotas |

### 2. Search & Discovery Resources → Tools

| Resource URI | Tool Function | Parameters | Description |
|--------------|---------------|------------|-------------|
| `grants://search/history` | `resource_search_history()` | `session_id: str (optional)` | Search history |
| `grants://search/active` | `resource_search_active()` | None | Current search context |
| `grants://search/suggestions` | `resource_search_suggestions()` | None | AI search recommendations |

### 3. Cache & Analysis Resources → Tools

| Resource URI | Tool Function | Parameters | Description |
|--------------|---------------|------------|-------------|
| `grants://cache/opportunities` | `resource_cache_opportunities()` | None | Cached opportunities |
| `grants://cache/agencies` | `resource_cache_agencies()` | None | Cached agency data |
| `grants://cache/analysis/{type}` | `resource_cache_analysis(type)` | `analysis_type: str` | Cached analysis results |

### 4. Intelligence Resources → Tools

| Resource URI | Tool Function | Parameters | Description |
|--------------|---------------|------------|-------------|
| `grants://intelligence/agency_patterns` | `resource_intelligence_agency_patterns()` | None | Agency behavior patterns |
| `grants://intelligence/competition_metrics` | `resource_intelligence_competition_metrics()` | None | Competition landscape |
| `grants://intelligence/timing_strategies` | `resource_intelligence_timing_strategies()` | None | Timing insights |
| `grants://intelligence/eligibility_matrix` | `resource_intelligence_eligibility_matrix()` | None | Eligibility patterns |

## Implementation Plan

### Phase 1: Tool Implementation

#### 1.1 API Status Tools
```python
# Add to server.py

@mcp.tool()
async def resource_api_status() -> dict:
    """Tool mirror of grants://api/status resource."""
    from .resources.api_status_resource import get_api_status
    return await get_api_status()

@mcp.tool()
async def resource_api_endpoints() -> dict:
    """Tool mirror of grants://api/endpoints resource."""
    from .resources.api_status_resource import get_api_endpoints
    return await get_api_endpoints()

@mcp.tool()
async def resource_api_usage() -> dict:
    """Tool mirror of grants://api/usage resource."""
    from .resources.api_status_resource import get_api_usage
    return await get_api_usage()
```

#### 1.2 Search Context Tools
```python
@mcp.tool()
async def resource_search_history(session_id: str = None) -> dict:
    """Tool mirror of grants://search/history resource."""
    from .resources.search_history_resource import get_search_history
    return await get_search_history(session_id)

@mcp.tool()
async def resource_search_active() -> dict:
    """Tool mirror of grants://search/active resource."""
    from .resources.search_history_resource import get_active_search
    return await get_active_search()

@mcp.tool()
async def resource_search_suggestions() -> dict:
    """Tool mirror of grants://search/suggestions resource."""
    from .resources.search_history_resource import get_search_suggestions
    return await get_search_suggestions()
```

#### 1.3 Cache Access Tools
```python
@mcp.tool()
async def resource_cache_opportunities() -> dict:
    """Tool mirror of grants://cache/opportunities resource."""
    from .resources.analysis_cache_resource import get_cached_opportunities
    return await get_cached_opportunities()

@mcp.tool()
async def resource_cache_agencies() -> dict:
    """Tool mirror of grants://cache/agencies resource."""
    from .resources.analysis_cache_resource import get_cached_agencies
    return await get_cached_agencies()

@mcp.tool()
async def resource_cache_analysis(analysis_type: str) -> dict:
    """Tool mirror of grants://cache/analysis/{type} resource."""
    from .resources.analysis_cache_resource import get_cached_analysis
    return await get_cached_analysis(analysis_type)
```

#### 1.4 Intelligence Tools
```python
@mcp.tool()
async def resource_intelligence_agency_patterns() -> dict:
    """Tool mirror of grants://intelligence/agency_patterns resource."""
    from .resources.intelligence_resource import get_agency_patterns
    return await get_agency_patterns()

@mcp.tool()
async def resource_intelligence_competition_metrics() -> dict:
    """Tool mirror of grants://intelligence/competition_metrics resource."""
    from .resources.intelligence_resource import get_competition_metrics
    return await get_competition_metrics()

@mcp.tool()
async def resource_intelligence_timing_strategies() -> dict:
    """Tool mirror of grants://intelligence/timing_strategies resource."""
    from .resources.intelligence_resource import get_timing_strategies
    return await get_timing_strategies()

@mcp.tool()
async def resource_intelligence_eligibility_matrix() -> dict:
    """Tool mirror of grants://intelligence/eligibility_matrix resource."""
    from .resources.intelligence_resource import get_eligibility_matrix
    return await get_eligibility_matrix()
```

### Phase 2: Testing Strategy

#### 2.1 Resource Tool Tests
```python
# Add to tests/test_resource_tools.py

import pytest
from src.mcp_server.server import (
    resource_api_status,
    resource_search_history,
    resource_intelligence_competition_metrics
)

class TestResourceMirrorTools:
    """Test resource mirror tools provide identical functionality."""
    
    async def test_resource_api_status_matches_resource(self):
        """Ensure tool matches resource output."""
        tool_result = await resource_api_status()
        # Compare with actual resource call
        assert "api_health" in tool_result
        assert "authentication" in tool_result
        assert "endpoint_status" in tool_result
    
    async def test_resource_search_history_with_session(self):
        """Test session-specific search history."""
        session_id = "test_session_123"
        result = await resource_search_history(session_id)
        assert "search_history" in result
        assert "session_id" in result
    
    async def test_resource_cache_analysis_parameter_validation(self):
        """Test parameter validation for cache analysis."""
        valid_types = ["density", "competition", "timing", "eligibility"]
        for analysis_type in valid_types:
            result = await resource_cache_analysis(analysis_type)
            assert "analysis_type" in result or "error" in result
    
    async def test_all_resource_tools_available(self):
        """Verify all 13 resource tools are implemented."""
        expected_tools = [
            # API & System (3)
            "resource_api_status",
            "resource_api_endpoints", 
            "resource_api_usage",
            
            # Search & Discovery (3)
            "resource_search_history",
            "resource_search_active",
            "resource_search_suggestions",
            
            # Cache & Analysis (3)
            "resource_cache_opportunities",
            "resource_cache_agencies",
            "resource_cache_analysis",
            
            # Intelligence (4)
            "resource_intelligence_agency_patterns",
            "resource_intelligence_competition_metrics",
            "resource_intelligence_timing_strategies",
            "resource_intelligence_eligibility_matrix"
        ]
        
        # Verify all tools exist and are callable
        import sys
        for tool_name in expected_tools:
            assert hasattr(sys.modules[__name__], tool_name)
```

#### 2.2 Integration Tests
```python
# Add to tests/test_integration.py

async def test_resource_tool_data_consistency(self):
    """Verify resource and tool return identical data."""
    
    # Perform a search to populate cache and history
    await discover_opportunities("education", {"category": "Education"})
    
    # Compare resource vs tool outputs
    api_status = await resource_api_status()
    search_history = await resource_search_history()
    competition = await resource_intelligence_competition_metrics()
    
    # Verify data structure consistency
    assert "api_health" in api_status
    assert api_status["api_health"]["status"] in ["healthy", "degraded", "down"]
    
    assert "searches" in search_history or "search_history" in search_history
    
    if competition.get("analysis_timestamp"):
        assert "funding_density_distribution" in competition
        assert "competition_levels" in competition

async def test_resource_tools_handle_empty_cache(self):
    """Test resource tools handle empty cache gracefully."""
    
    # Clear all caches
    cached_opportunities.clear()
    cached_agencies.clear()
    analysis_results.clear()
    
    # Test each resource tool with empty cache
    opportunities = await resource_cache_opportunities()
    assert opportunities == {"opportunities": [], "cache_empty": True}
    
    agencies = await resource_cache_agencies()
    assert agencies == {"agencies": [], "cache_empty": True}
    
    competition = await resource_intelligence_competition_metrics()
    assert "message" in competition  # Should indicate no analysis available
```

### Phase 3: Documentation Updates

#### 3.1 README.md Enhancement
```markdown
## 🔄 Tool-Only Client Support

For MCP clients that don't support resources, all resource functionality is available through mirror tools:

### Resource Mirror Tools (13 total)

#### API & System Status
- `resource_api_status()` - API health and authentication status
- `resource_api_endpoints()` - Available API endpoints
- `resource_api_usage()` - Usage statistics and rate limits

#### Search & Discovery Context
- `resource_search_history(session_id?)` - Search history by session
- `resource_search_active()` - Current active search context
- `resource_search_suggestions()` - AI-powered search suggestions

#### Cache Access
- `resource_cache_opportunities()` - Cached opportunity data
- `resource_cache_agencies()` - Cached agency profiles
- `resource_cache_analysis(type)` - Cached analysis results

#### Intelligence Data
- `resource_intelligence_agency_patterns()` - Agency behavior patterns
- `resource_intelligence_competition_metrics()` - Competition landscape
- `resource_intelligence_timing_strategies()` - Strategic timing insights
- `resource_intelligence_eligibility_matrix()` - Eligibility requirement patterns

### Usage Example
```python
# Instead of accessing resource: grants://api/status
api_status = await resource_api_status()

# Instead of accessing resource: grants://search/history/session123
search_history = await resource_search_history("session123")

# Instead of accessing resource: grants://intelligence/competition_metrics
competition_data = await resource_intelligence_competition_metrics()
```

#### 3.2 Migration Guide
```markdown
## Migration Guide: Resources → Tools

| Resource Pattern | Tool Pattern | Parameters |
|-----------------|--------------|------------|
| `grants://api/status` | `resource_api_status()` | None |
| `grants://search/history/{id}` | `resource_search_history(id)` | session_id (optional) |
| `grants://cache/analysis/{type}` | `resource_cache_analysis(type)` | analysis_type |
| `grants://intelligence/agency_patterns` | `resource_intelligence_agency_patterns()` | None |

### When to Use Resource Tools

Use resource mirror tools when:
- Your MCP client doesn't support the Resource protocol
- You need read-only access to system state
- You want to check cache status or API health
- You need intelligence data from previous analyses

### Data Consistency

Resource tools return identical data structures to their resource counterparts:
- Same JSON schema
- Same error handling
- Same cache behavior
- Same refresh logic
```

## Implementation Benefits

### For Tool-Only Clients
- ✅ **Full Intelligence Access** - All 13 resources available as tools
- ✅ **Identical Information** - Same data structures and content
- ✅ **Standard Tool Interface** - Uses familiar tool calling patterns
- ✅ **Parameter Support** - Handles optional parameters (e.g., session_id)

### For Development Teams  
- ✅ **Zero Maintenance Overhead** - Tools wrap existing resource functions
- ✅ **Consistent Testing** - Same underlying code paths
- ✅ **Flexible Deployment** - Can enable/disable based on client needs
- ✅ **Future-Proof** - Easy to deprecate when client support improves

### For MCP Ecosystem
- ✅ **Backward Compatibility** - Supports older/limited MCP clients
- ✅ **Migration Path** - Smooth transition when clients add resource support  
- ✅ **Standard Pattern** - Reusable approach for other MCP servers
- ✅ **Client Choice** - Developers can choose resource vs tool patterns

## Error Handling

### Resource Tool Error Patterns
```python
# Consistent error handling across resource tools

@mcp.tool()
async def resource_cache_analysis(analysis_type: str) -> dict:
    """Handle various error conditions gracefully."""
    
    # Validate analysis type
    valid_types = ["density", "competition", "timing", "eligibility", "agency"]
    if analysis_type not in valid_types:
        return {
            "error": "invalid_analysis_type",
            "message": f"Analysis type '{analysis_type}' not recognized",
            "valid_types": valid_types,
            "suggestion": f"Try one of: {', '.join(valid_types)}"
        }
    
    # Check cache availability
    if analysis_type not in analysis_results:
        return {
            "error": "no_cached_analysis",
            "message": f"No cached {analysis_type} analysis available",
            "suggestion": f"Run the corresponding analysis tool first",
            "analysis_type": analysis_type,
            "cache_empty": True
        }
    
    # Return cached data with metadata
    cached_data = analysis_results[analysis_type]
    return {
        "analysis_type": analysis_type,
        "data": cached_data["data"],
        "timestamp": cached_data["timestamp"],
        "cache_age_seconds": (datetime.utcnow() - cached_data["timestamp"]).seconds,
        "cache_valid": cached_data.get("valid", True)
    }
```

## Success Metrics

- **Implementation**: 13 resource mirror tools created
- **Testing**: 100% test coverage for resource-tool parity
- **Compatibility**: Works with any tool-capable MCP client
- **Performance**: No overhead - direct function wrapping
- **Maintainability**: Single source of truth (resource functions)

## Deployment Strategy

### Development Phase
1. Implement all 13 resource mirror tools
2. Add comprehensive test suite
3. Update documentation with usage examples

### Testing Phase  
1. Test with resource-enabled clients (should be unchanged)
2. Test with tool-only clients (should have full data access)
3. Verify identical data output between resources and tools
4. Performance testing (should show no degradation)

### Production Rollout
1. Deploy with resource tools available
2. Monitor usage patterns (resources vs tools)
3. Gather feedback from tool-only client users
4. Consider deprecation timeline when universal resource support achieved

## Advanced Features

### Session Management
```python
@mcp.tool()
async def resource_search_session_create() -> dict:
    """Create a new search session for tool-only clients."""
    session_id = str(uuid.uuid4())
    search_sessions[session_id] = {
        "created": datetime.utcnow(),
        "searches": [],
        "active": True
    }
    return {"session_id": session_id, "status": "created"}

@mcp.tool()
async def resource_search_session_list() -> dict:
    """List all active search sessions."""
    active_sessions = [
        {
            "session_id": sid,
            "created": data["created"],
            "search_count": len(data["searches"])
        }
        for sid, data in search_sessions.items()
        if data.get("active", False)
    ]
    return {"sessions": active_sessions, "total": len(active_sessions)}
```

This workaround strategy ensures our grants analysis MCP server provides universal compatibility while maintaining architectural elegance and preparing for future MCP protocol evolution.