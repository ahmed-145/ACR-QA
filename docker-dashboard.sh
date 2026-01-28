#!/bin/bash
# Quick script to start ACR-QA dashboard in Docker
# Usage: ./docker-dashboard.sh

set -e

echo "🐳 Starting ACR-QA Dashboard in Docker..."
echo "📊 Dashboard will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start all services
docker-compose up postgres app
