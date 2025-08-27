# Grantsmanship MCP Usage Guide

## Overview
This guide provides comprehensive instructions for using the Grantsmanship MCP (Model Context Protocol) server, a powerful grants intelligence platform that helps you discover, analyze, and strategically evaluate U.S. government funding opportunities.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Local Development](#local-development)
5. [Cloudflare Deployment](#cloudflare-deployment)
6. [Connecting to Claude Desktop](#connecting-to-claude-desktop)
7. [Using the Tools](#using-the-tools)
8. [Resources and Prompts](#resources-and-prompts)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)
11. [Examples](#examples)

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ and npm
- Cloudflare account (for deployment)
- Simpler Grants API key

### Fastest Path to Running
```bash
# Clone the repository
git clone https://github.com/yourusername/grantsmanship-mcp.git
cd grantsmanship-mcp

# Install dependencies
pip install -r requirements.txt
npm install -g wrangler

# Set up environment variables
cp .env.example .env
# Edit .env and add your API_KEY

# Run locally
python main.py

# Or deploy to Cloudflare
wrangler dev
```

## Installation

### Step 1: Project Setup
```bash
# Create project directory
mkdir grantsmanship-mcp
cd grantsmanship-mcp

# Initialize Python project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Create project structure
mkdir -p src/mcp_server/{tools,resources,prompts,models,config}
mkdir -p tests/fixtures
```

### Step 2: Install Dependencies
```bash
# Python dependencies
pip install fastmcp httpx pydantic python-dotenv pytest pytest-asyncio

# Node.js dependencies for Cloudflare
npm install -g wrangler
npm install -g @modelcontextprotocol/inspector

# Save dependencies
pip freeze > requirements.txt
```

### Step 3: Environment Configuration
Create a `.env` file:
```bash
# API Keys
API_KEY=your_simpler_grants_api_key_here

# MCP Configuration
MCP_NAME=grantsmanship-mcp
MCP_VERSION=2.0.0

# Development Settings
DEBUG=true
ENVIRONMENT=development

# Cloudflare Settings (for deployment)
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token
```

## Configuration

### API Key Setup

#### Getting a Simpler Grants API Key
1. Visit [Simpler Grants API Portal](https://api.simpler.grants.gov)
2. Register for an account
3. Navigate to API Keys section
4. Generate a new API key
5. Copy the key to your `.env` file

### MCP Server Configuration

Create `src/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    API_KEY = os.getenv("API_KEY")
    API_BASE_URL = "https://api.simpler.grants.gov/v1"
    
    # MCP Configuration
    MCP_NAME = os.getenv("MCP_NAME", "grantsmanship-mcp")
    MCP_VERSION = os.getenv("MCP_VERSION", "2.0.0")
    
    # Cache Settings
    CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))
    MAX_CACHE_SIZE_MB = int(os.getenv("MAX_CACHE_SIZE_MB", 100))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))
    
    # Environment
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
```

## Local Development

### Running the MCP Server Locally

#### Method 1: Direct Python Execution
```bash
# Activate virtual environment
source venv/bin/activate

# Run the server
python main.py

# The server will start on stdio transport by default
```

#### Method 2: Using FastMCP Dev Server
```bash
# Run with auto-reload
fastmcp dev src/main.py

# Run with specific transport
fastmcp dev src/main.py --transport sse --port 8000
```

### Testing with MCP Inspector
```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Test stdio transport
mcp-inspector stdio -- python main.py

# Test HTTP/SSE transport
mcp-inspector http://localhost:8000/sse
```

### Local Testing Commands

#### Test Individual Tools
```python
# test_tools.py
import asyncio
from src.main import mcp

async def test_search():
    result = await mcp.call_tool(
        "search_grants",
        {"query": "climate change", "page": 1}
    )
    print(result)

asyncio.run(test_search())
```

#### Interactive Testing
```python
# Start Python REPL
python

>>> from src.main import mcp
>>> import asyncio
>>> 
>>> # Search for grants
>>> result = asyncio.run(mcp.call_tool("search_grants", {"query": "education"}))
>>> print(result["total_found"])
>>> 
>>> # Analyze agency patterns
>>> agencies = ["NSF", "NIH"]
>>> patterns = asyncio.run(mcp.call_tool("analyze_agency_patterns", {"agencies": agencies}))
>>> print(patterns["agency_profiles"])
```

## Cloudflare Deployment

### Step 1: Prepare for Deployment

#### Create Wrangler Configuration
Create `wrangler.toml`:
```toml
name = "grantsmanship-mcp"
main = "src/main.py"
compatibility_date = "2024-01-01"
workers_dev = true

[build]
command = "pip install -r requirements.txt"

[env.production]
workers_dev = false
routes = [
    { pattern = "grantsmanship-mcp.yourdomain.com/*", zone_name = "yourdomain.com" }
]

[[env.production.secrets]]
name = "API_KEY"

[env.development]
workers_dev = true

[env.development.vars]
DEBUG = "true"
```

### Step 2: Deploy to Cloudflare

#### Development Deployment
```bash
# Login to Cloudflare
wrangler login

# Create KV namespace for caching
wrangler kv:namespace create "GRANTS_CACHE"
wrangler kv:namespace create "GRANTS_CACHE" --preview

# Add KV namespace ID to wrangler.toml
# kv_namespaces = [
#     { binding = "GRANTS_CACHE", id = "your-namespace-id" }
# ]

# Deploy to development
wrangler dev

# Your MCP will be available at:
# http://localhost:8787/sse
```

#### Production Deployment
```bash
# Set secrets
wrangler secret put API_KEY --env production
# Enter your API key when prompted

# Deploy to production
wrangler publish --env production

# Your MCP will be available at:
# https://grantsmanship-mcp.yourdomain.com/sse
```

### Step 3: Monitor Deployment
```bash
# View real-time logs
wrangler tail --env production

# Check deployment status
wrangler deployments list

# View error logs
wrangler tail --env production --format json | grep ERROR
```

## Connecting to Claude Desktop

### Configuration for Claude Desktop

#### Step 1: Install MCP Proxy
```bash
npm install -g @modelcontextprotocol/mcp-client-proxy
```

#### Step 2: Configure Claude Desktop
Add to Claude Desktop configuration:

**For Local Development:**
```json
{
  "mcpServers": {
    "grantsmanship-local": {
      "command": "python",
      "args": [
        "/path/to/grantsmanship-mcp/main.py"
      ]
    }
  }
}
```

**For Cloudflare Deployment:**
```json
{
  "mcpServers": {
    "grantsmanship": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/mcp-client-proxy",
        "connect",
        "https://grantsmanship-mcp.yourdomain.com/sse"
      ]
    }
  }
}
```

#### Step 3: Restart Claude Desktop
After updating the configuration, restart Claude Desktop to load the MCP server.

## Using the Tools

### Tool 1: Search Grants
**Purpose**: Search for government grants with advanced filtering

```python
# Basic search
result = await mcp.call_tool("search_grants", {
    "query": "artificial intelligence",
    "page": 1,
    "grants_per_page": 10
})

# Advanced search with filters
result = await mcp.call_tool("search_grants", {
    "query": "renewable energy",
    "filters": {
        "agency": "DOE",
        "award_ceiling": 1000000,
        "opportunity_status": "posted"
    },
    "page": 1
})
```

**In Claude Desktop:**
```
"Search for AI-related grants from the National Science Foundation"
"Find renewable energy grants with awards over $500,000"
```

### Tool 2: Discover Opportunities
**Purpose**: Comprehensive opportunity discovery with analysis

```python
result = await mcp.call_tool("discover_opportunities", {
    "domain": "climate science",
    "filters": {
        "award_floor": 100000,
        "award_ceiling": 500000
    },
    "max_results": 50
})
```

**In Claude Desktop:**
```
"Discover all climate science funding opportunities between $100K and $500K"
"Find opportunities in biotechnology with upcoming deadlines"
```

### Tool 3: Analyze Agency Landscape
**Purpose**: Map agencies and their funding patterns

```python
result = await mcp.call_tool("analyze_agency_landscape", {
    "agencies": ["NSF", "NIH", "DOE"],
    "include_opportunities": True,
    "focus_area": "research"
})
```

**In Claude Desktop:**
```
"Analyze the funding landscape for NSF, NIH, and DOE"
"Which agencies are most active in AI research funding?"
```

### Tool 4: Calculate Opportunity Density
**Purpose**: Assess competition levels and funding density

```python
# First, get some opportunity IDs
search_result = await mcp.call_tool("search_grants", {"query": "research"})
opportunity_ids = [opp["opportunity_id"] for opp in search_result["opportunities"]]

# Calculate density
result = await mcp.call_tool("calculate_opportunity_density", {
    "opportunity_ids": opportunity_ids,
    "include_accessibility": True
})
```

**In Claude Desktop:**
```
"Calculate the funding density for these opportunities and rank by competition"
"Which grants have the best funding-to-competition ratio?"
```

### Tool 5: Analyze Budget Distribution
**Purpose**: Understand funding availability across award tiers

```python
result = await mcp.call_tool("analyze_budget_distribution", {
    "category": "Science and Technology",
    "size_focus": "medium",  # micro, small, medium, large, major
    "agency_comparison": True
})
```

**In Claude Desktop:**
```
"Show me the budget distribution for science grants"
"Which funding tier has the most opportunities?"
```

### Tool 6: Cluster Deadlines
**Purpose**: Find strategic application timing

```python
result = await mcp.call_tool("cluster_deadlines", {
    "cluster_method": "monthly",  # monthly, quarterly, agency, category
    "agency_focus": ["NSF"],
    "identify_gaps": True
})
```

**In Claude Desktop:**
```
"When are the best times to submit applications to avoid competition?"
"Show me the deadline clusters for the next 3 months"
```

### Tool 7: Decode Eligibility
**Purpose**: Parse and analyze eligibility requirements

```python
result = await mcp.call_tool("decode_eligibility", {
    "opportunities": opportunity_ids,
    "complexity_scoring": True,
    "institution_type": "university"
})
```

**In Claude Desktop:**
```
"Which grants are universities eligible for?"
"Analyze the eligibility complexity for these opportunities"
```

### Tool 8: Analyze Agency Patterns
**Purpose**: Understand agency-specific funding behaviors

```python
result = await mcp.call_tool("analyze_agency_patterns", {
    "agencies": ["NSF", "NIH"],
    "compare_agencies": True,
    "focus_area": "innovation"
})
```

**In Claude Desktop:**
```
"What are NSF's funding patterns and preferences?"
"Compare NIH and NSF funding strategies"
```

### Tool 9: Identify Opportunity Patterns
**Purpose**: Find patterns in grant characteristics

```python
result = await mcp.call_tool("identify_opportunity_patterns", {
    "category": "Education",
    "focus": "collaboration",
    "include_agency_patterns": True
})
```

**In Claude Desktop:**
```
"What patterns exist in education grants?"
"Which grants favor collaborative projects?"
```

## Resources and Prompts

### Accessing Resources

Resources provide real-time information about the MCP state:

```python
# Get API status
status = await mcp.get_resource("grants://api/status")

# Get search history
history = await mcp.get_resource("grants://search/history")

# Get cached analysis
cache = await mcp.get_resource("grants://cache/analysis/density_analysis")
```

### Using Prompts

Prompts guide you through complex workflows:

```python
# Get landscape exploration prompt
prompt = await mcp.get_prompt("grant_landscape_exploration", {
    "domain": "renewable energy",
    "budget_range": (100000, 1000000)
})

# Get competition assessment prompt
prompt = await mcp.get_prompt("competition_assessment_workshop", {
    "opportunity_ids": ["12345", "67890"]
})
```

## Testing

### Running Unit Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_tools.py

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only fast tests
pytest tests/ -m "not slow"
```

### Integration Testing
```bash
# Test with real API (requires API key)
pytest tests/integration/ --integration

# Test specific workflow
pytest tests/integration/test_discovery_workflow.py
```

### Performance Testing
```bash
# Run performance benchmarks
pytest tests/performance/ --benchmark-only

# Test with large datasets
python tests/performance/test_large_datasets.py
```

## Troubleshooting

### Common Issues and Solutions

#### 1. API Key Issues
**Problem**: "API_KEY not configured" error
```bash
# Solution: Check environment variable
echo $API_KEY

# Set API key
export API_KEY=your_api_key_here

# Or add to .env file
echo "API_KEY=your_api_key_here" >> .env
```

#### 2. Connection Issues
**Problem**: Cannot connect to MCP server
```bash
# Check if server is running
ps aux | grep python | grep main.py

# Test connection
curl -N http://localhost:8787/sse

# Check logs
tail -f logs/mcp.log
```

#### 3. Cloudflare Deployment Issues
**Problem**: Deployment fails
```bash
# Check wrangler configuration
wrangler whoami

# Validate wrangler.toml
wrangler publish --dry-run

# Check error logs
wrangler tail --env production
```

#### 4. Cache Issues
**Problem**: Stale data being returned
```python
# Clear cache programmatically
from src.cache import clear_cache
clear_cache()

# Or via Cloudflare dashboard
# Go to Workers > KV > View namespace > Delete entries
```

#### 5. Rate Limiting
**Problem**: "Rate limit exceeded" errors
```python
# Implement exponential backoff
import time

for attempt in range(3):
    try:
        result = await mcp.call_tool("search_grants", {...})
        break
    except RateLimitError:
        time.sleep(2 ** attempt)
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set in environment
export DEBUG=true

# Or in .env file
DEBUG=true

# Run with verbose logging
python main.py --debug
```

View debug logs:
```bash
# Local logs
tail -f logs/debug.log

# Cloudflare logs
wrangler tail --env development --format pretty
```

## Examples

### Example 1: Complete Grant Discovery Workflow

```python
import asyncio
from src.main import mcp

async def discover_grants_workflow():
    # Step 1: Initial discovery
    print("🔍 Discovering opportunities...")
    opportunities = await mcp.call_tool("discover_opportunities", {
        "domain": "artificial intelligence",
        "max_results": 20
    })
    
    print(f"Found {opportunities['total_found']} opportunities")
    
    # Step 2: Analyze competition
    opportunity_ids = [o["opportunity_id"] for o in opportunities["opportunities"][:10]]
    
    print("📊 Analyzing competition levels...")
    density = await mcp.call_tool("calculate_opportunity_density", {
        "opportunity_ids": opportunity_ids,
        "include_accessibility": True
    })
    
    # Step 3: Check deadlines
    print("📅 Analyzing deadlines...")
    deadlines = await mcp.call_tool("cluster_deadlines", {
        "cluster_method": "monthly",
        "identify_gaps": True
    })
    
    # Step 4: Analyze agencies
    agencies = list(set([o["agency_code"] for o in opportunities["opportunities"][:10]]))
    
    print("🏛️ Analyzing agency patterns...")
    patterns = await mcp.call_tool("analyze_agency_patterns", {
        "agencies": agencies[:3],
        "compare_agencies": True
    })
    
    return {
        "opportunities": opportunities["total_found"],
        "best_density": density["rankings"]["by_density"][0],
        "optimal_timing": deadlines["timing_strategy"]["low_competition_windows"],
        "agency_insights": patterns["recommendations"]
    }

# Run the workflow
result = asyncio.run(discover_grants_workflow())
print(json.dumps(result, indent=2))
```

### Example 2: Agency Deep Dive

```python
async def agency_deep_dive(agency_code):
    # Get agency landscape
    landscape = await mcp.call_tool("analyze_agency_landscape", {
        "agencies": [agency_code],
        "include_opportunities": True
    })
    
    # Get funding patterns
    patterns = await mcp.call_tool("analyze_agency_patterns", {
        "agencies": [agency_code],
        "focus_area": "all"
    })
    
    # Get current opportunities
    opportunities = await mcp.call_tool("search_grants", {
        "filters": {"agency": agency_code},
        "grants_per_page": 20
    })
    
    return {
        "profile": patterns["agency_profiles"][agency_code],
        "active_grants": opportunities["total_found"],
        "funding_focus": landscape["agency_profiles"][agency_code],
        "recommendations": patterns["strategic_insights"]
    }

# Analyze NSF
nsf_analysis = asyncio.run(agency_deep_dive("NSF"))
```

### Example 3: Competition Assessment

```python
async def assess_competition(domain, budget_min, budget_max):
    # Find opportunities
    opportunities = await mcp.call_tool("discover_opportunities", {
        "domain": domain,
        "filters": {
            "award_floor": budget_min,
            "award_ceiling": budget_max
        }
    })
    
    # Calculate density for top opportunities
    top_10_ids = [o["opportunity_id"] for o in opportunities["opportunities"][:10]]
    
    density = await mcp.call_tool("calculate_opportunity_density", {
        "opportunity_ids": top_10_ids
    })
    
    # Analyze eligibility
    eligibility = await mcp.call_tool("decode_eligibility", {
        "opportunities": top_10_ids,
        "complexity_scoring": True
    })
    
    # Find best opportunities
    best_opportunities = []
    for opp_id in top_10_ids:
        if (density["density_analysis"][opp_id]["funding_density_score"] > 200000 and
            eligibility["eligibility_analysis"][opp_id]["complexity_score"] < 5):
            best_opportunities.append(opp_id)
    
    return {
        "total_analyzed": len(top_10_ids),
        "high_value_low_competition": best_opportunities,
        "average_density": sum(d["funding_density_score"] for d in density["density_analysis"].values()) / len(top_10_ids)
    }

# Assess AI grants competition
competition = asyncio.run(assess_competition("artificial intelligence", 100000, 1000000))
```

### Example 4: Using with Claude Desktop

Once connected to Claude Desktop, you can use natural language:

```
User: "Help me find education grants for community colleges"

Claude: I'll help you discover education grants suitable for community colleges. Let me search for relevant opportunities.

[Invokes search_grants tool with appropriate parameters]

I found 47 education grants that may be suitable for community colleges. Here are the key findings:

**Top Opportunities:**
1. STEM Education Innovation Program (ED-IES-2024-012)
   - Award Range: $75,000 - $350,000
   - Deadline: November 20, 2024
   - Eligibility: Higher education institutions including community colleges

[Continues with analysis...]

User: "Which ones have the least competition?"

Claude: Let me analyze the competition levels for these opportunities.

[Invokes calculate_opportunity_density tool]

Based on funding density analysis, these grants have the lowest competition...
```

## Best Practices

### 1. Efficient API Usage
- Cache frequently accessed data
- Batch requests when possible
- Use filters to reduce data transfer

### 2. Error Handling
```python
try:
    result = await mcp.call_tool("search_grants", {...})
except APIError as e:
    # Handle API errors
    logger.error(f"API error: {e}")
    # Use cached data if available
except RateLimitError as e:
    # Handle rate limiting
    await asyncio.sleep(e.retry_after)
    # Retry request
```

### 3. Session Management
```python
# Store session context
session = {
    "user_id": "user123",
    "search_history": [],
    "preferences": {}
}

# Track searches
session["search_history"].append({
    "query": query,
    "timestamp": datetime.now(),
    "results": result["total_found"]
})
```

### 4. Performance Optimization
- Use pagination for large result sets
- Implement progressive loading
- Cache analysis results
- Use concurrent requests when analyzing multiple items

## Support and Resources

### Documentation
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers)
- [Simpler Grants API Documentation](https://api.simpler.grants.gov/docs)

### Getting Help
- GitHub Issues: [Report bugs and request features](https://github.com/yourusername/grantsmanship-mcp/issues)
- Discord Community: [Join our Discord](https://discord.gg/grantsmanship)
- Email Support: support@grantsmanship.dev

### Contributing
We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License
MIT License - see [LICENSE](LICENSE) for details.

---

**Version**: 2.0.0
**Last Updated**: November 2024
**Status**: Production Ready