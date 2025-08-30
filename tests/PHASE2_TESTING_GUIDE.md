# Phase 2 Testing Guide - Grants MCP Server

## Setup Instructions

### 1. Configure API Key

Replace `your_api_key_here` in the Claude Desktop config with your actual Simpler Grants API key:

**File:** `/Users/tarive/Library/Application Support/Claude/claude_desktop_config.json`

```json
"grantsmanship": {
  "command": "python3",
  "args": ["/Users/tarive/Desktop/grants-data-analysis/grants-mcp/main.py"],
  "env": {
    "SIMPLER_GRANTS_API_KEY": "your_actual_api_key_here"
  }
}
```

### 2. Restart Claude Desktop

After updating the configuration:
1. Quit Claude Desktop completely (Cmd+Q)
2. Start Claude Desktop again
3. The MCP tools should appear in the tools list

## Available Tools After Phase 2

### 1. **opportunity_discovery** (Original - Enhanced)
Search and discover grant opportunities with advanced filtering.

**Test Commands:**
```
Search for artificial intelligence grants

Find renewable energy grants with award ceiling above $1 million

Search for NSF grants in technology category
```

### 2. **agency_landscape** (New in Phase 2)
Map agencies and their funding focus areas with comprehensive analysis.

**Test Commands:**
```
Analyze the agency landscape for top 5 agencies

Show agency landscape focusing on NSF and NIH

Map agency landscape for climate-related funding
```

### 3. **funding_trend_scanner** (New in Phase 2)
Scan funding trends to identify patterns and emerging opportunities.

**Test Commands:**
```
Scan funding trends for the last 90 days

Analyze funding trends in artificial intelligence category

Show emerging topics and high-value opportunities in recent grants
```

## Testing Scenarios

### Scenario 1: Basic Discovery
```
User: "Search for quantum computing grants"
Expected: Tool uses opportunity_discovery to find relevant grants
```

### Scenario 2: Agency Analysis
```
User: "Show me which agencies fund AI research"
Expected: Tool uses agency_landscape to analyze agency portfolios
```

### Scenario 3: Trend Analysis
```
User: "What are the emerging funding trends in the last month?"
Expected: Tool uses funding_trend_scanner to identify patterns
```

### Scenario 4: Combined Analysis
```
User: "I want to understand the renewable energy grants landscape"
Expected: Multiple tools work together:
1. opportunity_discovery finds current grants
2. agency_landscape maps key agencies
3. funding_trend_scanner identifies trends
```

## Verification Checklist

- [ ] Claude Desktop restarted after config update
- [ ] "grantsmanship" appears in available MCP tools
- [ ] API key is correctly set (no 401 errors)
- [ ] opportunity_discovery tool responds to queries
- [ ] agency_landscape tool analyzes agencies
- [ ] funding_trend_scanner identifies trends
- [ ] Cache is working (second identical query is faster)

## Cache Behavior

The optimized cache system uses different strategies:

- **opportunity_discovery**: 5-minute cache (frequently changing)
- **agency_landscape**: 1-hour cache (relatively stable)
- **funding_trend_scanner**: 30-minute temporal buckets

To test cache:
1. Run the same query twice
2. Second query should return instantly with "(from cache)" indicator

## Troubleshooting

### Tools Not Appearing
1. Check Claude Desktop logs: `~/Library/Logs/Claude/`
2. Verify Python path: `which python3`
3. Test server directly: `python3 /Users/tarive/Desktop/grants-data-analysis/grants-mcp/test_mcp_stdio.py`

### API Errors (401)
1. Verify API key is set correctly in config
2. Test API key: `export SIMPLER_GRANTS_API_KEY=your_key && python3 test_discovery_tools_api.py`

### Import Errors
1. Ensure you're in the project directory
2. Check Python version: `python3 --version` (should be 3.11+)
3. Verify imports: `python3 -c "from src.mcp_server.server import GrantsAnalysisServer"`

## Success Indicators

✅ All three tools respond to queries
✅ No errors in Claude Desktop logs
✅ Cache hit rate increases with repeated queries
✅ Results include detailed analysis and recommendations
✅ Cross-agency patterns are identified
✅ Emerging trends are detected

## Example Full Test Session

```
You: "Help me find funding opportunities for climate change research"

Claude: [Uses opportunity_discovery to search]
"I found 15 climate change research grants. Let me analyze the landscape..."

[Uses agency_landscape to map agencies]
"The main agencies funding climate research are EPA, NSF, and DOE..."

[Uses funding_trend_scanner for trends]
"I've identified increasing funding velocity in renewable energy with 45% growth..."

You: "Show me the top high-value opportunities"

Claude: [Returns cached trend data instantly]
"Based on the analysis, here are the top 3 high-value opportunities..."
```

## Phase 2 Features Summary

| Feature | Tool | New/Enhanced |
|---------|------|--------------|
| Grant Search | opportunity_discovery | Enhanced |
| Agency Portfolio Analysis | agency_landscape | New |
| Cross-Agency Patterns | agency_landscape | New |
| Temporal Trends | funding_trend_scanner | New |
| Emerging Topics | funding_trend_scanner | New |
| High-Value Opportunity Detection | funding_trend_scanner | New |
| Optimized Caching | All tools | New |

## Next Steps

After successful testing:
1. Document any issues found
2. Note performance improvements from caching
3. Identify most useful new features
4. Prepare for Phase 3 (Advanced Analytics) if desired