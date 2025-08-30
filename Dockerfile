# Multi-stage build for Cloud Run optimization
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy source code
COPY src/ ./src/
COPY main.py .
COPY simple_test_server.py .
COPY minimal_mcp_test.py .
COPY import_test.py .
COPY mcp_server_fixed.py .

# Set environment variables optimized for Cloud Run
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_TRANSPORT=http \
    LOG_LEVEL=INFO \
    PATH=/home/appuser/.local/bin:$PATH

# Change ownership of app directory
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check with proper headers for MCP endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f -H "Accept: application/json, text/event-stream" http://localhost:8080/health || exit 1

# Run the working test server (confirmed working)
CMD ["python", "simple_test_server.py"]