# ACR-QA Live Demo — Command Cheat Sheet

Keep this file open on a second monitor during the presentation.

---

## Before the Meeting (10 min early)
```bash
cd ~/Documents/KSIU/GRAD/SOLO
source .venv/bin/activate
docker compose up -d
python3 FRONTEND/app.py
```
Then open `http://localhost:5000` in your browser.

---

## Demo Commands (Run These In Order)

### Command 1: Run All 273 Tests
```bash
make test-all
```
*Expected: 273 passed, 4 skipped in ~6 seconds*

### Command 2: AST Test Gap Analyzer
```bash
python3 scripts/test_gap_analyzer.py --target CORE/ --format text
```
*Expected: 103 symbols, 40 untested, 61.2% coverage, red priority list at bottom*

### Command 3: AI Security Engine (Rich Output)
```bash
python3 CORE/main.py --target-dir TESTS/samples --rich --limit 5
```
*Expected: Beautiful colored table + Quality Gate ❌ FAILED panel*

---

## Browser Tabs to Have Open
1. `http://localhost:5000` — Flask Dashboard
2. `https://github.com/ahmed-145/ACR-QA/releases/tag/v2.7.0` — Release Page
3. `https://github.com/ahmed-145/ACR-QA/actions` — CI/CD Actions
