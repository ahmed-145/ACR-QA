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

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x scripts/*.sh scripts/*.py

# Create outputs directory
RUN mkdir -p outputs outputs/provenance

# Expose port for Flask API (optional)
EXPOSE 5000

# Default command (can be overridden in docker-compose)
CMD ["python3", "FRONTEND/app.py"]