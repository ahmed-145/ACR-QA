# Use official Python slim image (smaller, faster)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - postgresql-client: for psql commands
# - gcc, python3-dev: for psycopg2 compilation
# - nodejs, npm: for jscpd (duplication detection)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    nodejs \
    npm \
    curl \
    git \
    && npm install -g jscpd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Python analysis tools
RUN pip install --no-cache-dir ruff semgrep vulture radon bandit

# Create non-root user for security
RUN groupadd -r acrqa && useradd -r -g acrqa -d /app -s /sbin/nologin acrqa

# Copy application code
COPY . .

# Create output directories with correct structure
RUN mkdir -p DATA/outputs DATA/provenance DATA/reports \
    && chown -R acrqa:acrqa /app

# Make scripts executable
RUN chmod +x TOOLS/*.sh scripts/*.py 2>/dev/null || true

# Switch to non-root user
USER acrqa

# Expose port for Flask API
EXPOSE 5000

# Health check — verifies Flask API is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["python3", "FRONTEND/app.py"]