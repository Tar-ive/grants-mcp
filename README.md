# Grants MCP Server

A Model Context Protocol (MCP) server for comprehensive government grants discovery and analysis, powered by the Simpler Grants API.

## Overview

The Grants MCP Server is a Python-based MCP implementation using FastMCP that provides intelligent tools for discovering, analyzing, and tracking government grant opportunities. It offers multiple specialized tools for different aspects of grant research, from opportunity discovery to funding trend analysis and agency landscape mapping.

## Features

### 🔍 Core Capabilities

- **Grant Opportunity Discovery**: Search and filter grants based on keywords, agencies, funding categories, and eligibility criteria
- **Funding Trend Analysis**: Analyze historical funding patterns and identify emerging opportunities
- **Agency Landscape Mapping**: Understand the grant ecosystem across different government agencies
- **Intelligent Caching**: Built-in caching system to optimize API calls and improve response times
- **Comprehensive Grant Details**: Access detailed information including funding amounts, deadlines, eligibility requirements, and contact information

### 🛠️ Technical Features

- Built with FastMCP for robust MCP server implementation
- Asynchronous Python architecture for high performance
- **Dual Transport Support**: stdio (local) and HTTP (containerized)
- **Docker Support**: Ready-to-deploy containerized version
- Configurable caching with TTL and size limits
- Retry logic and error handling for API resilience
- Environment-based configuration management
- Comprehensive test suite with unit, integration, and live tests

## Quick Start with Docker 🐳

### Prerequisites
- Docker and Docker Compose installed
- Simpler Grants API key (see [Obtaining API Key](#obtaining-api-key))

### 1. Clone the Repository
```bash
git clone https://github.com/Tar-ive/grants-mcp.git
cd grants-mcp
```

### 2. Configure API Key

**Important**: You must provide your own API key. Never commit API keys to version control.

Option A - Using .env file (Recommended):
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your actual API key
# SIMPLER_GRANTS_API_KEY=your_actual_api_key_here
```

Option B - Edit docker-compose.yml directly:
```yaml
environment:
  - SIMPLER_GRANTS_API_KEY=your_actual_api_key_here
```

### 3. Build and Run
```bash
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d

# Check if it's running
docker ps | grep grants-mcp

# View logs
docker logs grants-mcp-server
```

### 4. Test the Server
```bash
# Test with curl
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Or use the provided test script
python scripts/test_http_local.py
```

### 5. Configure Claude Desktop
Copy the Docker configuration to Claude Desktop:
```bash
# For macOS
cp claude_desktop_configs/config_local_docker.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# For Windows
cp claude_desktop_configs/config_local_docker.json \
   %APPDATA%\Claude\claude_desktop_config.json
```

Then restart Claude Desktop to connect to your containerized MCP server.

## Architecture

```
grants-mcp/
├── src/
│   └── mcp_server/
│       ├── server.py              # Main server implementation
│       ├── config/                # Configuration management
│       │   └── settings.py
│       ├── models/                # Data models and schemas
│       │   └── grants_schemas.py
│       ├── tools/
│       │   ├── discovery/         # Grant discovery tools
│       │   │   ├── opportunity_discovery_tool.py
│       │   │   ├── agency_landscape_tool.py
│       │   │   └── funding_trend_scanner_tool.py
│       │   └── utils/             # Utility modules
│       │       ├── api_client.py
│       │       ├── cache_manager.py
│       │       └── cache_utils.py
│       └── prompts/               # System prompts
├── scripts/                       # Testing and deployment scripts
│   ├── test_http_local.py       # Test HTTP endpoint
│   ├── test_http_no_docker.py   # Run HTTP server locally
│   └── debug_connection.sh      # Debug connectivity
├── claude_desktop_configs/        # Claude Desktop configurations
│   ├── config_local_stdio.json  # Direct Python execution
│   ├── config_local_docker.json # Docker via mcp-remote
│   └── config_both.json         # Both options
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Container definition
└── tests/                        # Comprehensive test suite
```

## Deployment Options

### Option 1: Docker (Recommended for Production)

The Docker deployment provides:
- Consistent environment across platforms
- Easy scaling and deployment
- Isolation from system dependencies
- Ready for cloud deployment (Google Cloud Run, AWS ECS, etc.)

```bash
# Quick start
docker-compose up -d

# Stop the server
docker-compose down

# View logs
docker logs grants-mcp-server --follow

# Rebuild after code changes
docker-compose build && docker-compose up -d
```

### Option 2: Local Python Installation

For development and testing:

```bash
# Install dependencies
pip install -r requirements.txt

# Run with stdio transport (for direct integration)
SIMPLER_GRANTS_API_KEY=your_key python main.py

# Run with HTTP transport (for testing containerization locally)
MCP_TRANSPORT=http PORT=8080 SIMPLER_GRANTS_API_KEY=your_key python main.py
```

## Obtaining API Key

The Simpler Grants API key is required for this MCP server to function. To get your API key:

1. Visit [Simpler Grants API](https://api.simpler.grants.gov)
2. Sign up for an account or log in
3. Navigate to your API settings/dashboard
4. Generate or copy your API key
5. Keep this key secure - you'll need it for configuration

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SIMPLER_GRANTS_API_KEY` | API key for Grants.gov (required) | - |
| `MCP_TRANSPORT` | Transport mode: `stdio` or `http` | `stdio` |
| `PORT` | HTTP server port (container mode) | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CACHE_TTL` | Cache time-to-live (seconds) | `300` |
| `MAX_CACHE_SIZE` | Maximum cache entries | `1000` |

### Docker Configuration

The `docker-compose.yml` file includes:
- Port mapping: 8081 (host) → 8080 (container)
- Resource limits: 1 CPU, 1GB RAM
- Auto-restart policy
- Health checks with proper SSE headers

## Available Tools

### 1. opportunity_discovery
Search for grant opportunities with detailed analysis.

**Parameters:**
- `query`: Search keywords (e.g., "renewable energy", "climate change")
- `filters`: Advanced filter parameters
- `max_results`: Maximum number of results (default: 100)
- `page`: Page number for pagination
- `grants_per_page`: Grants per page (default: 3)

### 2. agency_landscape
Map agencies and their funding focus areas.

**Parameters:**
- `include_opportunities`: Include opportunity analysis (default: true)
- `focus_agencies`: Specific agency codes (e.g., ["NSF", "NIH"])
- `funding_category`: Filter by category
- `max_agencies`: Maximum agencies to analyze (default: 10)

### 3. funding_trend_scanner
Analyze funding trends and patterns.

**Parameters:**
- `time_window_days`: Analysis period (default: 90)
- `category_filter`: Filter by category
- `agency_filter`: Filter by agency
- `min_award_amount`: Minimum award filter
- `include_forecasted`: Include forecasted opportunities (default: true)

## Claude Desktop Integration

### For Docker Deployment
1. Ensure Docker container is running: `docker-compose up -d`
2. Install mcp-remote if needed: `npm install -g mcp-remote`
3. Copy configuration:
   ```bash
   # macOS
   cp claude_desktop_configs/config_local_docker.json \
      ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
4. Restart Claude Desktop

### For Local Development
1. Copy the stdio configuration:
   ```bash
   # macOS
   cp claude_desktop_configs/config_local_stdio.json \
      ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
2. Update the path in the config to your local installation
3. Restart Claude Desktop

## Testing

### Test Docker Deployment
```bash
# Run test script
python scripts/test_http_local.py

# Debug connection issues
bash scripts/debug_connection.sh

# Manual test with curl
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### Run Test Suite
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/live/  # Requires API key
```

## Troubleshooting

### Port Conflicts
If port 8081 is in use:
```bash
# Check what's using the port
lsof -i :8081

# Edit docker-compose.yml to use a different port
# Change "8081:8080" to "8082:8080"
```

### Container Issues
```bash
# Check container status
docker ps -a | grep grants-mcp

# View detailed logs
docker logs grants-mcp-server --tail 100

# Restart container
docker-compose restart

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### API Key Issues
- Ensure `SIMPLER_GRANTS_API_KEY` is set in docker-compose.yml
- Check logs for authentication errors: `docker logs grants-mcp-server`
- Verify API key is valid at [Simpler Grants API](https://api.simpler.grants.gov)

## Cloud Deployment

The containerized version is ready for cloud deployment:

### Google Cloud Run
```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT/grants-mcp

# Deploy to Cloud Run
gcloud run deploy grants-mcp \
  --image gcr.io/YOUR_PROJECT/grants-mcp \
  --platform managed \
  --port 8080 \
  --set-env-vars SIMPLER_GRANTS_API_KEY=your_key
```

### AWS ECS / Fargate
See `specs/cloud_deployment.md` for detailed AWS deployment instructions.

## Development

### Project Structure
- `src/mcp_server/`: Core server implementation
- `scripts/`: Testing and utility scripts
- `tests/`: Comprehensive test suite
- `specs/`: Technical specifications and documentation
- `claude_desktop_configs/`: Ready-to-use Claude Desktop configurations

### Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Ensure tests pass: `pytest`
5. Build and test Docker image: `docker-compose build && docker-compose up -d`
6. Commit with descriptive messages
7. Push and create a pull request

## Roadmap

- [x] Phase 1: Python implementation with FastMCP
- [x] Phase 2: Enhanced discovery tools
- [x] Phase 3: Docker containerization
- [ ] Phase 4: Intelligent scoring system
- [ ] Phase 5: Cloud deployment automation
- [ ] Phase 6: Multi-agency comparison tools
- [ ] Phase 7: Grant application assistance

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Powered by [Simpler Grants API](https://simpler.grants.gov)
- Model Context Protocol by Anthropic

## Support

For issues, questions, or contributions:
- Open an issue on [GitHub](https://github.com/Tar-ive/grants-mcp/issues)
- Check the [Deployment Guide](DEPLOYMENT_GUIDE.md) for detailed instructions
- Review `specs/` directory for technical documentation

---

**Note**: This is an alpha release. API and features may change. Use in production with caution.# Deployment Test

Service accounts and permissions are now properly configured!
