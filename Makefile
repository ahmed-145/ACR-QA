# ACR-QA v2.5 - Makefile
# One-click setup and common operations

.PHONY: help up down setup install-deps install-tools init-db docker-up docker-down run dashboard test test-all lint coverage version clean

# Default target
help:
	@echo "ACR-QA v2.5 - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make up             - Start EVERYTHING (DB + Redis + App + Prometheus + Grafana)"
	@echo "  make down           - Stop everything"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Complete setup (deps + tools + DB)"
	@echo "  make install-deps   - Install Python dependencies"
	@echo "  make install-tools  - Install analysis tools (ruff, semgrep, etc.)"
	@echo "  make init-db        - Initialize PostgreSQL database"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make docker-up      - Start Docker Compose stack"
	@echo "  make docker-down    - Stop Docker Compose stack"
	@echo "  make docker-logs    - View Docker logs"
	@echo "  make docker-restart - Restart Docker stack"
	@echo ""
	@echo "Running Analysis:"
	@echo "  make run            - Run analysis on test samples"
	@echo "  make run-full       - Run full analysis (no limit)"
	@echo "  make dashboard      - Start Flask dashboard"
	@echo ""
	@echo "Testing:"
	@echo "  make test-all       - Run FULL pytest suite (97 tests)"
	@echo "  make test           - Run acceptance tests only"
	@echo "  make test-pydantic  - Test Pydantic validation"
	@echo "  make test-rate      - Test rate limiting"
	@echo "  make test-e2e       - End-to-end integration test"
	@echo "  make lint           - Run Ruff linter + formatter check"
	@echo "  make coverage       - Run tests with coverage report"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Remove outputs and cache"
	@echo "  make reset-redis    - Reset Redis rate limits"
	@echo ""

# ============================================
# Setup & Installation
# ============================================

setup: install-deps install-tools init-db init-config
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. cp .env.example .env   # add your API keys"
	@echo "  2. Run: make up"
	@echo "  3. Run: make run"
	@echo ""

install-deps:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

install-tools:
	@echo "🔧 Installing analysis tools..."
	pip install ruff semgrep vulture radon bandit
	npm install -g jscpd || echo "⚠️  jscpd requires Node.js (optional)"
	@echo "✓ Tools installed"

init-db:
	@echo "🗄️  Initializing PostgreSQL database..."
	@if command -v psql > /dev/null; then \
		createdb acrqa || echo "Database may already exist"; \
		psql -d acrqa -f DATABASE/schema.sql; \
		echo "✓ Database initialized"; \
	else \
		echo "⚠️  PostgreSQL not found. Use Docker instead: make docker-up"; \
	fi

init-config:
	@echo "📋 Generating default .acrqa.yml config..."
	@if [ ! -f .acrqa.yml ]; then \
		.venv/bin/python3 CORE/config_loader.py --generate .acrqa.yml; \
	else \
		echo "   .acrqa.yml already exists, skipping"; \
	fi

# ============================================
# Docker Operations
# ============================================

# ─── Primary one-command startup ───────────────────────────────────────────
up:
	@echo "🚀 Starting ACR-QA full stack..."
	docker-compose up -d
	@echo ""
	@echo "✅ All services started!"
	@echo ""
	@echo "  📊 Dashboard:   http://localhost:5000"
	@echo "  📈 Grafana:     http://localhost:3000  (admin / admin)"
	@echo "  🔥 Prometheus:  http://localhost:9090"
	@echo "  🗄️  PostgreSQL:  localhost:5433"
	@echo "  🔴 Redis:       localhost:6379"
	@echo ""
	@echo "Run analysis: make run"
	@echo "Stop stack:   make down"
	@echo ""

down:
	@echo "🛑 Stopping ACR-QA stack..."
	docker-compose down
	@echo "✓ All services stopped"

docker-up:
	@echo "🐳 Starting Docker Compose stack..."
	docker-compose up -d
	@echo ""
	@echo "✅ Docker stack started!"
	@echo ""
	@echo "Services:"
	@echo "  - PostgreSQL: localhost:5433"
	@echo "  - Redis: localhost:6379"
	@echo "  - Dashboard: http://localhost:5000"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000"
	@echo ""
	@echo "View logs: make docker-logs"
	@echo ""

docker-down:
	@echo "🛑 Stopping Docker Compose stack..."
	docker-compose down
	@echo "✓ Docker stack stopped"

docker-logs:
	docker-compose logs -f

docker-restart: docker-down docker-up

# ============================================
# Running Analysis
# ============================================

run:
	@echo "🚀 Running analysis on test samples..."
	python3 CORE/main.py \
		--target-dir TESTS/samples/comprehensive-issues \
		--repo-name test-repo \
		--limit 10
	@echo ""
	@echo "✅ Analysis complete!"
	@echo "View results: make dashboard"

run-full:
	@echo "🚀 Running FULL analysis (no limit)..."
	python3 CORE/main.py \
		--target-dir TESTS/samples/comprehensive-issues \
		--repo-name test-repo \
		--limit 100

dashboard:
	@echo "📊 Starting Flask dashboard..."
	@echo "Dashboard will be available at: http://localhost:5000"
	@echo ""
	python3 FRONTEND/app.py

# ============================================
# Testing
# ============================================

test-all:
	@echo "🧪 Running FULL test suite (97 tests)..."
	.venv/bin/pytest TESTS/ -v --tb=short --override-ini="addopts=" 2>&1
	@echo ""
	@echo "✅ Full suite complete!"

test:
	@echo "🧪 Running acceptance tests..."
	.venv/bin/pytest TESTS/test_acceptance.py TESTS/test_pydantic_validation.py TESTS/test_rate_limiting.py -v --override-ini="addopts="
	@echo ""
	@echo "✅ Acceptance tests passed!"

test-pydantic:
	@echo "🧪 Testing Pydantic validation..."
	pytest TESTS/test_pydantic_validation.py -v

test-rate:
	@echo "🧪 Testing rate limiting..."
	pytest TESTS/test_rate_limiting.py -v

test-e2e:
	@echo "🧪 Running end-to-end integration test..."
	@echo ""
	@echo "Step 1: Starting Docker stack..."
	make docker-up
	@echo ""
	@echo "Step 2: Waiting for services to be ready..."
	sleep 10
	@echo ""
	@echo "Step 3: Running analysis..."
	make run
	@echo ""
	@echo "Step 4: Verifying results..."
	@if [ -f DATA/outputs/findings.json ]; then \
		echo "✓ Findings generated"; \
	else \
		echo "✗ No findings found"; \
		exit 1; \
	fi
	@echo ""
	@echo "✅ End-to-end test passed!"

# ============================================
# Utilities
# ============================================

clean:
	@echo "🧹 Cleaning outputs and cache..."
	rm -rf DATA/outputs/*.json
	rm -rf DATA/outputs/*.txt
	rm -rf __pycache__
	rm -rf CORE/__pycache__
	rm -rf CORE/engines/__pycache__
	rm -rf CORE/utils/__pycache__
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	@echo "✓ Cleaned"

reset-redis:
	@echo "🔄 Resetting Redis rate limits..."
	@if command -v redis-cli > /dev/null; then \
		redis-cli FLUSHDB; \
		echo "✓ Redis flushed"; \
	else \
		docker exec acr-qa-redis redis-cli FLUSHDB; \
		echo "✓ Redis flushed (via Docker)"; \
	fi

lint:
	@echo "🔍 Running Ruff linter..."
	.venv/bin/ruff check CORE/ DATABASE/ scripts/ FRONTEND/ --fix
	.venv/bin/ruff format CORE/ DATABASE/ scripts/ FRONTEND/
	@echo "✅ Lint complete!"

coverage:
	@echo "📊 Running tests with coverage..."
	.venv/bin/pytest TESTS/ --override-ini="addopts=" --cov=CORE --cov=DATABASE --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "✅ Coverage report: open htmlcov/index.html"

version:
	@.venv/bin/python3 -c "from CORE import __version__; print(f'ACR-QA v{__version__}')"
