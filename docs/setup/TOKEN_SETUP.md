# ACR-QA Token Setup Guide

## 🔑 Required Tokens

### 1. Cerebras API Key (Required for AI Explanations)
**Already configured** ✅

---

### 2. GitHub Token (For GitHub Actions PR Comments)

#### How to Get:
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: `ACR-QA Bot`
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)

#### Add to GitHub Repository:
1. Go to your repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `CEREBRAS_API_KEY`
4. Value: Your Cerebras API key
5. Click "Add secret"

**Note:** GitHub Actions automatically provides `GITHUB_TOKEN` - you don't need to create this manually!

---

### 3. GitLab Token (For GitLab CI MR Comments)

#### How to Get:
1. Go to https://gitlab.com/-/profile/personal_access_tokens
2. Or: GitLab → Preferences → Access Tokens
3. Token name: `ACR-QA Bot`
4. Expiration: Set as needed (or no expiration)
5. Select scopes:
   - ✅ `api` (Access the authenticated user's API)
   - ✅ `write_repository` (Read and write repository)
6. Click "Create personal access token"
7. **Copy the token immediately!**

#### Add to GitLab Repository:
1. Go to your project → Settings → CI/CD
2. Expand "Variables"
3. Click "Add variable"
4. Key: `GITLAB_TOKEN`
5. Value: Your GitLab token
6. Flags: 
   - ✅ Protect variable
   - ✅ Mask variable
7. Click "Add variable"

Also add `CEREBRAS_API_KEY` the same way.

---

## 📝 Local .env File

For local development, update your `.env` file:

```bash
# Required
CEREBRAS_API_KEY=your_cerebras_key_here

# Optional (only for local testing of PR/MR posting)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# Database (already configured)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=acrqa
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Redis (optional - graceful degradation if not available)
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 🚀 Quick Setup Commands

```bash
# 1. Install Flask
pip install flask

# 2. Install Redis (optional)
sudo apt install redis-server
sudo systemctl start redis

# 3. Test the system
python3 CORE/main.py --target-dir TESTS/samples/comprehensive-issues --limit 5

# 4. Start dashboard
python3 FRONTEND/app.py
```

---

## 🔒 Security Best Practices

1. **Never commit tokens to git**
   - `.env` is already in `.gitignore`
   - Use GitHub/GitLab secrets for CI/CD

2. **Rotate tokens periodically**
   - GitHub: Every 90 days recommended
   - GitLab: Set expiration dates

3. **Use minimal scopes**
   - Only grant permissions you need
   - Review token usage regularly

4. **Revoke unused tokens**
   - GitHub: https://github.com/settings/tokens
   - GitLab: https://gitlab.com/-/profile/personal_access_tokens

---

## ✅ Verification

After setup, verify:

```bash
# Check environment variables
python3 -c "import os; print('✅ Cerebras:', 'CEREBRAS_API_KEY' in os.environ)"

# Test GitHub token (if set)
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Test GitLab token (if set)
curl -H "PRIVATE-TOKEN: $GITLAB_TOKEN" https://gitlab.com/api/v4/user
```

---

## 📚 Documentation Links

- **GitHub Tokens:** https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
- **GitLab Tokens:** https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html
- **Cerebras API:** https://inference-docs.cerebras.ai/
