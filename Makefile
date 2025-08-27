.PHONY: help install test test-unit test-integration test-live run clean

help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies"
	@echo "  make test          - Run all tests (mocked)"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests (mocked)"
	@echo "  make test-live     - Run live API tests (requires API key)"
	@echo "  make run           - Run the MCP server"
	@echo "  make clean         - Clean cache and temporary files"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	pytest tests/unit tests/integration -v

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

test-live:
	USE_REAL_API=true pytest tests/live -m real_api -v

test-coverage:
	pytest tests/unit tests/integration --cov=src --cov-report=html --cov-report=term

run:
	python main.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage