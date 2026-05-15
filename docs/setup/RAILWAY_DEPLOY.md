# Railway PR Preview Deploys — Setup Guide

PR preview environments let reviewers test ACR-QA changes on a live URL before merging.
Each PR gets its own isolated Railway environment; it is torn down automatically when the PR closes.

---

## Prerequisites

- GitHub Student Pack (free Railway Hobby plan)
- Railway account linked to your GitHub org: [railway.app](https://railway.app)

---

## One-Time Setup

### Step 1: Create the Railway project

```bash
npm install -g @railway/cli
railway login
railway init   # name it "acr-qa"
```

### Step 2: Add PostgreSQL and Redis services

In the Railway dashboard → your project:
1. **New Service → Database → PostgreSQL** — name it `postgres`
2. **New Service → Database → Redis** — name it `redis`

Railway injects `DATABASE_URL` and `REDIS_URL` automatically into your app service.

### Step 3: Set environment variables

In Railway → your project → `acr-qa` service → Variables:

```
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...
JWT_SECRET_KEY=<random 32 char string>
GITHUB_TOKEN=ghp_...
SENTRY_DSN=https://...@sentry.io/...   # optional — get from sentry.io project settings
```

`DATABASE_URL` and `REDIS_URL` are provided automatically — do not set them manually.

### Step 4: Add GitHub secrets

```bash
railway whoami --token   # prints your token
```

Go to: **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `RAILWAY_TOKEN` | `<token from railway whoami --token>` |
| `RAILWAY_PRODUCTION_URL` | `https://acrqa-api-production.up.railway.app` (your Railway domain) |

### Step 5: Push to trigger the first deploy

```bash
git push origin main
```

- `deploy.yml` — triggers on every push to `main`, deploys to production
- `deploy-preview.yml` — triggers on every PR, deploys a throwaway preview environment

---

## How It Works

| Event | Action |
|-------|--------|
| PR opened / pushed | `railway up --environment pr-<N>` deploys a new preview |
| PR updated | Same environment is redeployed with the latest commit |
| PR merged / closed | `railway environment delete pr-<N>` tears down the environment |

The preview URL is posted as a comment on the PR by the workflow.

---

## Manual Operations

```bash
# List all preview environments
railway environment list

# Open a specific preview in browser
railway open --environment pr-42

# Delete a stale preview manually
railway environment delete pr-42 --service acr-qa --yes
```

---

## Database Migrations on Preview

The `startCommand` in `railway.toml` runs `alembic upgrade head` before starting the app.
Each new preview environment gets a fresh PostgreSQL instance with migrations applied automatically.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `RAILWAY_TOKEN` not found | Re-add secret in GitHub → Settings → Secrets |
| Deploy stuck at "building" | Check `railway logs --service acr-qa --environment pr-N` |
| Health check fails | Ensure `DATABASE_URL` is set (PostgreSQL service must be added) |
| Preview URL not posted | The `actions/github-script` step needs `issues: write` permission — check workflow `permissions` block |
