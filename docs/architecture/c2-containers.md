# C2 — Container Diagram

> Level 2 of the C4 model. Shows the deployable units inside ACR-QA and how they communicate.

```mermaid
C4Container
    title ACR-QA — Containers

    Person(dev, "Developer")

    Container_Boundary(acrqa, "ACR-QA System") {
        Container(cli, "CLI / GitHub Action", "Python 3.11", "Entry point. Parses args (--lang, --rich, --json, --diff-only). Routes to correct language adapter. Orchestrates full pipeline.")
        Container(core, "Analysis Engine", "Python 3.11", "Runs 10+ static tools in parallel, normalises findings to canonical schema, scores severity, deduplicates, applies config filters, runs AI explanation batch, enforces quality gate.")
        Container(dashboard, "Web Dashboard", "Flask 3.x + Jinja2", "22 REST API endpoints. Serves HTML dashboard at :5000. Exposes /metrics for Prometheus.")
        ContainerDb(postgres, "PostgreSQL 15", "PostgreSQL", "6 tables: analysis_runs, findings, llm_explanations, feedback, suppression_rules, pr_comments. Full provenance audit trail.")
        ContainerDb(redis, "Redis 7", "Redis", "Rate limiting (token bucket, 1 scan/repo/minute). LLM explanation cache (7-day TTL).")
    }

    Container_Ext(groq, "Groq API", "LLM-as-a-service", "Llama 3.3-70b for explanations. Llama 3.1-8b for path feasibility. Free tier.")
    Container_Ext(github, "GitHub / GitLab", "Git hosting + CI", "Triggers analysis, receives PR comments and SARIF.")
    Container_Ext(prometheus, "Prometheus", "Time-series DB", "Scrapes /metrics every 15 s.")
    Container_Ext(grafana, "Grafana", "Visualisation", "6-panel dashboard: request rate, P95 latency, error rate, LLM latency.")

    Rel(dev, cli, "Runs analysis", "shell / GitHub Actions")
    Rel(cli, core, "Invokes pipeline", "Python function call")
    Rel(core, postgres, "Reads/writes runs, findings, explanations", "psycopg2 / SQL")
    Rel(core, redis, "Checks rate limit, caches explanations", "redis-py")
    Rel(core, groq, "Sends evidence-grounded prompt, receives explanation", "HTTPS / httpx async")
    Rel(dashboard, postgres, "Reads findings, stats, trends", "psycopg2 / SQL")
    Rel(dashboard, dev, "Serves dashboard UI, REST API responses", "HTTP :5000")
    Rel(core, github, "Posts PR comments, uploads SARIF", "REST API / HTTPS")
    Rel(prometheus, dashboard, "Scrapes /metrics", "HTTP pull")
    Rel(grafana, prometheus, "Queries metrics", "PromQL")
```

## Container responsibilities

| Container | Responsibilities | Key files |
|---|---|---|
| **CLI / GitHub Action** | Argument parsing, language detection, entry point | `CORE/main.py` |
| **Analysis Engine** | Tool orchestration, normalisation, scoring, dedup, AI, quality gate | `CORE/engines/`, `CORE/adapters/` |
| **Web Dashboard** | REST API, HTML UI, /metrics endpoint | `FRONTEND/app.py`, `FRONTEND/templates/` |
| **PostgreSQL** | Provenance, findings history, feedback, suppression rules | `DATABASE/schema.sql`, `DATABASE/database.py` |
| **Redis** | Rate limiting, explanation cache | `CORE/utils/rate_limiter.py` |

## Port map

| Service | Port | Notes |
|---|---|---|
| Dashboard / API | 5000 | HTTP — local/internal only (no auth by design for thesis scope) |
| PostgreSQL | 5433 | Mapped from container's 5432 to avoid host conflict |
| Redis | 6379 | Default, no AUTH in dev |
| Prometheus | 9090 | Scrape target |
| Grafana | 3000 | admin/admin in dev |
