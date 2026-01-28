# ACR-QA v2.0 - Automated Code Review Platform

**Intelligent, Context-Aware Code Quality Analysis with AI-Powered Explanations**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-15+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Project Overview

ACR-QA is a language-agnostic code review platform that automatically detects issues, assigns intelligent severity levels, and provides AI-generated explanations grounded in rule definitions.

**Key Features:**
- 🔍 Multi-tool static analysis (Ruff, Semgrep, Vulture, Radon, jscpd, Bandit)
- 🧠 RAG-enhanced AI explanations (Cerebras Llama 3.1)
- 📊 Context-aware severity scoring (HIGH/MEDIUM/LOW)
- 🚀 GitHub + GitLab CI/CD integration
- 💾 Complete provenance tracking
- 📈 Beautiful web dashboard
- 🔒 OWASP/SANS compliance reporting
- 💰 Zero recurring costs (free tier APIs)

---

## 🎓 Thesis Evaluation Criteria

This section maps ACR-QA's design to academic research questions and evaluation metrics.

### Research Questions Addressed

| Research Question | ACR-QA Implementation | Evaluation Method |
|-------------------|----------------------|-------------------|
| **RQ1: Can RAG reduce LLM hallucination?** | Rules.yml knowledge base + evidence-grounded prompts | `cites_rule` field tracks citation accuracy |
| **RQ2: How to ensure provenance?** | PostgreSQL audit trail with full metadata | `llm_explanations` table stores all context |
| **RQ3: What confidence scoring works?** | 0.6-0.9 based on rule citation presence | Compare with ground truth labels |
| **RQ4: Does it match industry tools?** | 6 tools vs CodeRabbit/SonarQube | Feature parity comparison |

### Academic Metrics Implemented

#### 1. Hallucination Grounding
- **Metric**: `cites_rule` boolean (does explanation cite the canonical rule?)
- **Implementation**: String matching in `explainer.py`
- **Baseline**: 90% citation rate (high confidence = 0.9)

#### 2. Provenance Tracking
- **Metric**: Complete audit trail from detection → explanation → user feedback
- **Implementation**: `llm_explanations` table with:
  - `prompt_filled`: Full RAG prompt sent to LLM
  - `response_text`: Raw LLM output
  - `model_name`, `temperature`, `tokens_used`: Reproducibility metadata
  - `latency_ms`, `cost_usd`: Performance tracking
- **Evaluation**: `export_provenance.py` generates full trace

#### 3. Confidence Scoring
- **Metric**: 0.0-1.0 confidence based on grounding quality
- **Implementation**:
  - High (0.9): Explanation cites canonical rule ID
  - Medium (0.6): Explanation generated but no citation
- **Evaluation**: Compare with `ground_truth` labels in Phase 2

#### 4. Industry Feature Parity

| Feature | CodeRabbit | SonarQube | ACR-QA | Status |
|---------|------------|-----------|--------|--------|
| Multi-tool Analysis | 3-4 | 35+ langs | 6 tools | ✅ |
| AI Explanations | ✅ | AI CodeFix | RAG | ✅ |
| Source Citations | ✅ | ✅ | `[RULE-ID](rules.yml)` | ✅ |
| Autofix Suggestions | ✅ | ✅ | Code examples | ✅ |
| Response Caching | ✅ | ✅ | Redis 7-day | ✅ |
| GitHub CI/CD | ✅ | ✅ | ✅ | ✅ |
| GitLab CI/CD | ✅ | ✅ | ✅ | ✅ |
| Compliance (OWASP) | ⚠️ | ✅ | ✅ | ✅ |

### Evaluation Commands

```bash
# 1. Run analysis with provenance tracking
python3 CORE/main.py --target-dir myproject --limit 10

# 2. Export full provenance data
python3 scripts/export_provenance.py <RUN_ID>

# 3. Compute accuracy metrics (requires ground truth labels)
python3 scripts/compute_metrics.py --run-id <RUN_ID>

# 4. Generate compliance report
python3 scripts/compliance_report.py --run-id <RUN_ID>
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Node.js 18+ (for jscpd)

### Installation
```bash
# 1. Clone repository
git clone https://github.com/yourusername/acr-qa.git
cd acr-qa

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install analysis tools
pip install ruff semgrep vulture radon bandit
npm install -g jscpd

# 4. Set up database
createdb acrqa
psql -d acrqa -f DATABASE/schema.sql

# 5. Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Run Analysis
```bash
# Analyze a directory
python3 CORE/main.py --target-dir /path/to/code --limit 50

# Start dashboard
python3 FRONTEND/app.py
# Open http://localhost:5000

# Export provenance
python3 scripts/export_provenance.py 28

# Generate report
python3 scripts/generate_report.py 28
```

---

## 📁 Project Structure
```
acr-qa/
├── CORE/
│   ├── engines/
│   │   ├── severity_scorer.py    # Intelligent severity logic
│   │   ├── normalizer.py         # Canonical schema mapper
│   │   └── explainer.py          # RAG + LLM integration
│   ├── utils/
│   │   └── code_extractor.py    # Code snippet extraction
│   └── main.py                   # Analysis pipeline
├── DATABASE/
│   ├── schema.sql                # PostgreSQL schema
│   └── database.py               # Database interface
├── FRONTEND/
│   ├── app.py                    # Flask dashboard
│   └── templates/
│       └── index.html            # Modern UI
├── scripts/
│   ├── post_pr_comments.py      # GitHub PR integration
│   ├── generate_report.py       # Markdown reports
│   └── export_provenance.py     # Full audit trail
├── TESTS/
│   └── samples/
│       └── comprehensive-issues/ # Test files (6 files)
├── TOOLS/
│   ├── run_checks.sh            # Tool orchestration
│   └── semgrep/
│       └── python-rules.yml     # Custom Semgrep rules
├── .github/
│   └── workflows/
│       └── acr-qa.yml           # GitHub Action
└── config/
    └── rules.yml                 # Rule definitions (RAG knowledge base)
```

---

## 🔧 Architecture

### 1. Analysis Pipeline
```
GitHub PR → Detection Tools → Normalizer → Severity Scorer → LLM Explainer → Database → PR Comments
```

### 2. Severity Scoring
```python
HIGH:   Security vulnerabilities, crashes (eval, SQL injection)
MEDIUM: Design issues, complexity (CC>10, too many params)
LOW:    Style violations, unused code (imports, variables)
```

### 3. RAG Explanation Engine
```
1. Retrieve rule definition from rules.yml
2. Extract code context (3 lines before/after)
3. Construct evidence-grounded prompt
4. Call Cerebras API (Llama 3.1 8B)
5. Validate response cites rule ID
6. Store with provenance
```

---

## 🎨 GitHub Action Usage

### Auto-Trigger on PRs
```yaml
# .github/workflows/acr-qa.yml is pre-configured
# Just add CEREBRAS_API_KEY secret to your repo
```

### Manual Trigger

Comment on any PR:
```
acr-qa review
```

The action will analyze changed files and post comments sorted by severity.

---

## 📊 Dashboard Features

Access at `http://localhost:5000`:

- ✅ Real-time statistics (HIGH/MEDIUM/LOW counts)
- ✅ Severity filtering
- ✅ Category filtering
- ✅ Full-text search
- ✅ Collapsible AI explanations
- ✅ Export provenance data
- ✅ Beautiful modern UI

---

## 🧪 Testing
```bash
# Run comprehensive test suite
python3 CORE/main.py --target-dir TESTS/samples/comprehensive-issues --limit 56

# Expected: 56 findings
#   HIGH: 1-2 (security issues)
#   MEDIUM: 4-6 (design smells)
#   LOW: 50+ (style, unused code)

# Verify severity scorer
python3 CORE/engines/severity_scorer.py
# Expected: 6/6 tests passed
```

---

## 📈 Metrics & Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Severity Accuracy | 90% | ✅ 100% (6/6 tests) |
| Analysis Time | <120s | ✅ ~90s |
| AI Latency | <1s | ✅ 400-600ms |
| Cost per Analysis | <$0.05 | ✅ $0.025 |
| False Positive Rate | <30% | 🔄 TBD (Phase 2) |

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11 | Core implementation |
| Database | PostgreSQL 15 | Provenance storage |
| AI Model | Cerebras Llama 3.1 8B | Natural language explanations |
| Static Analysis | Ruff, Semgrep, Vulture, Radon | Multi-tool detection |
| Web Framework | Flask + Tailwind CSS | Dashboard UI |
| VCS Integration | GitHub Actions + PyGithub | PR automation |

---

## 📚 Documentation

- [Architecture Details](docs/DOCS/ARCHITECTURE.md)
- [Canonical Schema](docs/DOCS/CANONICAL_SCHEMA.md)
- [API Reference](docs/DOCS/API.md)
- [PRD](docs/prd.pdf)
- [Assignment 1](docs/assigment1_merged.pdf)
- [Assignment 2](docs/assigment2_merged.pdf)

---

## 🎓 Academic Context

**Student:** Ahmed Mahmoud Abbas (ID: 222101213)  
**Supervisor:** Dr. Samy AbdelNabi  
**Institution:** King Salman International University (KSIU)  
**Timeline:** October 2025 - June 2026  
**Status:** Phase 1 Complete (✅ Ahead of Schedule)

---

## 🚧 Roadmap

### Phase 1 (✅ COMPLETE - Jan 2, 2026)
- [x] Python adapter with 5 detection categories
- [x] Intelligent severity scoring
- [x] RAG-enhanced AI explanations
- [x] GitHub Action integration
- [x] Web dashboard
- [x] Provenance tracking

### Phase 2 (Feb-Jun 2026)
- [ ] JavaScript/TypeScript adapter
- [ ] User study (8-10 participants)
- [ ] Precision/recall evaluation
- [ ] Production deployment
- [ ] Performance optimization

---

## 🤝 Contributing

This is an academic project. Contributions welcome after June 2026 graduation.

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- Dr. Samy AbdelNabi (Supervisor)
- Cerebras AI (Free API tier)
- CustomGPT (RAG architecture guidance)
- IEEE (Multi-language static analysis patterns)

---

**⭐ Star this repo if you find it useful!**

Built with ❤️ at King Salman International University
