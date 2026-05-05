# ADR 0005 — PostgreSQL for Provenance Storage

**Status:** Accepted
**Date:** 2026-05-05
**Author:** Ahmed Mahmoud Abbas

---

## Context

ACR-QA's thesis research question RQ2 is: *"How do you ensure full provenance for AI-generated findings?"*

Provenance means: for any finding shown to a developer, you can trace back to:
- Which analysis run produced it (repo, branch, PR number, commit SHA)
- Which tool and rule detected it
- The exact LLM prompt that generated the explanation
- The exact LLM response, latency, model, and temperature
- Whether a human marked it as a false positive or helpful
- Whether it was suppressed by triage memory

This data must be:
- **Queryable** — the dashboard runs `GET /api/runs/{id}/findings` with severity/category filters
- **Relational** — findings belong to runs; explanations belong to findings; feedback belongs to findings
- **Durable** — data must survive application restarts
- **Concurrent** — multiple CI runners may insert findings simultaneously for the same repo

---

## Decision

Use **PostgreSQL 15** as the primary data store, with **6 tables** designed for audit trail completeness:

```sql
analysis_runs        -- one row per scan: repo, branch, pr_number, commit_sha, status, timing
findings             -- one row per finding: canonical_rule_id, file, line, severity, confidence_score
llm_explanations     -- one row per AI call: prompt, response, model, latency, entropy, self_eval, feasibility
feedback             -- one row per 👍/👎 click: finding_id, is_false_positive, is_helpful
suppression_rules    -- learned from feedback: rule_id + file_pattern → suppress future matches
pr_comments          -- tracks which findings were posted to which PR
```

The `DATABASE/database.py` interface wraps all SQL with a reconnection-safe `execute()` method and provides typed methods (`insert_finding()`, `get_findings_with_explanations()`, etc.) — no raw SQL in application code.

Schema initialisation is idempotent (`IF NOT EXISTS`) — safe to re-run on an existing database.

---

## Consequences

**What we gain:**
- Full provenance: every LLM call is stored with its exact prompt, response, model, latency — answering RQ2 definitively
- Historical trend data: `GET /api/trends` shows severity breakdown across the last 30 runs
- Feedback loop: `INSERT INTO feedback` → `feedback_tuner.py` reads it → generates `severity_overrides.yml`
- Concurrent-safe: PostgreSQL handles multiple CI runners writing simultaneously without data corruption
- ACID guarantees: a finding is either fully committed or not — no partial state

**What we lose:**
- Requires PostgreSQL running (Docker or native install) — higher setup cost than SQLite
- `psycopg2` is synchronous — under heavy load, the DB layer blocks the Flask thread pool. Acceptable for thesis scope; `asyncpg` is the migration path for production.

**Deployment:**
Docker Compose spins up PostgreSQL on port 5433 (mapped from 5432 inside the container to avoid conflicts with host Postgres). Schema initialises on first `make init-db`.

---

## Alternatives Considered

| Option | Rejected Because |
|---|---|
| SQLite | No concurrent write support — two CI runners inserting simultaneously cause lock errors; file locking semantics aren't suitable for a web app |
| MongoDB | Provenance data is highly relational (run → finding → explanation → feedback); a document store makes these joins awkward and loses ACID guarantees |
| File system (JSON files per run) | Not queryable; no concurrent safety; dashboard would need to parse files on every request |
| In-memory only (no persistence) | Defeats the entire provenance research question — RQ2 can't be answered without durable storage |
| Redis as primary store | Redis is volatile by default; appropriate for cache and rate limiting but not for audit trail |
