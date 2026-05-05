# C1 — System Context Diagram

> Level 1 of the C4 model. Shows ACR-QA as a black box and everything it talks to.

```mermaid
C4Context
    title ACR-QA — System Context

    Person(dev, "Developer", "Pushes code, reviews PR findings, marks false positives via dashboard")
    Person(supervisor, "Project Supervisor / Reviewer", "Evaluates analysis results and thesis quality")

    System(acrqa, "ACR-QA", "Automated Code Review & Quality Assurance platform. Runs 10+ static analysis tools, normalises findings, generates RAG-enhanced AI explanations, enforces quality gates.")

    System_Ext(github, "GitHub / GitLab", "Hosts the repository. Receives PR comments and SARIF uploads. Triggers CI/CD workflows.")
    System_Ext(groq, "Groq API", "Provides LLM inference (Llama 3.3-70b). Used for AI explanations, semantic entropy, and path feasibility validation. Free tier.")
    System_Ext(prometheus_grafana, "Prometheus + Grafana", "Scrapes /metrics endpoint every 15 s. Grafana renders 6-panel operational dashboard.")

    Rel(dev, acrqa, "Runs analysis via CLI or pushes code to GitHub")
    Rel(acrqa, github, "Posts PR review comments, uploads SARIF to Security tab, fails merge on gate violation")
    Rel(acrqa, groq, "Sends code snippet + rule context, receives AI explanation (HTTPS)")
    Rel(acrqa, prometheus_grafana, "Exposes /metrics endpoint")
    Rel(dev, acrqa, "Views findings on web dashboard, marks false positives, exports reports")
    Rel(supervisor, acrqa, "Reviews evaluation results, precision/recall metrics, OWASP coverage")
```

## Key relationships

| Relationship | Direction | Protocol | Notes |
|---|---|---|---|
| Developer → CLI | Push | stdin / shell | `python3 CORE/main.py --target-dir ./repo` |
| GitHub Actions → ACR-QA | Trigger | GitHub Actions runner | `.github/workflows/acr-qa.yml` |
| ACR-QA → GitHub | Post | REST API (HTTPS) | PR comments + SARIF upload |
| ACR-QA → Groq | Request | HTTPS | Key pool of 4 keys for rate limit bypass |
| Prometheus → ACR-QA | Scrape | HTTP `/metrics` | Every 15 seconds |

## What ACR-QA does NOT do

- Does not detect CSRF, IDOR, auth bypass, or business logic bugs (static analysis limits — by design)
- Does not store code on external servers (Groq only receives the relevant snippet + rule text)
- Does not require cloud hosting — designed for local or self-hosted deployment
