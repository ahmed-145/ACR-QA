# Runbook: Database Connection Pool Exhausted

**Severity:** High
**On-call trigger:** `psycopg2.OperationalError: connection pool exhausted` in logs, or P95 latency > 5s with DB-related tracebacks

---

## Symptoms

- Flask logs: `OperationalError: FATAL: remaining connection slots are reserved for replication`
- API endpoints return 500 with DB-related errors
- `docker exec acr-qa-postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity"` returns value close to `max_connections`
- Dashboard stops loading findings

---

## Diagnosis

```bash
# 1. Check active PostgreSQL connections
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT client_addr, state, count(*) FROM pg_stat_activity GROUP BY 1,2 ORDER BY 3 DESC;"

# 2. Check for long-running queries holding connections open
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT pid, now() - query_start AS duration, query, state
   FROM pg_stat_activity
   WHERE state != 'idle' AND query_start < now() - INTERVAL '30 seconds'
   ORDER BY duration DESC;"

# 3. Check what max_connections is set to
docker exec acr-qa-postgres psql -U postgres -c "SHOW max_connections;"
```

---

## Resolution Steps

### Step 1: Terminate idle connections (safe)

```bash
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle'
     AND query_start < now() - INTERVAL '5 minutes'
     AND pid != pg_backend_pid();"
```

### Step 2: Restart the app (if Step 1 doesn't clear it)

```bash
# This closes all app-held connections cleanly
docker compose restart app
```

### Step 3: Kill long-running queries blocking connections

```bash
# Find and kill queries running > 60 seconds
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state != 'idle'
     AND query_start < now() - INTERVAL '60 seconds'
     AND pid != pg_backend_pid();"
```

---

## Root Cause & Prevention

ACR-QA uses `psycopg2` with direct `connect()` calls (no connection pool by design for the thesis). Under concurrent CI load (multiple GitHub Actions runners), each runner opens its own DB connection. If many runners trigger simultaneously:

**Short-term fix:** Increase max_connections in docker-compose.yml:
```yaml
# docker-compose.yml postgres service
command: postgres -c max_connections=200
```

**Long-term fix (post-thesis):** Migrate `DATABASE/database.py` to use `psycopg2.pool.ThreadedConnectionPool` with a pool size of 10-20.

---

## Verification

```bash
# Confirm connections are back to normal
docker exec acr-qa-postgres psql -U postgres -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname = 'acrqa';"
# Expected: < 20 for typical load

curl -sf http://localhost:5000/api/health && echo "API healthy"
```
