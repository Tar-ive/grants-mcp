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
- Configurable caching with TTL and size limits
- Retry logic and error handling for API resilience
- Environment-based configuration management
- Comprehensive test suite with unit, integration, and live tests

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
└── tests/                         # Comprehensive test suite
    ├── unit/
    ├── integration/
    ├── contract/
    ├── edge_cases/
    ├── performance/
    └── live/
```

## Prerequisites

- Python 3.11 or higher
- Node.js 16+ (for MCP client compatibility)
- Simpler Grants API key (see below)

## Getting Started

### Obtaining API Key

The Simpler Grants API key is required for this MCP server to function. To get your API key:

1. Visit [Simpler Grants API](https://api.simpler.grants.gov)
2. Sign up for an account or log in
3. Navigate to your API settings/dashboard
4. Generate or copy your API key
5. Keep this key secure - you'll need it for configuration

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Tar-ive/grants-mcp.git
cd grants-mcp
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your API_KEY for Simpler Grants API
```

## Configuration

The server uses environment variables for configuration. Create a `.env` file with:

```env
# Required
API_KEY=your_simpler_grants_api_key

# Optional (with defaults)
API_BASE_URL=https://api.simpler.grants.gov
REQUEST_TIMEOUT=30
MAX_RETRIES=3
CACHE_TTL=3600
MAX_CACHE_SIZE=100
LOG_LEVEL=INFO
SERVER_NAME=grants-analysis-server
SERVER_VERSION=0.1.0
```

## Usage

### Starting the Server

Run the MCP server:
```bash
python -m src.mcp_server.server
```

### Setting up with Claude Desktop

1. **Open Claude Desktop settings**:
   - On macOS: Claude → Settings → Developer
   - On Windows: File → Settings → Developer

2. **Add the MCP server configuration**:
   
   Edit your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

   Add the following to the `mcpServers` section:
   ```json
   {
     "mcpServers": {
       "grants-mcp": {
         "command": "python",
         "args": ["-m", "src.mcp_server.server"],
         "cwd": "/path/to/grants-mcp",
         "env": {
           "API_KEY": "your_simpler_grants_api_key"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the new configuration

4. **Verify connection**: The server tools should appear in Claude's tool list

### Setting up with Claude Code

1. **Install Claude Code** if you haven't already:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **Configure MCP server in your project**:
   
   Create or update `.claude/mcp_config.json` in your project root:
   ```json
   {
     "servers": {
       "grants-mcp": {
         "command": "python",
         "args": ["-m", "src.mcp_server.server"],
         "cwd": ".",
         "env": {
           "API_KEY": "${SIMPLER_GRANTS_API_KEY}"
         }
       }
     }
   }
   ```

3. **Set environment variable**:
   ```bash
   export SIMPLER_GRANTS_API_KEY=your_api_key_here
   ```

4. **Start Claude Code** in your project directory:
   ```bash
   claude-code
   ```

5. **The MCP tools will be automatically available** in your Claude Code session

### Available Tools

Once connected, the server exposes these tools:
- `search-grants`: Search for grant opportunities
- `analyze-funding-trends`: Analyze funding patterns  
- `map-agency-landscape`: Explore agency grant distributions

### Example Usage

Once connected, you can use natural language queries like:
- "Find grants related to artificial intelligence research"
- "Show me climate change grants with funding over $1 million"
- "Analyze funding trends for renewable energy projects"
- "Map the grant landscape for the Department of Energy"

## API Integration

This MCP server integrates with the [Simpler Grants API](https://api.simpler.grants.gov/openapi.json), which provides:
- Comprehensive grant opportunity data
- Advanced search and filtering capabilities
- Historical funding information
- Agency and category metadata

The API is currently in alpha, designed for testing and feedback.

## Development

### Running Tests

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

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
pylint src/

# Type checking
mypy src/
```

## Testing Strategy

The project includes comprehensive testing:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Contract Tests**: Validate API responses
- **Edge Case Tests**: Handle error conditions
- **Performance Tests**: Ensure efficiency at scale
- **Live Tests**: Validate against real API (requires API key)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Ensure tests pass: `pytest`
5. Commit with descriptive messages
6. Push and create a pull request

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your `API_KEY` environment variable is set correctly
2. **Connection Issues**: Check your internet connection and API endpoint availability
3. **Cache Issues**: Clear cache or adjust `CACHE_TTL` if seeing stale data
4. **Python Version**: Ensure you're using Python 3.11+

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m src.mcp_server.server
```

## Roadmap

- [ ] Advanced filtering capabilities
- [ ] Grant deadline notifications
- [ ] Multi-agency comparison tools
- [ ] Grant application assistance
- [ ] Historical success rate analysis
- [ ] Export functionality (CSV, JSON, PDF)

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Powered by [Simpler Grants API](https://simpler.grants.gov)
- Model Context Protocol by Anthropic

## Support

For issues, questions, or contributions, please:
- Open an issue on [GitHub](https://github.com/Tar-ive/grants-mcp/issues)
- Check existing issues for solutions
- Provide detailed error messages and steps to reproduce

---

**Note**: This is an alpha release. API and features may change. Use in production with caution.