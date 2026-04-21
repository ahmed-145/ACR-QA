# ACR-QA Documentation Index

## 📐 Architecture

| Document | Description |
|----------|-------------|
| [Architecture](architecture/ARCHITECTURE.md) | Pipeline stages, component design, database schema, security |
| [Canonical Schema](architecture/CANONICAL_SCHEMA.md) | Universal finding data model with field reference |
| [Internal API](architecture/API.md) | Python class/function API reference for all components |

## 🔧 Setup & Configuration

| Document | Description |
|----------|-------------|
| [REST API Reference](API_REFERENCE.md) | All 22 HTTP endpoints, CLI reference, JS fetch() integration example [v3.0] |
| [REST API (legacy)](setup/API-Documentation.md) | Original 11 HTTP endpoints reference (v2.7) |
| [Cloud Deployment](setup/Cloud-Deployment.md) | PythonAnywhere, Replit, ngrok deployment guides |
| [Token Setup](setup/TOKEN_SETUP.md) | GitHub, GitLab, and Cerebras API key configuration |
| [Policy Engine](POLICY_ENGINE.md) | `.acrqa.yml` config reference — rules, thresholds, autofix, AI |

## 🧪 Testing & Quality

| Document | Description |
|----------|-------------|
| [Testing & Calibration](TESTING_AND_CALIBRATION.md) | Full test suite breakdown, code audit bugs, mass repo testing across 9 repos, god-mode end-to-end validation (v2.9), all calibration fixes |

## 📊 Evaluation

| Document | Description |
|----------|-------------|
| [Evaluation Report](evaluation/EVALUATION.md) | Precision/recall/F1, confusion matrix, DVPWA ground truth, comparative benchmarks, OWASP coverage, competitive analysis |
| [Per-Tool Evaluation](evaluation/PER_TOOL_EVALUATION.md) | Per-engine accuracy analysis: Bandit, Semgrep, Ruff, Vulture, Radon, jscpd across 4 vulnerable repos |
| [User Study](evaluation/USER_STUDY.md) | A/B comparison materials: raw tool output vs ACR-QA with AI explanations |
| [User Study Protocol](evaluation/USER_STUDY_PROTOCOL.md) | 20-minute structured user study protocol, 3 test scenarios, researcher script, data recording table |
| [User Study Survey](evaluation/USER_STUDY_SURVEY.md) | 15-question participant questionnaire for formal evaluation |

## 🎓 Presentation

| Document | Description |
|----------|-------------|
| [Presentation Script](PRESENTATION_SCRIPT.md) | 7-min presentation script, Q&A cheat sheet, demo commands (all in one) |
| [Demo Video Script](DEMO_VIDEO_SCRIPT.md) | 5-minute structured demo video script with timestamps and voiceover narration |
| [LaTeX Slides](acr_qa_presentation.tex) | Formal presentation slide source |
| [Phase 1 Extras](thesis/Phase1-extras.md) | Additional Phase 1 implementation details |

## 🗺️ Roadmap

| Document | Description |
|----------|-------------|
| [ROADMAP](ROADMAP.md) | Phase 1 (Python v3.0, complete), Phase 1B (JS adapter), Phase 2 (full TS rewrite — architecture, stack, implementation order) |

## 📁 Project Root Docs

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, features, quick start |
| [CHANGELOG](../CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING](../CONTRIBUTING.md) | Development setup and contribution guidelines |
| [SECURITY](../SECURITY.md) | Security policy and vulnerability reporting |
| [PERFORMANCE_BASELINE](PERFORMANCE_BASELINE.md) | Pipeline timing benchmarks |

## 📊 Generated Documentation

During analysis runs, ACR-QA generates:
- **Reports:** `DATA/outputs/report_run_*.md`
- **Provenance:** `DATA/outputs/provenance/`
- **SARIF:** `DATA/outputs/*.sarif`
- **Compliance:** Via `scripts/generate_compliance_report.py`

---

**Last Updated:** April 22, 2026 · **Version:** 3.1.2
