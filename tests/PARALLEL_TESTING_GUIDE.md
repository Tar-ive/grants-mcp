# Comprehensive Parallel Testing Guide

## Overview

This guide covers the comprehensive parallel testing infrastructure for the Grants MCP server, including both Python and TypeScript implementations, with GitHub Actions CI/CD pipeline and multiple testing strategies.

## Testing Architecture

### Test Categories

1. **Unit Tests** (`tests/unit/`) - Fast, isolated component tests
2. **Integration Tests** (`tests/integration/`) - Component interaction tests with mocked dependencies
3. **Contract Tests** (`tests/contract/`) - API schema and protocol compliance tests
4. **Performance Tests** (`tests/performance/`) - Load, stress, and benchmark tests
5. **Edge Case Tests** (`tests/edge_cases/`) - Error handling and boundary condition tests
6. **Live API Tests** (`tests/live/`) - Real-world scenarios with actual API
7. **TypeScript Tests** (`tests/typescript/`) - Node.js MCP server tests

### Parallel Execution Strategy

The testing infrastructure is designed for maximum parallelization:

- **Matrix Testing**: Multiple Python versions (3.9-3.12) and OS platforms (Ubuntu, macOS, Windows)
- **Categorized Parallel Jobs**: Different test types run in parallel
- **Concurrent API Testing**: Multiple search scenarios executed simultaneously
- **Performance Testing**: Isolated performance benchmarks
- **Containerized Testing**: Docker-based deployment validation

## Quick Start

### 1. Local Development Testing

```bash
# Install all dependencies
pip install -r requirements.txt -r requirements-dev.txt
npm install

# Run basic test suite
pytest tests/unit/ tests/integration/ -v

# Run TypeScript tests
npm test

# Run performance tests
pytest tests/performance/ --benchmark-only

# Run with coverage
pytest --cov=src --cov-report=html
```

### 2. GitHub Actions Pipeline

The CI/CD pipeline automatically runs when:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch

**Pipeline Jobs:**
1. Code Quality & Linting (Fast feedback)
2. Unit Tests (Matrix: Python 3.9-3.12, Ubuntu/macOS/Windows)
3. Integration Tests (Parallel by category)
4. TypeScript Tests (Node.js 18, 20, 21)
5. Contract Tests (API schema validation)
6. Performance Tests (Optional, main branch only)
7. Live API Tests (Optional, with secrets)
8. Docker Tests (Container deployment)
9. Edge Case Tests (Parallel by scenario)
10. Results Aggregation & Coverage Report

## Test Execution Examples

### Python Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test categories
pytest -m "unit" -v
pytest -m "integration" -v
pytest -m "contract" -v
pytest -m "performance" --benchmark-only
pytest -m "edge_case" -v

# Run with live API (requires API_KEY)
USE_REAL_API=true pytest tests/live/ -m real_api -v

# Parallel execution with pytest-xdist
pytest -n auto tests/unit/ tests/integration/

# Run specific test scenarios
pytest tests/performance/test_concurrent_operations.py::TestConcurrentPerformance::test_concurrent_api_requests -v

# Memory profiling
pytest tests/performance/ --profile-svg

# Coverage with branch analysis
pytest --cov=src --cov-branch --cov-report=term-missing
```

### TypeScript Tests

```bash
# Run all TypeScript tests
npm test

# Watch mode for development
npm run test:watch

# Coverage report
npm run test:coverage

# CI mode (for GitHub Actions)
npm run test:ci

# Run specific test suites
npx jest tests/typescript/test_grants_mcp.test.ts --verbose

# Debug mode
npx jest --runInBand --verbose tests/typescript/
```

## Test Scenarios

### Real-World Grant Search Tests

The test suite includes comprehensive real-world scenarios:

1. **AI Research Grants**
   ```python
   # tests/live/test_real_world_scenarios.py
   async def test_ai_research_grants(self, real_api_client):
       query = "artificial intelligence machine learning"
       response = await real_api_client.search_opportunities(query=query, ...)
   ```

2. **Climate Change Grants**
   ```python
   async def test_climate_change_grants(self, real_api_client):
       query = "climate change environmental sustainability"
       # Analyzes funding amounts and agency distribution
   ```

3. **Healthcare Innovation**
   ```python
   async def test_healthcare_innovation_grants(self, real_api_client):
       queries = [
           "healthcare innovation medical technology",
           "biomedical research drug development",
           "health disparities community health"
       ]
   ```

### Performance Testing Scenarios

1. **Concurrent Operations**
   ```python
   # tests/performance/test_concurrent_operations.py
   async def test_concurrent_api_requests(self, benchmark):
       # Tests 20 concurrent API requests
       results = benchmark(asyncio.run, make_concurrent_requests(20))
   ```

2. **Cache Performance**
   ```python
   def test_cache_concurrent_access(self, benchmark):
       # Tests cache with 10 concurrent workers, 1000 operations
       results = benchmark(concurrent_cache_operations, 1000)
   ```

3. **Memory Usage**
   ```python
   def test_memory_usage_under_load(self):
       # Monitors memory growth during 50,000 cache operations
   ```

### Edge Cases & Error Handling

1. **Network Failures**
   ```python
   # tests/edge_cases/test_error_scenarios.py
   async def test_connection_timeout_handling(self):
       # Simulates connection timeouts
   
   async def test_ssl_certificate_error(self):
       # Tests SSL validation failures
   ```

2. **Malformed Data**
   ```python
   async def test_invalid_json_response(self):
       # Tests handling of corrupted JSON responses
   
   async def test_missing_required_fields(self):
       # Tests API responses with missing fields
   ```

3. **Boundary Values**
   ```python
   async def test_zero_page_size_request(self):
       # Tests edge case pagination parameters
   
   def test_cache_zero_ttl(self):
       # Tests cache with zero time-to-live
   ```

## Performance Benchmarks

### Expected Performance Metrics

- **Unit Tests**: < 10 seconds total
- **Integration Tests**: < 30 seconds per category
- **API Response Time**: < 2 seconds for typical queries
- **Cache Hit Ratio**: > 80% under high locality patterns
- **Concurrent Requests**: Handle 20+ parallel requests
- **Memory Usage**: < 500MB growth under sustained load

### Benchmark Commands

```bash
# Run performance benchmarks
pytest tests/performance/ --benchmark-only --benchmark-sort=mean

# Generate benchmark comparison
pytest tests/performance/ --benchmark-compare=last --benchmark-sort=mean

# Save benchmark results
pytest tests/performance/ --benchmark-save=baseline

# Memory profiling
pytest tests/performance/test_concurrent_operations.py --profile

# Asyncio event loop profiling
pytest tests/performance/ --asyncio-mode=auto --profile
```

## CI/CD Configuration

### GitHub Secrets Required

- `API_KEY`: Simpler Grants API key for live tests

### Workflow Triggers

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:
    inputs:
      run_performance_tests:
        description: 'Run performance tests'
        type: boolean
        default: false
      run_live_api_tests:
        description: 'Run live API tests'
        type: boolean
        default: false
```

### Matrix Strategy Examples

```yaml
# Python matrix testing
strategy:
  fail-fast: false
  matrix:
    python-version: [3.9, 3.10, 3.11, 3.12]
    os: [ubuntu-latest, macos-latest, windows-latest]
    exclude:
      - python-version: 3.9
        os: windows-latest

# Node.js matrix testing
strategy:
  fail-fast: false
  matrix:
    node-version: [18, 20, 21]
    os: [ubuntu-latest, macos-latest]
```

## Docker Testing

### Container Build & Test

```bash
# Build Docker image
docker build -t grants-mcp:test .

# Run container tests
docker run -d --name grants-mcp-test -p 8080:8080 -e SIMPLER_GRANTS_API_KEY=test_key grants-mcp:test

# Health check
curl -f http://localhost:8080/health

# MCP protocol test
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

### Docker Compose Testing

```bash
# Start with Docker Compose
docker-compose up -d

# Run integration tests against container
python scripts/test_http_local.py

# View logs
docker logs grants-mcp-server
```

## Test Data & Fixtures

### Mock Data Generation

```python
# tests/conftest.py
@pytest.fixture
def sample_opportunity():
    """Generate realistic grant opportunity data."""
    return {
        "opportunity_id": 12345,
        "opportunity_title": "Advanced AI Research Initiative",
        "agency_name": "National Science Foundation",
        "summary": {
            "award_ceiling": 500000,
            "close_date": "2024-12-31",
            "summary_description": "Funding for AI research projects"
        }
    }
```

### API Response Snapshots

```python
@pytest.fixture
def api_snapshot_recorder():
    """Record real API responses for fixture generation."""
    class SnapshotRecorder:
        async def record(self, name: str, api_call):
            response = await api_call()
            self.snapshots[name] = {
                "timestamp": datetime.now().isoformat(),
                "response": response
            }
            return response
```

## Monitoring & Reporting

### Test Results Dashboard

The pipeline generates:
- **JUnit XML** reports for test results
- **Coverage reports** (HTML, XML, JSON)
- **Performance benchmarks** (JSON, charts)
- **Security scan results** (Bandit, Safety)

### Coverage Targets

- **Unit Tests**: > 90% line coverage
- **Integration Tests**: > 80% branch coverage
- **Overall Coverage**: > 85% combined coverage

### Performance Monitoring

```python
@pytest.fixture
def performance_tracker():
    """Track API call performance metrics."""
    class PerformanceTracker:
        async def track(self, operation: str, api_call):
            start = time.time()
            result = await api_call()
            duration = time.time() - start
            # Record metrics
            return result
```

## Troubleshooting

### Common Issues

1. **Rate Limiting**
   - Use `USE_REAL_API=false` for development
   - Implement delays between API calls
   - Monitor rate limit headers

2. **Timeout Errors**
   - Increase test timeout: `pytest --timeout=60`
   - Use async timeouts: `asyncio.wait_for()`

3. **Memory Issues**
   - Run tests with memory profiling
   - Clear caches between tests
   - Use `pytest --maxfail=1` to stop early

4. **Docker Issues**
   ```bash
   # Check container logs
   docker logs grants-mcp-server
   
   # Rebuild without cache
   docker build --no-cache -t grants-mcp:test .
   
   # Check port conflicts
   lsof -i :8080
   ```

### Debug Commands

```bash
# Run with verbose output
pytest -vvv -s tests/

# Run single test with debugging
pytest --pdb tests/unit/test_cache_manager.py::TestInMemoryCache::test_cache_stores_and_retrieves_data

# Profile memory usage
pytest --profile-svg tests/performance/

# Generate test coverage report
pytest --cov=src --cov-report=html && open htmlcov/index.html
```

## Advanced Testing Strategies

### Property-Based Testing

```python
# Using hypothesis for property-based testing
from hypothesis import given, strategies as st

@given(st.text(min_size=1), st.integers(min_value=1, max_value=100))
def test_search_query_properties(query, page_size):
    # Test that any valid query and page size work
    assert isinstance(query, str)
    assert page_size > 0
```

### Mutation Testing

```bash
# Install mutmut for mutation testing
pip install mutmut

# Run mutation tests
mutmut run --paths-to-mutate src/

# View mutation test results
mutmut results
```

### Load Testing with Locust

```python
# tests/performance/locust_load_test.py
from locust import HttpUser, task, between

class GrantsAPIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def search_grants(self):
        self.client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": "search-grants",
                "arguments": {"query": "artificial intelligence"}
            }
        })
```

## Integration with Development Workflow

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest tests/unit/
        language: system
        pass_filenames: false
        
      - id: typescript-test
        name: typescript-test
        entry: npm test
        language: system
        pass_filenames: false
```

### VS Code Integration

```json
// .vscode/settings.json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/", "-v"],
    "python.testing.unittestEnabled": false,
    "typescript.preferences.includePackageJsonAutoImports": "on"
}
```

This comprehensive testing infrastructure ensures high code quality, reliability, and performance for the Grants MCP server across all supported platforms and use cases.