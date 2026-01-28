# Render.com Deployment - Step by Step

## Prerequisites
- GitHub account with your ACR-QA repo pushed
- Render.com account (free)

---

## Step 1: Push Code to GitHub

```bash
cd /home/ahmeed/Documents/KSIU/GRAD/SOLO
git add -A
git commit -m "Add cloud deployment config"
git push origin main
```

---

## Step 2: Create Render Account

1. Go to **[render.com](https://render.com)**
2. Click **"Get Started for Free"**
3. Sign up with **GitHub** (recommended)

---

## Step 3: Create New Web Service

1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Connect your GitHub repository
4. Select **"ahmed-145/ACR-QA"** repo

---

## Step 4: Configure Service

Fill in these settings:

| Setting | Value |
|---------|-------|
| **Name** | `acrqa-api` |
| **Region** | Choose nearest to you |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn FRONTEND.app:app --bind 0.0.0.0:$PORT` |
| **Plan** | `Free` |

---

## Step 5: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**:

| Key | Value |
|-----|-------|
| `FLASK_SECRET_KEY` | (click Generate) |
| `PYTHON_VERSION` | `3.11.4` |

---

## Step 6: Create PostgreSQL Database (Optional)

If you need the database:

1. Click **"New +"** → **"PostgreSQL"**
2. Name: `acrqa-db`
3. Plan: `Free`
4. Click **"Create Database"**
5. Copy the **Internal Database URL**
6. Add to web service as `DATABASE_URL`

---

## Step 7: Deploy

1. Click **"Create Web Service"**
2. Wait 5-10 minutes for build
3. Watch the logs for errors

---

## Step 8: Get Your URL

After deployment, your API is at:
```
https://acrqa-api.onrender.com
```

Test it:
```bash
curl https://acrqa-api.onrender.com/api/health
# Returns: {"status": "healthy", "version": "2.0"}
```

---

## Step 9: Update VSCode Extension

In VSCode settings, set:
```json
{
  "acrqa.apiUrl": "https://acrqa-api.onrender.com"
}
```

---

## Troubleshooting

**Build Failed?**
- Check logs for missing dependencies
- Ensure `gunicorn` is in `requirements.txt`

**App Not Starting?**
- Verify start command is correct
- Check for import errors in logs

**Cold Starts (30-60 sec)?**
- Normal for free tier
- App spins down after 15 min of inactivity

---

## Cost: FREE ✅

Render free tier includes:
- 750 hours/month (enough for 1 always-on app)
- Auto-deploy on git push
- Free PostgreSQL (90-day retention)

---

**Done!** Your API is now live at `https://acrqa-api.onrender.com` 🎉
