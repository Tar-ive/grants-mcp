# Testing Guide for Grants MCP Server

## Quick Start Testing

### 1. Basic Functionality Test
Tests core components (cache, API, search):
```bash
python3 test_basic.py
```

### 2. Direct Component Test
Tests MCP components without running the full server:
```bash
python3 test_mcp_direct.py
```

## Automated Test Suites

### Unit Tests (Fast, No API)
```bash
# Run all unit tests
make test-unit

# Run specific test file
python3 -m pytest tests/unit/test_cache_manager.py -v

# Run with coverage
python3 -m pytest tests/unit --cov=src --cov-report=html
```

### Integration Tests (Mocked API)
```bash
# Run integration tests
make test-integration

# Run specific integration test
python3 -m pytest tests/integration/test_opportunity_discovery.py -v
```

### Live API Tests (Real API)
```bash
# Requires valid API_KEY in .env
make test-live

# Or directly with pytest
USE_REAL_API=true python3 -m pytest tests/live -m real_api -v
```

## Manual Testing with MCP Server

### Option 1: Run Server Directly
```bash
# Start the MCP server
python3 main.py

# The server will wait for MCP commands via stdio
# Press Ctrl+C to stop
```

### Option 2: Use with Claude Desktop

1. Add to Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "grantsmanship": {
      "command": "python3",
      "args": ["/full/path/to/grants-mcp/main.py"]
    }
  }
}
```

2. Restart Claude Desktop

3. In Claude, you can now use commands like:
   - "Search for renewable energy grants"
   - "Find grants related to artificial intelligence"
   - "Look for climate change funding opportunities"

### Option 3: Test with MCP Inspector

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run the inspector
npx @modelcontextprotocol/inspector python3 main.py

# Open browser to the URL shown (usually http://localhost:5173)
# You can interact with the MCP server through the web interface
```

## Testing Specific Features

### Test Cache Performance
```python
# In Python REPL
from src.mcp_server.tools.utils.cache_manager import InMemoryCache

cache = InMemoryCache(ttl=60, max_size=100)
cache.set("key1", {"data": "test"})
result = cache.get("key1")  # Should hit cache
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

### Test API Client Directly
```python
import asyncio
from src.mcp_server.tools.utils.api_client import SimplerGrantsAPIClient

async def test_api():
    client = SimplerGrantsAPIClient(api_key="your_key")
    response = await client.search_opportunities(
        query="technology",
        pagination={"page_size": 5, "page_offset": 1}
    )
    print(f"Found {len(response['data'])} grants")
    await client.close()

asyncio.run(test_api())
```

### Test Search Functionality
```python
# Run test_mcp_direct.py which tests all major components
python3 test_mcp_direct.py
```

## Troubleshooting Common Issues

### Issue: ModuleNotFoundError
```bash
# Install all dependencies
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt
```

### Issue: API_KEY not found
```bash
# Create .env file with your API key
echo "API_KEY=your_actual_api_key" > .env
```

### Issue: Tests failing with API errors
- Check API key is valid
- Ensure internet connection
- API might be rate limited (wait and retry)

### Issue: Cache tests failing
- Check system time is correct
- Ensure enough memory available

## Performance Testing

### Check Response Times
```bash
# Time a search operation
time python3 -c "
import asyncio
from test_mcp_direct import test_direct
asyncio.run(test_direct())
"
```

### Monitor Cache Effectiveness
Run the same search multiple times and check cache hit rate increases:
```bash
python3 test_mcp_direct.py
# Note the cache stats in output
```

## Test Coverage Report

```bash
# Generate HTML coverage report
python3 -m pytest tests/ --cov=src --cov-report=html

# Open report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Continuous Testing

### Watch Mode (auto-run tests on file changes)
```bash
# Install pytest-watch
pip3 install pytest-watch

# Run tests in watch mode
ptw tests/unit
```

### Pre-commit Testing
```bash
# Before committing, run all tests
make test
make test-live  # If you want to test with real API
```

## Expected Test Results

### Successful Basic Test Output
```
✅ Environment loaded
✅ Cache working correctly
✅ API health check: healthy
✅ API search successful: Found 2 results
```

### Successful Unit Test Output
```
tests/unit/test_cache_manager.py::TestInMemoryCache::test_cache_stores_and_retrieves_data PASSED
... (all tests passing)
```

### Successful Component Test Output  
```
Found 3 grants (total: 20)
✅ Cache working: Data stored and retrieved
✅ All component tests passed!
```

## Next Steps

1. Run `python3 test_basic.py` to verify installation
2. Run `make test` to run all automated tests
3. Configure Claude Desktop to use the server
4. Start building additional tools in Phase 2!

## Support

If tests are failing:
1. Check the error messages carefully
2. Ensure all dependencies are installed
3. Verify API key is valid and set in .env
4. Check internet connectivity
5. Review logs for detailed error information