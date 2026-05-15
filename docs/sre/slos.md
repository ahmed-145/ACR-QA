# ACR-QA — Service Level Objectives (SLOs)

> Formal SLO definitions for the ACR-QA service.
> These inform alerting rules, runbooks, and error budget management.

---

## SLO 1 — API Availability

| | |
|---|---|
| **SLO** | 99.5% of HTTP requests return a non-5xx response |
| **Window** | Rolling 30 days |
| **Error budget** | 0.5% × 30d × 24h × 60m = **216 minutes/month** |
| **Measurement** | `1 - (rate(acrqa_http_errors_total[30d]) / rate(acrqa_http_requests_total[30d]))` |
| **Alert threshold** | Page if budget burns faster than 5× baseline (30-min window) |

**Prometheus query (dashboard):**
```promql
(1 - (
  rate(acrqa_http_errors_total[1h])
  / rate(acrqa_http_requests_total[1h])
)) * 100
```

---

## SLO 2 — API P95 Latency

| | |
|---|---|
| **SLO** | 95th-percentile request latency < 500ms |
| **Window** | Rolling 7 days |
| **Excludes** | `/api/runs/{id}/explain` (AI calls — SLO 3 covers these) |
| **Measurement** | `histogram_quantile(0.95, rate(acrqa_http_request_duration_seconds_bucket[7d]))` |
| **Alert threshold** | Alert if P95 > 500ms sustained for 5 minutes |

**Prometheus query (dashboard):**
```promql
histogram_quantile(0.95,
  rate(acrqa_http_request_duration_seconds_bucket[5m])
) * 1000
```

---

## SLO 3 — Scan Completion Rate

| | |
|---|---|
| **SLO** | 99% of analysis runs complete with status = 'completed' (not 'failed') |
| **Window** | Rolling 7 days |
| **Error budget** | 1% × 7d × expected_scans — allows ~70 failed scans per 7000 |
| **Measurement** | PostgreSQL: `SELECT COUNT(*) FILTER (WHERE status='completed') / COUNT(*) FROM analysis_runs WHERE started_at > NOW() - INTERVAL '7 days'` |
| **Alert threshold** | Alert if failure rate > 5% in any 1-hour window |

---

## SLO 4 — AI Explanation Latency (P95)

| | |
|---|---|
| **SLO** | AI explanation endpoint P95 < 5 seconds |
| **Window** | Rolling 7 days |
| **Context** | Includes 3× Groq API calls for semantic entropy — inherently slower than regular endpoints |
| **Measurement** | `histogram_quantile(0.95, rate(acrqa_http_request_duration_seconds_bucket{endpoint="/api/runs/{id}/explain"}[7d]))` |
| **Alert threshold** | Alert if P95 > 10s (2× SLO) for 10 minutes — likely Groq rate limit or provider issue |

---

## Error Budget Policy

| Budget remaining | Action |
|---|---|
| > 50% | Normal development velocity |
| 25–50% | Review and document recent 5xx errors |
| 10–25% | Feature freeze — only reliability fixes |
| < 10% | Incident declared — follow `docs/sre/runbooks/high-error-rate-5xx.md` |

---

## Grafana Dashboard

SLO panels are on the ACR-QA dashboard at **http://localhost:3000**:
- Panel 7: API Availability % (stat, green > 99.5%)
- Panel 8: P95 Latency SLO (stat, green < 500ms)
- Panel 9: Scan Success Rate (gauge, red < 95%, yellow 95-99%)

---

---

## Alerting Implementation (Phase 12 Week 5)

Multi-window burn-rate alerting is implemented in `config/alerts/slo_burn_rate.yml` (Prometheus).

| Alert | Window | Threshold | Severity |
|---|---|---|---|
| `SLOBudgetBurnRateFast` | 1h + 5h | 14.4× budget | page (P1) |
| `SLOBudgetBurnRateSlow` | 6h + 1d | 3× budget | warning (P2) |

Error budget: 0.1% over 30 days. Recording rules pre-compute 1h/5h/6h/1d error-rate windows.
Load-tested at 500 RPS via `tests/load/locustfile.py` — targets: p99 < 2s, error rate < 1%.

*Last updated: 2026-05-15 — Phase 12 Week 5*
