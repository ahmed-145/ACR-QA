# ACR-QA Cloud Deployment Guide

> **Current system:** v2.8.0 · Flask + PostgreSQL + Redis + Prometheus + Grafana (5-service Docker Compose stack)

---

## Choosing the Right Option

| Option | Cost | Setup Time | Docker Support | Best For |
|--------|------|------------|----------------|----------|
| **Railway** | Free tier (500h/mo) | ~10 min | ✅ Native | Thesis demo, quick live URL |
| **DigitalOcean Droplet** | ~$12-20/mo | ~30 min | ✅ Full stack | Production / long-running |
| **ngrok + Local** | Free | 2 min | N/A | Defense demo, zero config |

---

## Option 1: Railway (Recommended for Thesis Demo)

**Why Railway:** Push to GitHub → instantly live. Managed PostgreSQL and Redis as add-ons. No DevOps knowledge required.

### Step 1: Prepare

Make sure your repo has a `Dockerfile` or `railway.toml`. ACR-QA already has both.

```bash
# Confirm Dockerfile exists
ls FRONTEND/Dockerfile  # or root Dockerfile
```

### Step 2: Deploy

1. Go to **[railway.app](https://railway.app)** → sign in with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select `ahmed-145/ACR-QA`
4. Railway auto-detects Docker and starts building

### Step 3: Add Services

In your Railway project dashboard:

1. **Add PostgreSQL:**
   - Click **+ New** → **Database** → **PostgreSQL**
   - Railway injects `DATABASE_URL` automatically

2. **Add Redis:**
   - Click **+ New** → **Database** → **Redis**
   - Railway injects `REDIS_URL` automatically

### Step 4: Set Environment Variables

In Railway app settings → **Variables**:

```
FLASK_SECRET_KEY=your-super-secret-key-here
CEREBRAS_API_KEY=your-cerebras-key
ENVIRONMENT=production
```

### Step 5: Generate Domain

Settings → **Networking** → **Generate Domain**

Your app is live at: `https://acr-qa-production.up.railway.app`

### Step 6: Verify

```bash
curl https://your-app.up.railway.app/api/health
# Returns: {"status": "healthy", "version": "2.8.0"}
```

### Railway Free Tier Limits

- 500 compute hours/month (enough for demos)
- 1 GB RAM per service
- PostgreSQL: 1 GB storage
- Auto-sleeps after 30 min inactivity (cold start ~5s)

> **Thesis note:** For the defense, wake the app up 5 minutes before presenting. It will stay warm during the demo.

---

## Option 2: DigitalOcean Droplet (Production)

**Why DigitalOcean:** Full Docker Compose stack, persistent database, no cold starts. Use $200 GitHub Student credit.

### Step 1: Create Droplet

```bash
# Install doctl CLI
brew install doctl   # or: snap install doctl

# Authenticate
doctl auth init

# Create droplet (Ubuntu 22.04, 2GB RAM = $12/mo)
doctl compute droplet create acr-qa-prod \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-2gb \
  --region nyc3 \
  --ssh-keys $(doctl compute ssh-key list --no-header --format ID)
```

### Step 2: SSH and Install Docker

```bash
# SSH in
ssh root@YOUR_DROPLET_IP

# Install Docker + Compose
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin -y
```

### Step 3: Clone and Configure

```bash
git clone https://github.com/ahmed-145/ACR-QA.git
cd ACR-QA

# Create production .env
cat > .env << 'EOF'
FLASK_SECRET_KEY=generate-a-strong-key-here
CEREBRAS_API_KEY=your-key
POSTGRES_PASSWORD=strong-db-password
ENVIRONMENT=production
EOF
```

### Step 4: Deploy Full Stack

```bash
# Deploy all 5 services
docker compose -f docker-compose.prod.yml up -d

# Check all services are healthy
docker compose ps
```

### Step 5: Configure Domain (Optional)

Point your domain's A record to the Droplet IP, then:

```bash
# Install Caddy for HTTPS (auto-cert)
apt install caddy -y

# /etc/caddy/Caddyfile
acr-qa.yourdomain.com {
    reverse_proxy localhost:5000
}

systemctl restart caddy
```

### Services Running on Droplet

| Service | Port | Purpose |
|---------|------|---------|
| Flask App | 5000 | Web dashboard + API |
| PostgreSQL | 5432 | Findings + runs storage |
| Redis | 6379 | Rate limiting + caching |
| Prometheus | 9090 | Metrics scraping |
| Grafana | 3000 | Metrics visualization |

### GitHub Student Pack

1. Verify at [education.github.com](https://education.github.com/students)
2. Go to [digitalocean.com/github-students](https://www.digitalocean.com/go/github-students)
3. Apply $200 credit — covers ~16 months at $12/mo level

---

## Option 3: ngrok (Thesis Defense, Zero Setup)

**Best for:** Running locally on your laptop during the defense presentation.

```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc > /dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Start ACR-QA locally
docker compose up -d

# Expose publicly
ngrok http 5000
```

You get a URL like `https://abc123.ngrok.io` — share it or project it.

> **Pro tip:** Sign up at ngrok.com (free) to get a fixed subdomain instead of a random one.

---

## Architecture in Production

```
Internet → Load Balancer / Caddy (HTTPS)
              ↓
         Flask (5000)  ←→  PostgreSQL (5432)
              ↓                   ↑
         Redis (6379)    Prometheus (9090) → Grafana (3000)
```

---

## Summary Recommendation

| Scenario | Use |
|----------|-----|
| Thesis demo URL in report | Railway |
| Defense day (laptop) | ngrok |
| Self-hosted production | DigitalOcean Droplet |
| Organization on-premise | Docker Compose (self-host) |
