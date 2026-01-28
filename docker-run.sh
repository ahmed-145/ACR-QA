#!/bin/bash
# Quick script to run ACR-QA analysis in Docker
# Usage: ./docker-run.sh [--target-dir DIR] [--limit N]

set -e

echo "🐳 Starting ACR-QA Analysis in Docker..."

# Start database if not running
docker-compose up -d postgres

# Wait for database to be healthy
echo "⏳ Waiting for database..."
sleep 5

# Run analysis
echo "🚀 Running analysis..."
docker-compose run --rm app python3 CORE/main.py "$@"

echo "✅ Analysis complete!"
echo "💡 View results: ./docker-dashboard.sh"
