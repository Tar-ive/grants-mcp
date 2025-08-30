# Grants MCP Server - Deployment & Testing Guide

## Overview
The Grants MCP server now supports both local (stdio) and containerized (HTTP) deployment modes. This guide covers local testing, Docker deployment, and Claude Desktop integration.

## Architecture
- **Local Mode**: Uses stdio transport for direct integration
- **Container Mode**: Uses HTTP transport with SSE (Server-Sent Events) for scalable deployment
- **Port Configuration**: Default port 8081 (mapped from container's 8080)

## Prerequisites
- Python 3.11+ (for local development)
- Docker & Docker Compose (for containerized deployment)
- Node.js & npm (for mcp-remote proxy)
- API Key from Simpler Grants (`SIMPLER_GRANTS_API_KEY`)

## Quick Start

### 1. Local Development (stdio)
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally with stdio transport
SIMPLER_GRANTS_API_KEY=your_key_here python main.py

# Or set transport explicitly
MCP_TRANSPORT=stdio SIMPLER_GRANTS_API_KEY=your_key_here python main.py
```

### 2. Docker Deployment
```bash
# Build and start container
docker-compose build
docker-compose up -d

# Check status
docker ps | grep grants-mcp
docker logs grants-mcp-server

# Stop container
docker-compose down
```

### 3. Testing the Container
```bash
# Test with curl (requires proper headers)
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Test with Python script
python scripts/test_http_local.py

# Debug connection issues
bash scripts/debug_connection.sh
```

## Claude Desktop Integration

### Option 1: Local stdio (Direct)
Copy configuration to Claude Desktop:
```bash
# Use the local stdio config
cp claude_desktop_configs/config_local_stdio.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
```

### Option 2: Docker Container (via mcp-remote)
```bash
# First ensure container is running
docker-compose up -d

# Install mcp-remote if needed
npm install -g mcp-remote

# Use the Docker config
cp claude_desktop_configs/config_local_docker.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
```

### Option 3: Both Configurations
```bash
# Use both configs for testing
cp claude_desktop_configs/config_both.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
# You'll see both "grantsmanship-local" and "grantsmanship-docker" options
```

## Configuration Files

### docker-compose.yml
- Port: 8081 (host) -> 8080 (container)
- Environment variables configured
- Resource limits: 1 CPU, 1GB RAM
- Auto-restart policy

### Dockerfile
- Based on Python 3.11-slim
- Health check with proper SSE headers
- Optimized layer caching

### Claude Desktop Configs
- **config_local_stdio.json**: Direct Python execution
- **config_local_docker.json**: Container via mcp-remote proxy
- **config_both.json**: Both options for comparison

## Available MCP Tools

1. **opportunity_discovery**: Search and analyze grant opportunities
   - Parameters: query, filters, max_results, page, grants_per_page
   
2. **agency_landscape**: Map agencies and funding patterns
   - Parameters: include_opportunities, focus_agencies, funding_category
   
3. **funding_trend_scanner**: Analyze funding trends
   - Parameters: time_window_days, category_filter, agency_filter

## Troubleshooting

### Port Conflicts
If port 8081 is in use:
```bash
# Check what's using the port
lsof -i :8081

# Modify docker-compose.yml to use different port
# Change "8081:8080" to "8082:8080" (or another free port)
```

### Container Health Issues
```bash
# Check container health
docker ps | grep grants-mcp

# View detailed logs
docker logs grants-mcp-server --tail 100

# Restart container
docker-compose restart
```

### Claude Desktop Not Connecting
1. Ensure container is running and healthy
2. Verify mcp-remote is installed: `npm list -g mcp-remote`
3. Check Claude Desktop logs for errors
4. Restart Claude Desktop after config changes

### API Key Issues
Ensure API key is set in:
- Environment variable: `SIMPLER_GRANTS_API_KEY`
- docker-compose.yml: `API_KEY` or `SIMPLER_GRANTS_API_KEY`
- Claude Desktop config: env section

## Development Workflow

1. **Local Development**:
   - Edit code in `src/` directory
   - Test with stdio transport locally
   - Run unit tests

2. **Container Testing**:
   - Rebuild: `docker-compose build`
   - Test HTTP endpoint
   - Check logs for errors

3. **Production Deployment**:
   - Build production image
   - Deploy to Google Cloud Run or similar
   - Configure with production API keys

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | Transport mode (stdio/http) | stdio |
| `PORT` | HTTP server port | 8080 |
| `SIMPLER_GRANTS_API_KEY` | API key for Grants.gov | Required |
| `LOG_LEVEL` | Logging level | INFO |
| `CACHE_TTL` | Cache time-to-live (seconds) | 300 |
| `MAX_CACHE_SIZE` | Maximum cache entries | 1000 |

## Security Notes
- Never commit API keys to version control
- Use environment variables or secrets management
- Container runs as non-root user (recommended)
- Health checks don't expose sensitive data

## Next Steps
1. Deploy to Google Cloud Run (see `specs/cloud_deployment.md`)
2. Set up monitoring and alerting
3. Configure production API keys
4. Implement rate limiting if needed

## Support
For issues or questions:
- Check logs: `docker logs grants-mcp-server`
- Debug script: `bash scripts/debug_connection.sh`
- Review specs in `specs/` directory