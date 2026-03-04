# ACR-QA Documentation Index

## 📐 Architecture

| Document | Description |
|----------|-------------|
| [Architecture](architecture/ARCHITECTURE.md) | Pipeline stages, component design, database schema, security |
| [Canonical Schema](architecture/CANONICAL_SCHEMA.md) | Universal finding data model with field reference |
| [Internal API](architecture/API.md) | Python class/function API reference for all components |

## 🔧 Setup

| Document | Description |
|----------|-------------|
| [REST API](setup/API-Documentation.md) | All 11 HTTP endpoints with request/response examples |
| [Cloud Deployment](setup/Cloud-Deployment.md) | PythonAnywhere, Replit, ngrok deployment guides |
| [Token Setup](setup/TOKEN_SETUP.md) | GitHub, GitLab, and Cerebras API key configuration |

## 🎓 Thesis

| Document | Description |
|----------|-------------|
| [Phase 1 Extras](thesis/Phase1-extras.md) | Additional Phase 1 implementation details |

## 📁 Project Root Docs

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, features, quick start |
| [CHANGELOG](../CHANGELOG.md) | Version history and release notes |
| [CONTRIBUTING](../CONTRIBUTING.md) | Development setup and contribution guidelines |
| [SECURITY](../SECURITY.md) | Security policy and vulnerability reporting |
| [PERFORMANCE_BASELINE](../PERFORMANCE_BASELINE.md) | Pipeline timing benchmarks |

## 📊 Generated Documentation

During analysis runs, ACR-QA generates:
- **Reports:** `DATA/outputs/report_run_*.md`
- **Provenance:** `DATA/outputs/provenance/`
- **SARIF:** `DATA/outputs/*.sarif`
- **Compliance:** Via `scripts/compliance_report.py`

---

**Last Updated:** March 4, 2026 · **Version:** 2.5.0
