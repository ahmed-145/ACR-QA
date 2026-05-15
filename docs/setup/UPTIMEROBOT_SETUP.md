# UptimeRobot External Monitoring Setup — Task 12.33

UptimeRobot provides free external uptime monitoring (every 5 minutes) for the Railway-hosted API.

## One-time setup (human task)

1. Go to <https://uptimerobot.com> and create a free account.
2. Click **"+ Add New Monitor"**.
3. Configure:
   | Field | Value |
   |---|---|
   | Monitor Type | HTTP(s) |
   | Friendly Name | `ACR-QA API` |
   | URL | `https://acrqa-api-production.up.railway.app/health` |
   | Monitoring Interval | 5 minutes |
   | Alert Contacts | your email |
4. Click **"Create Monitor"**.

## Status badge (optional)

Once the monitor is created, UptimeRobot generates a **public status page** and a **badge URL**:

1. Open the monitor → **"Get status page badge"**
2. Copy the badge URL (format: `https://img.shields.io/uptimerobot/status/m<ID>-<hash>`)
3. Replace the placeholder badge in `README.md` line with the live badge URL.

The current README badge links to this document until the live monitor ID is available.

## What is monitored

The `/health` endpoint returns:
```json
{"status": "healthy", "database": "connected", "redis": "connected"}
```

UptimeRobot triggers an email alert if HTTP status is non-200 or the response time exceeds 30 s.
