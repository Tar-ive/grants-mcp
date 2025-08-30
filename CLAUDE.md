# Grants MCP Server - Claude AI Integration Guide

## Overview
This is a Model Context Protocol (MCP) server for comprehensive government grants discovery and analysis. It provides intelligent tools for finding, analyzing, and strategically planning grant applications using the Simpler Grants API.

## Current Implementation Status

### ✅ Phase 1 & 2: Core Tools (Implemented)
**Currently Available Tools:**

1. **`opportunity_discovery`** - Search and analyze grant opportunities
   - Advanced filtering by agency, funding category, eligibility
   - Pagination support with customizable grants per page
   - Comprehensive grant details including deadlines and contacts

2. **`agency_landscape`** - Map agencies and their funding patterns  
   - Agency-specific funding focus analysis
   - Cross-agency collaboration opportunities
   - Funding distribution insights

3. **`funding_trend_scanner`** - Analyze funding trends and patterns
   - Temporal trend analysis over customizable time windows
   - Emerging topic detection
   - Category and agency-specific trend analysis

### 🚧 Phase 3: Advanced Analytics (Planned)
**Planned Additional Tools:**

4. **`grant_match_scorer`** - Intelligent grant scoring system
   - Technical fit scoring (keyword matching, category alignment)
   - Competition index calculation (based on NIH/NSF methodologies)
   - ROI analysis with effort-adjusted calculations
   - Success probability scoring
   - Multi-dimensional scoring with transparent calculations

5. **`hidden_opportunity_finder`** - Discover undersubscribed grants
   - Under-subscribed grants detection
   - Emerging funders identification  
   - Cross-category matching opportunities
   - Geographic advantage analysis
   - Timing arbitrage opportunities

6. **`strategic_application_planner`** - Portfolio optimization
   - Application portfolio diversification (reach/match/safety)
   - Timeline optimization across multiple applications
   - Collaboration opportunity suggestions
   - Resource allocation guidance
   - Resubmission strategy planning

## Quick Setup

### Docker Deployment (Recommended)
```bash
# Clone and navigate
git clone https://github.com/Tar-ive/grants-mcp.git
cd grants-mcp

# Configure API key (get from https://api.simpler.grants.gov)
cp .env.example .env
# Edit .env and add: SIMPLER_GRANTS_API_KEY=your_key_here

# Build and run
docker-compose build
docker-compose up -d

# Verify it's working
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### Claude Desktop Integration
```bash
# For Docker setup
cp claude_desktop_configs/config_local_docker.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# For local Python setup  
cp claude_desktop_configs/config_local_stdio.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Update the API key in the config file, then restart Claude Desktop
```

## Usage Examples

### Basic Grant Search
"Find renewable energy grants with funding over $500,000"

### Agency Analysis
"Show me the funding landscape for the Department of Energy, focusing on climate research opportunities"

### Trend Analysis
"Analyze funding trends for artificial intelligence research over the last 6 months"

### Advanced Filtering
"Search for NSF grants in computer science with deadlines in the next 90 days, show 5 per page"

## API Configuration

### Required Environment Variables
- `SIMPLER_GRANTS_API_KEY` - Your API key from Simpler Grants API (required)

### Optional Configuration
- `MCP_TRANSPORT` - Transport mode: `stdio` (default) or `http`  
- `PORT` - HTTP server port for containerized mode (default: 8080)
- `LOG_LEVEL` - Logging level (default: INFO)
- `CACHE_TTL` - Cache time-to-live in seconds (default: 300)
- `MAX_CACHE_SIZE` - Maximum cache entries (default: 1000)

## Architecture

### Current Stack
- **Framework**: FastMCP (Python MCP implementation)
- **Language**: Python 3.11+
- **API Client**: httpx with async support
- **Caching**: In-memory cache with TTL and LRU eviction
- **Validation**: Pydantic v2 models
- **Transport**: stdio (local) / HTTP (containerized)

### Planned Phase 3 Enhancements
- **Analytics Engine**: NumPy-powered scoring calculations
- **Database**: SQLite for session persistence
- **Metrics**: Industry-standard NIH/NSF methodologies
- **Transparency**: Explainable AI with calculation breakdowns

## Performance Features
- ✅ Intelligent caching reduces API calls by 60-80%
- ✅ Async architecture for concurrent operations
- ✅ Retry logic and error handling for reliability
- ✅ Pagination support for large result sets
- 🚧 Vectorized calculations for scoring (Phase 3)
- 🚧 Session persistence for long-term analysis (Phase 3)

## Troubleshooting

### Common Issues
1. **API Key Error**: Ensure `SIMPLER_GRANTS_API_KEY` is set correctly
2. **Port Conflicts**: Docker uses 8081, check `lsof -i :8081`
3. **Claude Desktop Not Connecting**: Verify config path and restart Claude Desktop
4. **Container Issues**: Check logs with `docker logs grants-mcp-server`

### Debug Commands
```bash
# Test HTTP endpoint
python scripts/test_http_local.py

# Debug connection issues  
bash scripts/debug_connection.sh

# Check container status
docker ps | grep grants-mcp
docker logs grants-mcp-server --tail 50
```

## Development Status

### Completed (Ready for Production)
- [x] Core grant discovery functionality
- [x] Agency landscape mapping
- [x] Funding trend analysis  
- [x] Docker containerization
- [x] Claude Desktop integration
- [x] Comprehensive caching system
- [x] Error handling and retry logic

### In Development (Phase 3)
- [ ] Grant match scoring algorithm
- [ ] Hidden opportunity detection
- [ ] Strategic planning tools
- [ ] Session persistence
- [ ] Advanced analytics dashboard

## Mathematical Foundations (Phase 3)

The scoring system will use industry-standard methodologies:

**Competition Index**: Based on NIH success rate calculations
**Success Probability**: Adapted from NSF percentile methodology  
**ROI Analysis**: Research funding efficiency metrics
**Timing Score**: Preparation adequacy assessment
**Hidden Opportunity Score**: Novel undersubscription detection

All calculations will provide transparent breakdowns showing exactly how scores are computed.

## Contributing

This is an open-source project. Key areas for contribution:
- Phase 3 analytics tools implementation
- Additional API integrations (state/local grants)
- Advanced filtering capabilities
- Performance optimizations
- UI/dashboard development

## Support & Documentation

- **Repository**: https://github.com/Tar-ive/grants-mcp
- **Deployment Guide**: `DEPLOYMENT_GUIDE.md`
- **Phase 3 Specifications**: `specs/phase3.md`  
- **API Documentation**: Built-in tool descriptions via `tools/list`

---

**Note**: This is an active development project. Phase 1-2 features are production-ready, Phase 3 analytics tools are in planning/development phase.