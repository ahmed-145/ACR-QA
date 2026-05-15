# Third-Party Validation — ACR-QA Finding Agreement Tracker

**Version:** ACR-QA v3.9.1
**Last updated:** May 2026
**Purpose:** Per-finding record of which third-party tools (CodeQL, SonarCloud, Snyk) confirmed ACR-QA findings on the same benchmark repos.

---

## How to Read This Table

- **ACR-QA rule** — canonical rule ID (e.g. `SECURITY-027`)
- **Confirmed** — ✅ tool flagged same file/line/category | ✗ tool did not flag | `N/A` tool doesn't support this category
- **Notes** — context (e.g. different line number but same root cause = counted as ✅)

---

## DSVW (Damn Small Vulnerable Web)

| # | ACR-QA Rule | Severity | File | Line | CodeQL | SonarCloud | Snyk Code | Notes |
|---|---|---|---|---|:---:|:---:|:---:|---|
| 1 | SECURITY-027 (SQLi) | HIGH | dsvw.py | 89 | ✅ | ✅ | ✅ | All three confirm string-concat SQL |
| 2 | SECURITY-021 (OS cmd injection) | HIGH | dsvw.py | 132 | ✅ | ✅ | ✅ | `os.system` with user input |
| 3 | SECURITY-001 (eval) | HIGH | dsvw.py | 155 | ✅ | ✅ | ✅ | `eval(request.args.get(...))` |
| 4 | SECURITY-018 (yaml.load) | MEDIUM | dsvw.py | 201 | N/A | ✅ | ✗ | CodeQL has no yaml.load rule |

**DSVW agreement: CodeQL 3/4 (75%), SonarCloud 4/4 (100%), Snyk 3/4 (75%)**

---

## VulPy

| # | ACR-QA Rule | Severity | File | Line | CodeQL | SonarCloud | Snyk Code | Notes |
|---|---|---|---|---|:---:|:---:|:---:|---|
| 1 | SECURITY-027 (SQLi) | HIGH | app.py | 34 | ✅ | ✅ | ✅ | String interpolation in execute() |
| 2 | SECURITY-001 (eval) | HIGH | utils.py | 12 | ✅ | ✅ | ✅ | eval() with user-controlled data |
| 3 | SECURITY-008 (pickle) | HIGH | app.py | 78 | ✅ | ✗ | ✅ | SonarCloud has no pickle rule |
| 4 | SECURITY-021 (cmd injection) | HIGH | app.py | 91 | ✅ | ✅ | ✅ | subprocess.run(shell=True) |
| 5 | SECURITY-018 (yaml.load) | MEDIUM | config.py | 5 | N/A | ✅ | ✗ | CodeQL: N/A; Snyk: ✗ (no rule) |

**VulPy agreement: CodeQL 4/5 (80%), SonarCloud 4/5 (80%), Snyk 4/5 (80%)**

---

## Pygoat (Django)

| # | ACR-QA Rule | Severity | File | Line | CodeQL | SonarCloud | Snyk Code | Notes |
|---|---|---|---|---|:---:|:---:|:---:|---|
| 1 | SECURITY-027 (SQLi) | HIGH | introduction/views.py | 42 | ✅ | ✅ | ✅ | Raw SQL with string format |
| 2 | SECURITY-027 (SQLi) | HIGH | introduction/views.py | 67 | ✅ | ✅ | ✅ | Same file, second location |
| 3 | SECURITY-047 (JWT none alg) | CRITICAL | introduction/views.py | 118 | ✗ | ✗ | ✅ | CodeQL/Sonar lack JWT-alg rule |
| 4 | SECURITY-021 (cmd injection) | HIGH | lab/views.py | 23 | ✅ | ✅ | ✅ | `os.popen` with user input |
| 5 | SECURITY-001 (eval) | HIGH | lab/views.py | 89 | ✅ | ✅ | ✅ | eval() |
| 6 | SECURITY-018 (yaml.load) | MEDIUM | lab/views.py | 134 | N/A | ✅ | ✗ | |
| 7 | SECURITY-008 (pickle) | HIGH | lab/views.py | 156 | ✅ | ✗ | ✅ | SonarCloud no pickle rule |

**Pygoat agreement: CodeQL 5/7 (71%), SonarCloud 5/7 (71%), Snyk 5/7 (71%)**

---

## DVPWA (Damn Vulnerable Python Web Application)

| # | ACR-QA Rule | Severity | File | Line | CodeQL | SonarCloud | Snyk Code | Notes |
|---|---|---|---|---|:---:|:---:|:---:|---|
| 1 | SECURITY-027 (SQLi) | HIGH | views.py | 45 | ✅ | ✅ | ✅ | Raw format string in execute() |
| 2 | SECURITY-021 (cmd injection) | HIGH | views.py | 78 | ✅ | ✅ | ✅ | subprocess.call(shell=True) |
| 3 | SECURITY-001 (eval) | HIGH | views.py | 112 | ✅ | ✅ | ✅ | eval(user_input) |

**DVPWA agreement (3 confirmed findings): CodeQL 3/3 (100%), SonarCloud 3/3 (100%), Snyk 3/3 (100%)**

> Note: ACR-QA missed 3 DVPWA findings (`B105` hardcoded password, `B201` debug mode, CSRF). These are documented in `TESTS/evaluation/ground_truth/dvpwa.yml`. The 3 confirmed findings all agree 100% with third-party tools.

---

## Summary

| Repo | ACR-QA HIGH confirmed | CodeQL | SonarCloud | Snyk Code |
|------|:--------------------:|:------:|:----------:|:---------:|
| DSVW | 3 HIGH + 1 MEDIUM | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| VulPy | 4 HIGH + 1 MEDIUM | 4/4 (100%) | 3/4 (75%) | 4/4 (100%) |
| Pygoat | 5 HIGH + 1 CRITICAL + 1 MEDIUM | 4/5 (80%) | 4/5 (80%) | 4/5 (80%) |
| DVPWA | 3 HIGH | 3/3 (100%) | 3/3 (100%) | 3/3 (100%) |
| **Overall** | **15 HIGH / CRITICAL** | **14/15 (93%)** | **13/15 (87%)** | **14/15 (93%)** |

**ACR-QA HIGH findings confirmed by at least one third-party tool: 15/15 (100%)**

---

## Validation Methodology

1. Run ACR-QA on each repo at a pinned commit (see `ground_truth/*.yml` for SHAs).
2. Run CodeQL via `github/codeql-action/analyze@v3` (Python + JS queries).
3. Run SonarCloud via `SonarSource/sonarcloud-github-action` with `security-and-quality` quality profile.
4. Run Snyk Code via `snyk code test --json`.
5. For each ACR-QA finding, search third-party output for: same file + category match within ±5 lines.
6. Record ✅ / ✗ / N/A in this table.

This document is updated whenever ACR-QA's RULE_MAPPING changes or a new benchmark repo is added.
