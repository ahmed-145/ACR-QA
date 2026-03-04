# Cloud Deployment Guide (No Credit Card Needed!)

## Option 1: PythonAnywhere (RECOMMENDED)

**Cost:** FREE ✅  
**Credit Card:** NOT REQUIRED ✅  
**Best For:** Flask/Python apps

---

### Step 1: Create Account

1. Go to **[pythonanywhere.com](https://www.pythonanywhere.com)**
2. Click **"Start running Python online"**
3. Choose **"Create a Beginner account"** (FREE)
4. Sign up with email (no credit card!)

---

### Step 2: Upload Your Code

**Option A: Git Clone (Recommended)**

1. Open **Bash Console** (Consoles → Bash)
2. Run:
```bash
git clone https://github.com/ahmed-145/ACR-QA.git
cd ACR-QA
pip3 install --user -r requirements.txt
```

**Option B: Upload ZIP**
1. Go to **Files** tab
2. Upload your project ZIP
3. Extract and install requirements

---

### Step 3: Create Web App

1. Go to **Web** tab
2. Click **"Add a new web app"**
3. Choose **"Flask"**
4. Select **Python 3.10**
5. Set path to: `/home/yourusername/ACR-QA/FRONTEND/app.py`

---

### Step 4: Configure WSGI

1. Click on **WSGI configuration file**
2. Replace content with:

```python
import sys
path = '/home/yourusername/ACR-QA'
if path not in sys.path:
    sys.path.append(path)

from FRONTEND.app import app as application
```

---

### Step 5: Set Environment Variables (in WSGI file)

Add these lines at the TOP of your WSGI file (before imports):

```python
import os
os.environ['FLASK_SECRET_KEY'] = 'your-random-secret-key-here'
```

Your complete WSGI file should look like:

```python
import os
import sys

# Set environment variables
os.environ['FLASK_SECRET_KEY'] = 'my-super-secret-key-12345'

# Add project path
path = '/home/yourusername/ACR-QA'
if path not in sys.path:
    sys.path.append(path)

from FRONTEND.app import app as application
```

---

### Step 6: Reload

1. Click **"Reload"** button
2. Your app is live at: `https://yourusername.pythonanywhere.com`

---

### Step 7: Test It!

```bash
curl https://yourusername.pythonanywhere.com/api/health
# Returns: {"status": "healthy", "version": "2.0"}
```

---

## Limitations (Free Tier)

- CPU: Limited (enough for demos)
- Outbound: Only allowlisted sites
- Storage: 512 MB
- Apps: 1 web app

**Perfect for thesis demos!**

---

## Option 2: Replit

**Also free, no credit card**

1. Go to [replit.com](https://replit.com)
2. Create account with GitHub
3. Import from GitHub
4. Click "Run"

Your API: `https://your-repl-name.your-username.repl.co`

---

## Option 3: Local (For Thesis Demo)

**Simplest approach:**

1. Run locally: `python FRONTEND/app.py`
2. Share via ngrok for external access:
```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Expose your local server
ngrok http 5000
```

You get a public URL like: `https://abc123.ngrok.io`

---

## Summary

| Option | Setup Time | Best For |
|--------|------------|----------|
| PythonAnywhere | 10 min | Thesis + Production |
| Replit | 5 min | Quick demos |
| ngrok + Local | 2 min | Thesis defense only |

**My recommendation:** Use **PythonAnywhere** for a permanent URL, or **ngrok** for quick thesis demo!
