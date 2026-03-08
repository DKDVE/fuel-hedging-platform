FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy all requirement files to leverage Docker's layer caching
COPY requirements.txt requirements-core.txt requirements-analytics.txt ./

# Configure pip for better reliability with timeouts and retries
RUN pip install --upgrade pip && \
    pip config set global.timeout 300 && \
    pip config set global.retries 5 && \
    pip install --no-cache-dir -r requirements.txt \
        -r requirements-core.txt \
        -r requirements-analytics.txt

# Copy application code
COPY . .

# Create directories for models and data
RUN mkdir -p /models /data

# Copy and set entrypoint (runs migrations + seed before uvicorn)
COPY docker-entrypoint.sh /docker-entrypoint.sh
# Fix CRLF line endings (Windows) so exec works
RUN sed -i 's/\r$//' /docker-entrypoint.sh 2>/dev/null || true
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run migrations, seed, then start the application
# Use /bin/sh explicitly to avoid CRLF/shebang issues on Windows
ENTRYPOINT ["/bin/sh", "/docker-entrypoint.sh"]
