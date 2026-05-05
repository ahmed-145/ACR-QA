# Runbook: Restore PostgreSQL from Backup

**Severity:** Critical
**Use when:** Data loss, corruption, or accidental table drop

---

## Creating a Backup (Do This Regularly)

```bash
# One-time manual backup
docker exec acr-qa-postgres pg_dump -U postgres acrqa \
  --format=custom \
  --compress=9 \
  --file=/tmp/acrqa_backup_$(date +%Y%m%d_%H%M%S).dump

# Copy from container to host
docker cp acr-qa-postgres:/tmp/acrqa_backup_*.dump ./backups/

# Automated daily backup (add to host crontab: crontab -e)
# 0 2 * * * docker exec acr-qa-postgres pg_dump -U postgres acrqa --format=custom --compress=9 > /backups/acrqa_$(date +\%Y\%m\%d).dump
```

---

## Restore Procedure

### Step 1: Stop the application

```bash
docker compose stop app
# Keep postgres running for the restore
```

### Step 2: Drop and recreate the database

```bash
docker exec acr-qa-postgres psql -U postgres -c "DROP DATABASE IF EXISTS acrqa;"
docker exec acr-qa-postgres psql -U postgres -c "CREATE DATABASE acrqa;"
```

### Step 3: Restore from backup

```bash
# Copy backup into container
docker cp ./backups/acrqa_20260505.dump acr-qa-postgres:/tmp/restore.dump

# Restore
docker exec acr-qa-postgres pg_restore \
  -U postgres \
  -d acrqa \
  --no-owner \
  --no-privileges \
  /tmp/restore.dump

# Verify row counts
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT 'analysis_runs' AS tbl, count(*) FROM analysis_runs
   UNION ALL SELECT 'findings', count(*) FROM findings
   UNION ALL SELECT 'llm_explanations', count(*) FROM llm_explanations;"
```

### Step 4: Run Alembic to ensure schema is current

```bash
# Apply any migrations that may have been added after the backup was taken
.venv/bin/alembic upgrade head
```

### Step 5: Restart the application

```bash
docker compose start app
sleep 5
curl -sf http://localhost:5000/api/health && echo "Restored successfully"
```

---

## Partial Restore (single table)

```bash
# Restore only the findings table from backup
docker exec acr-qa-postgres pg_restore \
  -U postgres \
  -d acrqa \
  --table=findings \
  /tmp/restore.dump
```

---

## Verify Data Integrity After Restore

```bash
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT
     (SELECT count(*) FROM analysis_runs WHERE status = 'completed') AS completed_runs,
     (SELECT count(*) FROM findings) AS total_findings,
     (SELECT count(*) FROM llm_explanations) AS explanations,
     (SELECT count(*) FROM feedback) AS feedback_entries,
     (SELECT count(*) FROM suppression_rules WHERE is_active) AS active_suppressions;"
```

---

## Estimated Recovery Time

| Scenario | Estimated time |
|---|---|
| Restore 1,000 findings | < 30 seconds |
| Restore 100,000 findings | 2–5 minutes |
| Full restore from scratch | < 10 minutes |
