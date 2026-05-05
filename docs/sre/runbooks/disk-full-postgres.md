# Runbook: Disk Full — PostgreSQL

**Severity:** Critical
**On-call trigger:** PostgreSQL logs `could not write to file: No space left on device`, or Docker volume usage > 90%

---

## Symptoms

- PostgreSQL container crashes or becomes read-only
- `INSERT` queries fail with `ENOSPC` errors
- `docker system df` shows volumes near capacity
- ACR-QA findings stop being saved (runs show `status: failed`)

---

## Diagnosis

```bash
# 1. Check Docker volume disk usage
docker system df -v | grep postgres

# 2. Check host disk usage
df -h /var/lib/docker

# 3. Identify the largest tables
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
   FROM pg_stat_user_tables
   ORDER BY pg_total_relation_size(relid) DESC;"

# 4. Check for bloated tables (dead tuples from mass deletes)
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT relname, n_dead_tup, n_live_tup
   FROM pg_stat_user_tables
   ORDER BY n_dead_tup DESC;"
```

---

## Resolution Steps

### Step 1: Free space immediately (safe operations)

```bash
# Remove unused Docker images, build cache
docker system prune -f

# Remove old log files
find /var/log -name "*.log" -mtime +7 -delete 2>/dev/null

# Check if DATA/outputs/ has accumulated large files on the host
du -sh /home/ahmeed/Documents/KSIU/GRAD/SOLO/DATA/outputs/
# If large: rm -rf DATA/outputs/*.json DATA/outputs/*.md (generated, not source-of-truth)
```

### Step 2: Reclaim PostgreSQL space (VACUUM)

```bash
# VACUUM reclaims dead tuples without locking
docker exec acr-qa-postgres psql -U postgres -d acrqa -c "VACUUM ANALYZE;"

# Full vacuum (rewrites tables — more aggressive, causes brief lock)
docker exec acr-qa-postgres psql -U postgres -d acrqa -c "VACUUM FULL ANALYZE;"
```

### Step 3: Delete old analysis runs (if data retention allows)

```bash
# Preview: how many runs older than 30 days?
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "SELECT count(*) FROM analysis_runs WHERE started_at < NOW() - INTERVAL '30 days';"

# Delete (CASCADE removes findings, explanations, feedback for those runs)
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "DELETE FROM analysis_runs WHERE started_at < NOW() - INTERVAL '30 days';"

# Reclaim space after delete
docker exec acr-qa-postgres psql -U postgres -d acrqa -c "VACUUM FULL ANALYZE;"
```

---

## Verification

```bash
docker system df -v | grep postgres
df -h /var/lib/docker

# Confirm PostgreSQL is accepting writes
docker exec acr-qa-postgres psql -U postgres -d acrqa -c \
  "INSERT INTO analysis_runs (repo_name, status) VALUES ('disk-test', 'running');
   DELETE FROM analysis_runs WHERE repo_name = 'disk-test';"
# Expected: INSERT 0 1 / DELETE 1
```

---

## Prevention

- Set up a cron job to VACUUM weekly: `0 3 * * 0 docker exec acr-qa-postgres psql -U postgres -d acrqa -c "VACUUM ANALYZE;"`
- Monitor volume usage in Grafana (add a `node_filesystem_avail_bytes` panel if Node Exporter is deployed)
- See `docs/sre/runbooks/restore-from-backup.md` for recovery if disk corruption occurs
