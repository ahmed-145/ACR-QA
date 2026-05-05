# Runbook: High Error Rate (5xx)

**Severity:** High
**On-call trigger:** Error rate > 5% in a 5-minute window, OR SLO error budget < 10%

---

## Symptoms

- Grafana `Error Rate (5xx/min)` panel shows sustained non-zero values
- API responses return `{"error": "Internal server error"}` with status 500
- Flask logs contain tracebacks
- GitHub Actions CI jobs failing on ACR-QA analysis step

---

## Immediate Diagnosis (< 5 minutes)

```bash
# 1. Check Flask app logs for tracebacks
docker compose logs app --tail=50 | grep -A 10 "ERROR\|Traceback\|500"

# 2. Check if it's a DB connection issue (most common cause)
docker compose logs app --tail=20 | grep -i "database\|psycopg2\|connection"

# 3. Check if all services are up
docker compose ps

# 4. Quick health check
curl -sv http://localhost:5000/api/health
```

---

## Resolution by Root Cause

### Root cause: Database connection failure

```bash
# Check Postgres is healthy
docker compose ps postgres
docker exec acr-qa-postgres pg_isready -U postgres -d acrqa

# If Postgres is down, restart it
docker compose restart postgres

# Wait for health check to pass, then restart app
sleep 10 && docker compose restart app
```

### Root cause: Redis connection failure

```bash
docker compose ps redis
docker exec acr-qa-redis redis-cli ping   # should return PONG

# If Redis is down (non-fatal — rate limiting fails open)
docker compose restart redis
```

### Root cause: Application code exception (unhandled error)

```bash
# Find the specific endpoint causing 500s
grep "500" /var/log/acrqa/access.log | awk '{print $7}' | sort | uniq -c | sort -rn

# Check the Flask error handler logs
docker compose logs app 2>&1 | grep "ERROR" | tail -30

# If it's a specific endpoint, check if it's a missing DB record:
# The fix is usually to return 404 not 500 — see AGENT_NOTES.md gotcha #7
```

### Root cause: Out of memory (OOM)

```bash
# Check container resource usage
docker stats --no-stream

# If app container is using > 80% memory:
docker compose restart app
# Then investigate what caused the memory spike (large repo scan?)
```

---

## Verification

```bash
# Confirm error rate is back to 0
curl -s http://localhost:5000/api/health
# Expected: {"status": "healthy"}

# Watch error rate in real time
watch -n5 'curl -s http://localhost:9090/api/v1/query \
  --data-urlencode "query=rate(acrqa_http_errors_total[1m])" \
  | python3 -m json.tool | grep value'
```

---

## Post-Incident

1. Document the incident in `CHANGELOG.md` under the next version section
2. Add a test case that would have caught the issue (`TESTS/`)
3. Update `DATABASE/database.py` if a new "existence check before UPDATE" pattern is needed
