# ACR-QA Terms of Service

**Effective date:** 2026-05-19
**Service:** ACR-QA — Automated Code Review & Quality Analysis
**Operator:** Ahmed Mahmoud Abbas (KSIU thesis project)

---

## 1. Acceptance

By accessing acrqa.dev or using the ACR-QA API you agree to these terms. If you do not agree, do not use the service.

## 2. Free Tier Limits

The hosted service is provided free of charge during the thesis evaluation period. Limits:

| Resource | Limit |
|----------|-------|
| Groq AI token calls | 100,000 tokens / user / day |
| Scan history | 90 days retention (unpinned) |
| API keys | 10 per user |
| Concurrent scans | 2 per user |

Limits may change with 7 days notice. Exceeding quotas returns HTTP 429.

## 3. Acceptable Use

You may **not** use ACR-QA to:

- Scan repositories you do not own or have explicit written permission to test.
- Attempt to extract, reverse-engineer, or exfiltrate other users' scan data.
- Deliberately submit code designed to exhaust shared AI token quotas.
- Use the service for any purpose illegal in the Kingdom of Saudi Arabia or your jurisdiction.

## 4. No Warranty

The service is provided **as-is** for academic and evaluation purposes. ACR-QA findings are advisory only — they do not constitute a security audit, a legal compliance opinion, or a warranty of any kind. Always review findings before acting on them.

## 5. Limitation of Liability

To the maximum extent permitted by law, the operator is not liable for any damages arising from use of the service, including missed vulnerabilities, false positives, or data loss.

## 6. Data & Privacy

Data handling is described in [PRIVACY.md](PRIVACY.md). Summary: code snippets (≤500 chars) are sent to Groq for AI explanations; full source files never leave your machine in self-hosted mode.

## 7. Account Deletion

You may delete your account at any time via `DELETE /v1/auth/users/me`. All personal data is removed within 24 hours per the retention policy in PRIVACY.md.

## 8. Changes

Terms may be updated with 14 days notice posted at acrqa.dev. Continued use after notice constitutes acceptance.

## 9. Contact

ahmedabbass871@gmail.com
