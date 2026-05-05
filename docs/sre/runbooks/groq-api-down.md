# Runbook: Groq API Down / Rate Limited

**Severity:** Medium (scans complete, just without AI explanations)
**On-call trigger:** AI explanation latency P95 > 10s for 10+ minutes, OR 429 errors in Flask logs

---

## Symptoms

- Dashboard shows findings without AI explanation text
- Flask logs contain: `groq.RateLimitError`, `httpx.TimeoutException`, or HTTP 429
- Grafana: LLM Latency panel shows spikes > 5000ms or drops to 0
- `GET /api/runs/{id}/findings` returns findings with `explanation: null`

---

## Immediate Mitigation (< 2 minutes)

ACR-QA is designed to degrade gracefully. If Groq is unavailable:
- Scans still complete — all findings are detected and stored
- AI explanation falls back to the static rule description from `config/rules.yml`
- Quality gate still evaluates and blocks/passes CI correctly
- **No action required for scan functionality**

---

## Diagnosis

```bash
# 1. Check if it's a rate limit (429) or outage (5xx)
grep -i "groq\|rate.limit\|429\|timeout" /var/log/acrqa/app.log | tail -20

# 2. Check Groq status page
# https://status.groq.com

# 3. Check which key is failing (ACR-QA rotates through GROQ_API_KEY_1..4)
grep "GROQ_API_KEY" .env | wc -l   # should be 4 keys

# 4. Test a key manually
curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY_1" | python3 -m json.tool | head -5
```

---

## Resolution Steps

### If rate limited (429):

```bash
# Check current key pool size
grep "GROQ_API_KEY" .env | grep -v "^#" | wc -l

# Add more API keys if available (up to 8 for ~240 req/min)
# .env:
# GROQ_API_KEY_5=gsk_...
# GROQ_API_KEY_6=gsk_...

# Restart app to pick up new keys (Docker)
docker compose restart app
```

### If Groq is down (5xx / connection refused):

```bash
# Enable no-AI mode temporarily (set in .acrqa.yml)
# ai:
#   enabled: false
# This makes scans instant and doesn't consume Groq quota

# Or run with --no-ai flag for manual scans
python3 CORE/main.py --target-dir . --no-ai
```

### If a specific key is expired/revoked:

```bash
# Remove the bad key from .env, renumber remaining keys
# GROQ_API_KEY_1=... (keep)
# GROQ_API_KEY_2=... (remove if bad)
# GROQ_API_KEY_3=... → rename to GROQ_API_KEY_2

docker compose restart app
```

---

## Verification

```bash
# Confirm explanations are working again
curl -s http://localhost:5000/api/runs/latest/findings | \
  python3 -c "import json,sys; data=json.load(sys.stdin); \
  explained = sum(1 for f in data.get('findings', []) if f.get('explanation')); \
  print(f'{explained}/{len(data[\"findings\"])} findings have AI explanations')"
```

---

## Prevention

- Maintain 4 API keys in rotation (current max throughput: ~120 req/min)
- Monitor `LLM Explanation Latency` panel in Grafana — spikes above 3000ms often precede rate limits
- Use Redis cache (7-day TTL) — repeated scans of unchanged code don't call Groq again
