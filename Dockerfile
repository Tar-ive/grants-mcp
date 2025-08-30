# Use Python 3.11 for better compatibility
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY main.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http \
    PORT=8080 \
    LOG_LEVEL=INFO

# Expose port
EXPOSE 8080

# Health check - send proper headers for SSE endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f -H "Accept: application/json, text/event-stream" http://localhost:8080/mcp || exit 1

# Run the server
CMD ["python", "main.py"]