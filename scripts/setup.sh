#!/bin/bash
# ACR-QA v2.0 - Quick Setup Script
# Sets up database and runs first analysis

set -e

echo "🚀 ACR-QA v2.0 Setup"
echo "===================="

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "❌ Python 3.11+ required"; exit 1; }

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if PostgreSQL is running
echo ""
echo "🔍 Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL client found"
else
    echo "⚠️  PostgreSQL client not found (optional for local setup)"
fi

# Setup database (Docker)
echo ""
echo "🐳 Starting PostgreSQL with Docker..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d postgres
    echo "✓ PostgreSQL started"
    
    # Wait for DB to be ready
    echo "Waiting for database to be ready..."
    sleep 5
    
    # Initialize schema
    echo "Initializing database schema..."
    docker-compose exec -T postgres psql -U postgres -d acrqa < db/schema.sql
    echo "✓ Database initialized"
else
    echo "⚠️  Docker Compose not found - using existing PostgreSQL"
    
    # Try direct psql
    if command -v psql &> /dev/null; then
        export PGPASSWORD=postgres
        psql -U postgres -d acrqa -f db/schema.sql 2>/dev/null || {
            echo "Creating database..."
            psql -U postgres -c "CREATE DATABASE acrqa;"
            psql -U postgres -d acrqa -f db/schema.sql
        }
        echo "✓ Database initialized"
    fi
fi

# Create .env if missing
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Add your CEREBRAS_API_KEY to .env file"
    echo "   Get your key at: https://cloud.cerebras.ai/"
fi

# Check Cerebras API key
echo ""
source .env 2>/dev/null || true
if [ -z "$CEREBRAS_API_KEY" ]; then
    echo "⚠️  CEREBRAS_API_KEY not set in .env"
    echo "   The system will use template fallbacks without API key"
else
    echo "✓ Cerebras API key found"
fi

# Test installation
echo ""
echo "🧪 Testing installation..."
python3 -c "from db.database import Database; from engines.explainer import ExplanationEngine; print('✓ All imports successful')"

echo ""
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Add CEREBRAS_API_KEY to .env (if not done)"
echo "  2. Run analysis: python3 main.py --limit 5"
echo "  3. View dashboard: python3 scripts/dashboard.py"
echo "  4. Generate report: python3 scripts/generate_report.py"
echo ""