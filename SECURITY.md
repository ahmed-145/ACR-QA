# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 2.5.x   | ✅ Active          |
| < 2.5   | ❌ No longer supported |

## Reporting a Vulnerability

If you discover a security vulnerability in ACR-QA, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email: **222101213@ksiu.edu.eg** with subject: `[SECURITY] ACR-QA vulnerability`
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide an estimated timeline for resolution.

## Security Design Principles

ACR-QA follows these security practices:

- **On-premises first** — all data stays on your infrastructure
- **No telemetry** — zero data is sent to external services (except Cerebras API for AI explanations)
- **Secrets management** — API keys stored in `.env` (never committed)
- **Dependency pinning** — all dependencies pinned to exact versions in `requirements.txt`
- **Inline suppression audit** — suppressed findings are logged, not silently dropped
- **Input validation** — Pydantic schema validation on all canonical findings

## Known Security Considerations

- The Cerebras API receives code snippets for generating AI explanations. If this is a concern, configure `ai.enabled: false` in `.acrqa.yml`
- Redis is used without authentication by default. In production, enable Redis AUTH
- PostgreSQL credentials should be rotated regularly in production deployments
