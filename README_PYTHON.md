# Grants Analysis MCP Server (Python Implementation)

## Overview

This is the Python implementation of the Grants Analysis MCP Server, migrated from the original TypeScript version. It provides comprehensive tools for discovering and analyzing government grants using the Simpler Grants API.

## Features

### Phase 1 (Completed)
- ✅ Python project structure with FastMCP
- ✅ Core server implementation with stdio transport
- ✅ In-memory cache with TTL support (5-minute default)
- ✅ Simpler Grants API client with retry logic
- ✅ Opportunity discovery tool (port of search-grants)
- ✅ Comprehensive test suite following testing_v3.md
- ✅ Feature parity with TypeScript version

### Upcoming Features
- Agency landscape analysis tool
- Funding trend scanner (current vs forecasted)
- Opportunity density calculator
- Budget distribution analyzer
- Deadline clustering tool
- Eligibility decoder
- Agency pattern recognition
- Resource endpoints for monitoring

## Installation

1. **Install Python 3.10+**
   ```bash
   python --version  # Should be 3.10 or higher
   ```

2. **Install dependencies**
   ```bash
   make install
   # or manually:
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Configure API Key**
   
   Create a `.env` file in the project root:
   ```env
   API_KEY=your_simpler_grants_api_key
   ```

## Usage

### Running the MCP Server

```bash
# Using make
make run

# Or directly
python main.py
```

### Using with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "grantsmanship": {
      "command": "python",
      "args": ["/path/to/grants-mcp/main.py"]
    }
  }
}
```

## Testing

### Run All Tests (Mocked)
```bash
make test
```

### Run Unit Tests Only
```bash
make test-unit
```

### Run Integration Tests
```bash
make test-integration
```

### Run Live API Tests
```bash
# Requires valid API_KEY in .env
make test-live
```

### Test Coverage Report
```bash
make test-coverage
# Open htmlcov/index.html to view coverage report
```

## Project Structure

```
grants-mcp/
├── main.py                          # Entry point
├── pyproject.toml                   # Python project configuration
├── requirements.txt                 # Core dependencies
├── requirements-dev.txt             # Development dependencies
├── .env                            # API key configuration (create this)
├── src/
│   └── mcp_server/
│       ├── server.py               # Main MCP server
│       ├── config/
│       │   └── settings.py         # Configuration management
│       ├── models/
│       │   └── grants_schemas.py   # Pydantic models
│       ├── tools/
│       │   ├── discovery/
│       │   │   └── opportunity_discovery_tool.py
│       │   └── utils/
│       │       ├── api_client.py   # Simpler Grants API client
│       │       └── cache_manager.py # In-memory cache
│       ├── resources/              # MCP resources
│       └── prompts/                # MCP prompts
└── tests/
    ├── conftest.py                 # Test configuration
    ├── .env.test                   # Test environment
    ├── unit/                       # Unit tests
    ├── integration/                # Integration tests
    └── live/                       # Real API tests
```

## Available Tools

### opportunity_discovery
Search for grant opportunities with comprehensive filtering and analysis.

**Parameters:**
- `query` (optional): Search keywords
- `filters` (optional): Advanced filtering options
- `max_results`: Maximum results to retrieve (default: 100)
- `page`: Display page number (default: 1)
- `grants_per_page`: Grants per page (default: 3)

**Example usage in Claude:**
```
Search for renewable energy grants
```

## Architecture Decisions

1. **Simple In-Memory Cache**: Ephemeral cache with 5-minute TTL for API responses
2. **Private Tool**: API key authentication for secure access
3. **Current/Forecasted Focus**: No historical data tracking
4. **Local Deployment**: Standard Python deployment (not edge/Cloudflare)
5. **Test-Driven Development**: Following testing_v3.md specifications

## Performance Metrics

- Response time: < 5s for standard queries (< 0.5s with cache)
- Memory usage: < 200MB typical operation
- Cache hit rate: > 50% in normal usage
- Concurrent requests: Handles 5+ simultaneous requests

## Troubleshooting

### API Key Issues
- Ensure `API_KEY` is set in `.env` file
- Check API key validity with Simpler Grants

### Test Failures
- Run `pytest -v` for detailed output
- Check `.env.test` for test configuration
- Ensure all dependencies are installed

### Performance Issues
- Monitor cache statistics via API status resource
- Check API rate limits
- Review server logs for errors

## Migration from TypeScript

This Python implementation maintains full compatibility with the TypeScript version while adding:
- Enhanced caching with TTL
- Better error handling with retries
- Comprehensive test coverage
- Structured data models with Pydantic
- Performance monitoring capabilities

## Contributing

1. Write tests first (TDD approach)
2. Follow Python code style (black, ruff)
3. Update documentation for new features
4. Run full test suite before committing

## License

MIT License - See LICENSE file for details