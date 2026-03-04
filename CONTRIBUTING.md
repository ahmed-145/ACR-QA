# Contributing to ACR-QA

Thank you for your interest in contributing to ACR-QA! This document explains how to set up your development environment and submit changes.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/ahmed-145/ACR-QA.git
cd ACR-QA

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 5. Initialize database (requires PostgreSQL)
make init-db

# 6. Generate default config
make init-config

# 7. Run tests
pytest TESTS/ -v
```

## Project Structure

```
CORE/           → Engine logic (normalizer, explainer, quality gate, etc.)
CORE/adapters/  → Language adapters (Python, JS placeholder)
DATABASE/       → PostgreSQL schema and ORM
FRONTEND/       → Flask dashboard (20 endpoints)
TESTS/          → pytest suite (97 tests)
TOOLS/          → Shell scripts for running analysis tools
scripts/        → CI/CD and utility scripts
config/         → Prometheus, Grafana, and rule definitions
docs/           → Architecture docs, setup guides, thesis docs
```

## Development Workflow

1. **Create a branch** from `main`
2. **Make your changes** following the existing patterns
3. **Add tests** for new functionality in `TESTS/`
4. **Run the test suite** — all 97 tests must pass:
   ```bash
   pytest TESTS/ -v --override-ini="addopts="
   ```
5. **Run the pipeline** to verify integration:
   ```bash
   python3 CORE/main.py --target-dir TESTS/samples/comprehensive-issues --limit 3
   ```
6. **Submit a PR** — the ACR-QA GitHub Action will automatically analyze your code

## Adding a New Language Adapter

To add support for a new language (e.g., JavaScript, Java):

1. Create `CORE/adapters/<language>_adapter.py`
2. Implement the `LanguageAdapter` interface from `CORE/adapters/base.py`
3. Add tool runner script in `TOOLS/run_<language>_checks.sh`
4. Add rule mappings to `CORE/engines/normalizer.py`
5. Add rule definitions to `config/rules.yml`
6. Add tests in `TESTS/test_<language>_adapter.py`
7. Add test samples in `TESTS/samples/<language>-issues/`

See `CORE/adapters/python_adapter.py` for a reference implementation.

## Adding New Rules

1. Define the rule in `config/rules.yml` with: name, category, severity, description, rationale, remediation, examples
2. Add the rule mapping in `CORE/engines/normalizer.py` → `RULE_MAPPING` dict
3. Ensure the underlying tool (Ruff, Semgrep, etc.) detects it

## Code Style

- Python 3.11+
- Use type hints where practical
- Follow existing patterns in the codebase
- Run `ruff format` before committing

## Configuration

Per-repo configuration is via `.acrqa.yml`. See the generated default for all options:
```bash
make init-config
```

## Inline Suppression

Suppress specific findings with inline comments:
```python
password = "admin123"  # acr-qa:ignore
eval(user_input)       # acrqa:disable SECURITY-001
```

## Questions?

Open an [issue on GitHub](https://github.com/ahmed-145/ACR-QA/issues).
