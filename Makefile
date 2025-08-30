# Makefile for Grants MCP Server - Comprehensive Testing

PYTHON := python3
NPM := npm
PYTEST := pytest
DOCKER := docker

.PHONY: help install install-dev test test-all test-unit test-integration test-live
.PHONY: test-performance test-contract test-edge-cases test-typescript docker-test
.PHONY: test-parallel test-coverage lint security clean run

help:
	@echo "Grants MCP Server - Comprehensive Testing Commands"
	@echo "=================================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  clean           Clean temporary files and caches"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test            Run basic test suite (unit + integration)"
	@echo "  test-all        Run complete test suite"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-contract   Run API contract tests"
	@echo "  test-edge-cases Run edge case and error handling tests"
	@echo "  test-performance Run performance and benchmark tests"
	@echo "  test-live       Run live API tests (requires API_KEY)"
	@echo "  test-typescript Run TypeScript/Node.js tests"
	@echo "  test-parallel   Run tests with parallel execution"
	@echo "  test-coverage   Run tests with comprehensive coverage"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-test     Test Docker deployment"
	@echo ""
	@echo "Quality Commands:"
	@echo "  lint            Run code linting"
	@echo "  security        Run security scans"
	@echo ""
	@echo "Examples:"
	@echo "  make test                    # Quick test suite"
	@echo "  make test-live API_KEY=xxx   # Live API tests with key"
	@echo "  make test-coverage           # Tests with coverage report"

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(NPM) ci

install-dev: install
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(NPM) install --include=dev

# Basic testing
test: test-unit test-integration
	@echo "✅ Basic test suite completed"

test-unit:
	@echo "🧪 Running unit tests..."
	$(PYTEST) -v -m "unit" tests/unit/

test-integration:
	@echo "🔗 Running integration tests..."
	$(PYTEST) -v -m "integration" tests/integration/

test-contract:
	@echo "📋 Running contract tests..."
	$(PYTEST) -v -m "contract" tests/contract/

test-edge-cases:
	@echo "🔍 Running edge case tests..."
	$(PYTEST) -v -m "edge_case" tests/edge_cases/

test-performance:
	@echo "⚡ Running performance tests..."
	$(PYTEST) -v -m "performance" --benchmark-only tests/performance/

test-live:
	@echo "🌐 Running live API tests..."
	@if [ -z "$(API_KEY)" ]; then \
		echo "❌ API_KEY environment variable is required for live tests"; \
		echo "Usage: make test-live API_KEY=your_api_key_here"; \
		exit 1; \
	fi
	USE_REAL_API=true API_KEY=$(API_KEY) $(PYTEST) -v -m "real_api" tests/live/

test-typescript:
	@echo "📘 Running TypeScript tests..."
	$(NPM) run build
	$(NPM) test

test-parallel:
	@echo "⚡ Running tests in parallel..."
	$(PYTEST) -v -n auto tests/unit/ tests/integration/ tests/contract/

test-coverage:
	@echo "📊 Running tests with coverage..."
	$(PYTEST) -v --cov=src --cov-branch --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml:coverage.xml tests/unit/ tests/integration/ tests/contract/
	@echo "📊 Coverage report generated in htmlcov/index.html"

test-all:
	@echo "🚀 Running complete test suite..."
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(MAKE) test-contract
	$(MAKE) test-edge-cases
	$(MAKE) test-typescript
	@echo "✅ Complete test suite finished"

# Docker commands
docker-test:
	@echo "🐳 Testing Docker deployment..."
	$(DOCKER) build -t grants-mcp:test .
	$(DOCKER) run -d --name grants-mcp-test -p 8080:8080 -e SIMPLER_GRANTS_API_KEY=test_key grants-mcp:test
	@echo "Waiting for container to start..."
	sleep 10
	@echo "Testing health endpoint..."
	curl -f http://localhost:8080/health || ($(DOCKER) stop grants-mcp-test && $(DOCKER) rm grants-mcp-test && exit 1)
	@echo "Testing MCP endpoint..."
	curl -X POST http://localhost:8080/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' || ($(DOCKER) stop grants-mcp-test && $(DOCKER) rm grants-mcp-test && exit 1)
	@echo "Cleaning up..."
	$(DOCKER) stop grants-mcp-test && $(DOCKER) rm grants-mcp-test
	@echo "✅ Docker tests passed"

# Quality commands
lint:
	@echo "🔍 Running linting..."
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503 || true
	mypy src/ --ignore-missing-imports || true
	$(NPM) run build

security:
	@echo "🔒 Running security scans..."
	bandit -r src/ -f json -o security-report.json || true
	safety check --json --output security-deps.json || true
	@echo "🔒 Security reports generated: security-report.json, security-deps.json"

# Development commands
run:
	$(PYTHON) main.py

clean:
	@echo "🧹 Cleaning temporary files..."
	rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov coverage.xml
	rm -rf build/ dist/ *.egg-info/
	rm -rf node_modules/.cache coverage-typescript/
	rm -rf test-results/ junit*.xml security-*.json
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	$(DOCKER) system prune -f 2>/dev/null || true