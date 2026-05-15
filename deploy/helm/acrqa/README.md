# ACR-QA Helm Chart

Deploys ACR-QA (AI Code Review & Security Analysis) to Kubernetes with:
- API deployment (FastAPI) with liveness/readiness probes
- Celery worker deployment
- HPA scaling 2→20 pods on CPU/memory
- Pod Disruption Budget (minAvailable: 1)
- NetworkPolicy (ingress-nginx + monitoring namespaces only)
- Ingress with cert-manager TLS

## Prerequisites

- Kubernetes 1.25+
- Helm 3.10+
- cert-manager (for TLS)
- nginx ingress controller

## Install

```bash
helm install acrqa ./deploy/helm/acrqa \
  --set api.env.DATABASE_URL="postgresql://user:pass@host:5432/acrqa" \
  --set api.env.REDIS_URL="redis://redis:6379/0" \
  --set api.env.GROQ_API_KEY="gsk_..." \
  --set api.env.SECRET_KEY="$(openssl rand -hex 32)" \
  --set ingress.host="acrqa.yourdomain.com"
```

## Upgrade

```bash
helm upgrade acrqa ./deploy/helm/acrqa \
  --reuse-values \
  --set api.image.tag="4.1.0"
```

## Values

| Key | Default | Description |
|-----|---------|-------------|
| `api.image.tag` | `4.0.0` | Docker image tag |
| `api.replicaCount` | `2` | API pod replicas |
| `worker.replicaCount` | `2` | Celery worker replicas |
| `autoscaling.minReplicas` | `2` | HPA minimum |
| `autoscaling.maxReplicas` | `20` | HPA maximum |
| `ingress.host` | `acrqa.example.com` | Ingress hostname |
| `ingress.tls` | `true` | Enable cert-manager TLS |
| `postgresql.enabled` | `true` | Deploy in-cluster Postgres (dev only) |
| `redis.enabled` | `true` | Deploy in-cluster Redis |

## Production Notes

- Set `postgresql.enabled=false` and `redis.enabled=false` in production; use RDS + ElastiCache
- Pass secrets via `--set` or a sealed-secrets / ESO solution — never commit plaintext values
- NetworkPolicy allows only `ingress-nginx` and `monitoring` namespaces by default
