# 🚀 DEPLOYMENT GUIDE - Fuel Hedging Platform

**Version**: 1.0  
**Last Updated**: March 3, 2026  
**Estimated Time**: 30-45 minutes for first-time setup

---

## 📋 TABLE OF CONTENTS

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [GitHub Setup](#github-setup)
4. [Render.com Setup](#rendercom-setup)
5. [GitHub Actions Configuration](#github-actions-configuration)
6. [First Deployment](#first-deployment)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Troubleshooting](#troubleshooting)
9. [Updating Configuration](#updating-configuration)

---

## 🎯 OVERVIEW

This guide walks you through deploying the Fuel Hedging Platform from scratch to production.

### **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                     PRODUCTION STACK                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  GitHub Pages    │◄────────┤  GitHub Actions         │  │
│  │  (Frontend)      │         │  - ci.yml               │  │
│  │  Static Site     │         │  - deploy-frontend.yml  │  │
│  └────────┬─────────┘         │  - deploy-backend.yml   │  │
│           │                   │  - lstm-retrain.yml     │  │
│           │ HTTPS             │  - nightly-validation   │  │
│           │                   └─────────────────────────┘  │
│           ▼                                                 │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  Render.com      │         │  Render.com             │  │
│  │  hedge-api       │◄────────┤  hedge-postgres         │  │
│  │  (FastAPI)       │         │  (PostgreSQL 15 +       │  │
│  │                  │         │   TimescaleDB)          │  │
│  └────────┬─────────┘         └─────────────────────────┘  │
│           │                                                 │
│           │                   ┌─────────────────────────┐  │
│           ├──────────────────►│  Render.com             │  │
│           │                   │  hedge-redis            │  │
│           │                   │  (Redis)                │  │
│           │                   └─────────────────────────┘  │
│           │                                                 │
│           │                   ┌─────────────────────────┐  │
│           └──────────────────►│  Render.com             │  │
│                               │  hedge-n8n              │  │
│                               │  (Background Worker)    │  │
│                               └─────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### **Deployment Flow**

1. **Code Push**: Developer pushes to `main` branch
2. **CI/CD**: GitHub Actions runs tests, builds, and deploys
3. **Backend**: Render.com hosts API, database, Redis, N8N
4. **Frontend**: GitHub Pages hosts static React app
5. **Monitoring**: Slack notifications for alerts

---

## ✅ PREREQUISITES

### **1. Accounts Required**

- [ ] **GitHub Account** (with admin access to repository)
- [ ] **Render.com Account** (free tier works for prototype)
- [ ] **Slack Account** (for notifications)
- [ ] **External API Keys**:
  - [ ] EIA API Key (https://www.eia.gov/opendata/)
  - [ ] CME API Key (https://www.cmegroup.com/market-data)
  - [ ] OpenAI API Key (https://platform.openai.com/)

### **2. Local Tools**

- [ ] Git (version 2.30+)
- [ ] Node.js (version 20+)
- [ ] Python (version 3.11+)
- [ ] Text editor (VS Code recommended)

### **3. Knowledge Prerequisites**

- Basic understanding of:
  - Git and GitHub
  - Command line interface
  - Environment variables
  - YAML syntax

---

## 🔐 GITHUB SETUP

### **Step 1: Fork/Clone Repository**

```bash
# Option A: Clone the repository
git clone https://github.com/<your-username>/fuel-hedging-platform.git
cd fuel-hedging-platform

# Option B: Fork on GitHub first, then clone your fork
# GitHub UI: Click "Fork" button → Clone your fork
```

### **Step 2: Create GitHub Secrets**

**Navigate to**: Repository → Settings → Secrets and variables → Actions → New repository secret

Add the following 10 secrets:

#### **2.1 Render Deployment Hooks**

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `RENDER_DEPLOY_HOOK_API` | `https://api.render.com/deploy/srv-...` | Render → hedge-api → Settings → Deploy Hook → Copy URL |
| `RENDER_DEPLOY_HOOK_N8N` | `https://api.render.com/deploy/srv-...` | Render → hedge-n8n → Settings → Deploy Hook → Copy URL |

**Note**: You'll add these after creating Render services (Step 3)

#### **2.2 Database Connection**

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `RENDER_DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Render → hedge-postgres → Connect → External Connection String |

#### **2.3 Frontend Configuration**

| Secret Name | Value | Example |
|-------------|-------|---------|
| `VITE_API_BASE_URL` | Backend API URL | `https://hedge-api.onrender.com` |
| `VITE_WS_URL` | Backend WebSocket URL | `wss://hedge-api.onrender.com` |

#### **2.4 External API Keys**

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `EIA_API_KEY` | Your EIA API key | Register at https://www.eia.gov/opendata/register.php |
| `CME_API_KEY` | Your CME API key | Register at https://www.cmegroup.com/market-data/api |
| `OPENAI_API_KEY` | Your OpenAI API key | https://platform.openai.com/api-keys |

#### **2.5 Notification & Automation**

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/services/...` | Slack → Apps → Incoming Webhooks → Add to Workspace |
| `GH_PAT` | GitHub Personal Access Token | GitHub → Settings → Developer settings → Personal access tokens → Generate (scope: `repo`, `workflow`) |

### **Step 3: Enable GitHub Pages**

1. **Navigate to**: Repository → Settings → Pages

2. **Source**: Select "GitHub Actions"

3. **Custom domain** (optional): Add your domain and configure DNS

4. **Save**

5. **Note the URL**: `https://<your-username>.github.io/fuel-hedging-platform`

---

## ☁️ RENDER.COM SETUP

### **Step 1: Create Render Account**

1. Go to https://render.com
2. Sign up with GitHub account (recommended)
3. Verify email

### **Step 2: Create PostgreSQL Database**

1. **Render Dashboard** → New → PostgreSQL

2. **Configuration**:
   - **Name**: `hedge-postgres`
   - **Database**: `fuel_hedging`
   - **User**: `fuel_hedging_user` (auto-generated)
   - **Region**: Choose closest to your users (e.g., `Oregon (US West)`)
   - **Plan**: `Starter` ($7/month) or `Free` (prototype only)

3. **Create Database**

4. **Wait for provisioning** (~2 minutes)

5. **Copy connection strings**:
   - Internal: Used by services in same region
   - External: Used by GitHub Actions for migrations

6. **Enable TimescaleDB extension**:
   - Connect via psql: `psql <connection-string>`
   - Run: `CREATE EXTENSION IF NOT EXISTS timescaledb;`
   - Verify: `\dx` (should show timescaledb)

### **Step 3: Create Redis Instance**

1. **Render Dashboard** → New → Redis

2. **Configuration**:
   - **Name**: `hedge-redis`
   - **Region**: Same as PostgreSQL
   - **Plan**: `Free` (25MB) - sufficient for rate limiting

3. **Create Redis**

4. **Copy Internal Connection String** (for API service)

### **Step 4: Create API Web Service**

1. **Render Dashboard** → New → Web Service

2. **Connect Repository**:
   - Select `fuel-hedging-platform` from GitHub

3. **Configuration**:
   - **Name**: `hedge-api`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: `python_engine`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Starter` ($7/month)

4. **Environment Variables** (click "Advanced" → Add Environment Variable):

| Key | Value | Source |
|-----|-------|--------|
| `DATABASE_URL` | (from database) | Render → hedge-postgres → Connect → Internal |
| `REDIS_URL` | (from Redis) | Render → hedge-redis → Connect → Internal |
| `JWT_SECRET_KEY` | (generate new) | Run: `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` | (literal value) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | (literal value) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | (literal value) |
| `EIA_API_KEY` | (your EIA key) | From prerequisites |
| `CME_API_KEY` | (your CME key) | From prerequisites |
| `OPENAI_API_KEY` | (your OpenAI key) | From prerequisites |
| `N8N_WEBHOOK_SECRET` | (generate new) | Run: `openssl rand -hex 32` |
| `FRONTEND_ORIGIN` | (GitHub Pages URL) | `https://<username>.github.io` |
| `ENVIRONMENT` | `production` | (literal value) |
| `LOG_LEVEL` | `INFO` | (literal value) |
| `SENTRY_DSN` | (optional) | Leave empty initially |

5. **Health Check**:
   - **Path**: `/api/v1/health`
   - **Timeout**: 30 seconds

6. **Create Web Service**

7. **Wait for first deploy** (~3-5 minutes)

8. **Copy Service URL**: `https://hedge-api.onrender.com`

### **Step 5: Create N8N Background Worker**

1. **Render Dashboard** → New → Background Worker

2. **Connect Repository**: Same as API

3. **Configuration**:
   - **Name**: `hedge-n8n`
   - **Region**: Same as API
   - **Branch**: `main`
   - **Root Directory**: `n8n`
   - **Build Command**: `npm install`
   - **Start Command**: `npx n8n start`
   - **Plan**: `Starter` ($7/month)

4. **Environment Variables**:

| Key | Value |
|-----|-------|
| `N8N_ENCRYPTION_KEY` | Run: `openssl rand -hex 32` |
| `N8N_BASIC_AUTH_ACTIVE` | `true` |
| `N8N_BASIC_AUTH_USER` | `admin` |
| `N8N_BASIC_AUTH_PASSWORD` | (strong password) |
| `FASTAPI_INTERNAL_URL` | Render internal URL of API |
| `N8N_WEBHOOK_URL` | `https://hedge-n8n.onrender.com` |
| `DATABASE_TYPE` | `postgresdb` |
| `DB_POSTGRESDB_HOST` | (from database) |
| `DB_POSTGRESDB_PORT` | `5432` |
| `DB_POSTGRESDB_DATABASE` | `fuel_hedging` |
| `DB_POSTGRESDB_USER` | (from database) |
| `DB_POSTGRESDB_PASSWORD` | (from database) |

5. **Disk**:
   - Path: `/home/node/.n8n`
   - Size: 1 GB

6. **Create Background Worker**

7. **Wait for first deploy**

8. **Copy Service URL**: `https://hedge-n8n.onrender.com`

### **Step 6: Verify Render Services**

- [ ] **hedge-postgres**: Status = Available
- [ ] **hedge-redis**: Status = Available
- [ ] **hedge-api**: Status = Available, Health check passing
- [ ] **hedge-n8n**: Status = Available

### **Step 7: Run Initial Database Migration**

```bash
# Install Alembic locally
pip install alembic asyncpg

# Set database URL
export DATABASE_URL="<RENDER_DATABASE_URL from secrets>"

# Run migrations
alembic upgrade head

# Verify
psql $DATABASE_URL -c "\dt"  # Should show all tables
```

### **Step 8: Seed Initial Data**

```bash
# Run seed script
python python_engine/app/db/seed.py

# Verify admin user created
psql $DATABASE_URL -c "SELECT email, role FROM users;"
```

**Default admin credentials**:
- Email: `admin@airline.com`
- Password: `Admin123!` (change immediately after first login)

---

## ⚙️ GITHUB ACTIONS CONFIGURATION

### **Step 1: Update GitHub Secrets (continued)**

Now that Render services are created, add the deploy hooks:

1. **Render** → hedge-api → Settings → Deploy Hook
   - Copy URL → GitHub → Secrets → `RENDER_DEPLOY_HOOK_API`

2. **Render** → hedge-n8n → Settings → Deploy Hook
   - Copy URL → GitHub → Secrets → `RENDER_DEPLOY_HOOK_N8N`

### **Step 2: Verify Workflow Files**

Ensure these 5 files exist in `.github/workflows/`:

- [ ] `ci.yml`
- [ ] `deploy-frontend.yml`
- [ ] `deploy-backend.yml`
- [ ] `lstm-retrain.yml`
- [ ] `nightly-validation.yml`

*(These will be created in the next phase of the project)*

### **Step 3: Enable GitHub Actions**

1. **Repository** → Settings → Actions → General

2. **Actions permissions**: Allow all actions

3. **Workflow permissions**: Read and write permissions

4. **Save**

---

## 🚀 FIRST DEPLOYMENT

### **Step 1: Deploy Backend (Manual)**

```bash
# From project root
git add .
git commit -m "Initial production deployment"
git push origin main
```

**This triggers**:
1. `ci.yml` - Runs tests
2. `deploy-backend.yml` - Deploys API to Render
3. `deploy-frontend.yml` - Deploys frontend to GitHub Pages

### **Step 2: Monitor Deployment**

**GitHub Actions**:
- GitHub → Actions tab
- Watch workflows: ci.yml → deploy-backend.yml → deploy-frontend.yml
- All should be green ✅

**Render Logs**:
- Render → hedge-api → Logs
- Look for: `Application startup complete.`
- Look for: `Uvicorn running on http://0.0.0.0:10000`

**Expected Duration**:
- CI: ~3-5 minutes
- Backend Deploy: ~5-7 minutes
- Frontend Deploy: ~2-3 minutes
- **Total**: ~10-15 minutes

### **Step 3: Access Application**

1. **Frontend URL**: https://<your-username>.github.io/fuel-hedging-platform

2. **Backend URL**: https://hedge-api.onrender.com

3. **N8N URL**: https://hedge-n8n.onrender.com (requires basic auth)

---

## ✅ POST-DEPLOYMENT VERIFICATION

### **Automated Checks**

Run the verification script:

```bash
# scripts/verify_deployment.sh
#!/bin/bash

FRONTEND_URL="https://<username>.github.io/fuel-hedging-platform"
BACKEND_URL="https://hedge-api.onrender.com"

echo "🔍 Verifying deployment..."

# Check backend health
echo "Checking backend health..."
HEALTH=$(curl -s $BACKEND_URL/api/v1/health)
if echo $HEALTH | grep -q '"status":"healthy"'; then
  echo "✅ Backend health check passed"
else
  echo "❌ Backend health check failed"
  exit 1
fi

# Check frontend loads
echo "Checking frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL)
if [ $FRONTEND_STATUS -eq 200 ]; then
  echo "✅ Frontend loads successfully"
else
  echo "❌ Frontend failed to load (HTTP $FRONTEND_STATUS)"
  exit 1
fi

# Check database connection
echo "Checking database..."
DB_CONNECTED=$(echo $HEALTH | grep -o '"db_connected":true')
if [ -n "$DB_CONNECTED" ]; then
  echo "✅ Database connection successful"
else
  echo "❌ Database connection failed"
  exit 1
fi

echo ""
echo "🎉 All verification checks passed!"
echo ""
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"
echo ""
echo "Default admin login:"
echo "  Email: admin@airline.com"
echo "  Password: Admin123!"
echo ""
echo "⚠️  Please change the admin password immediately!"
```

### **Manual Verification Checklist**

#### **1. Backend API**

- [ ] Health endpoint returns 200:
  ```bash
  curl https://hedge-api.onrender.com/api/v1/health
  ```

- [ ] Response includes:
  ```json
  {
    "status": "healthy",
    "version": "1.0.0",
    "environment": "production",
    "db_connected": true,
    "redis_connected": true,
    "uptime_seconds": 123
  }
  ```

- [ ] API documentation disabled (should return 404):
  ```bash
  curl https://hedge-api.onrender.com/docs
  ```

#### **2. Frontend**

- [ ] Open: https://<username>.github.io/fuel-hedging-platform
- [ ] Login page loads
- [ ] No console errors in browser DevTools
- [ ] Dark theme applied
- [ ] Logo and branding visible

#### **3. Authentication**

- [ ] Log in with admin credentials:
  - Email: `admin@airline.com`
  - Password: `Admin123!`

- [ ] Redirect to Dashboard after login
- [ ] Sidebar shows all 7 pages (admin has full access)
- [ ] User avatar shows "Admin" with "Admin" role badge

#### **4. Dashboard Functionality**

- [ ] Dashboard page loads
- [ ] KPI cards display (may show "No data" initially - this is normal)
- [ ] Charts render without errors
- [ ] Live price ticker shows connection status

#### **5. Recommendations Page**

- [ ] Page loads
- [ ] Shows "No pending recommendations" (initial state)
- [ ] Approval buttons visible (admin role)

#### **6. Analytics Page**

- [ ] Page loads
- [ ] Hypothesis cards render
- [ ] Charts display axes and legends

#### **7. Other Pages**

- [ ] Positions page loads
- [ ] Audit Log page loads (admin only)
- [ ] Settings page loads (admin only)

#### **8. Logout**

- [ ] Click logout button in sidebar
- [ ] Redirected to login page
- [ ] Cannot access protected pages after logout

---

## 🔧 TROUBLESHOOTING

### **Issue 1: Backend Health Check Fails**

**Symptoms**:
- Render shows service as "Unhealthy"
- Health endpoint returns 500 or times out

**Solutions**:

1. **Check Render Logs**:
   ```
   Render → hedge-api → Logs
   ```

2. **Common Causes**:
   - **Database connection error**: Verify `DATABASE_URL` is correct
   - **Missing environment variable**: Check all required env vars set
   - **Model artifacts missing**: Ensure `models/` directory deployed

3. **Fix**:
   - Update environment variables in Render dashboard
   - Trigger manual deploy: Render → hedge-api → Manual Deploy

### **Issue 2: Frontend Cannot Connect to Backend**

**Symptoms**:
- Login fails with "Network Error"
- Browser console shows CORS error

**Solutions**:

1. **Check CORS Configuration**:
   - Render → hedge-api → Environment Variables
   - Verify `FRONTEND_ORIGIN` matches GitHub Pages URL exactly
   - Should be `https://<username>.github.io` (no trailing slash)

2. **Check API URL**:
   - GitHub → Settings → Secrets → `VITE_API_BASE_URL`
   - Should be `https://hedge-api.onrender.com` (no trailing slash)

3. **Re-deploy Frontend**:
   ```bash
   git commit --allow-empty -m "Trigger frontend re-deploy"
   git push origin main
   ```

### **Issue 3: N8N Workflow Fails**

**Symptoms**:
- No recommendations generated
- N8N execution shows error

**Solutions**:

1. **Check N8N Logs**:
   ```
   Render → hedge-n8n → Logs
   ```

2. **Common Causes**:
   - **API keys invalid**: Check `EIA_API_KEY`, `CME_API_KEY`, `OPENAI_API_KEY`
   - **FastAPI unreachable**: Verify `FASTAPI_INTERNAL_URL` uses Render internal network
   - **Webhook secret mismatch**: Ensure `N8N_WEBHOOK_SECRET` same in both services

3. **Manual Test**:
   - Open N8N UI: https://hedge-n8n.onrender.com
   - Log in with basic auth
   - Workflows → fuel_hedge_advisor_v2 → Execute Workflow
   - Check which node fails

### **Issue 4: Database Migration Fails**

**Symptoms**:
- `deploy-backend.yml` fails at migration step
- Render service won't start

**Solutions**:

1. **Check Migration Logs**:
   ```
   GitHub → Actions → deploy-backend.yml → migrate job
   ```

2. **Common Causes**:
   - **Schema drift**: Database schema doesn't match migration
   - **Connection timeout**: Database unreachable

3. **Manual Migration**:
   ```bash
   export DATABASE_URL="<RENDER_DATABASE_URL>"
   alembic current  # Check current version
   alembic upgrade head  # Apply migrations
   ```

4. **If Stuck**:
   - Restore from backup (see RUNBOOK.md)
   - Or: Drop and recreate database (LAST RESORT)

### **Issue 5: GitHub Actions Workflow Fails**

**Symptoms**:
- Red X on commit in GitHub
- Workflow fails at specific step

**Solutions**:

1. **Check Workflow Logs**:
   ```
   GitHub → Actions → Click failed workflow → Click failed job
   ```

2. **Common Causes**:
   - **Missing secret**: Add missing secret in GitHub Settings
   - **Syntax error**: Check YAML syntax
   - **Dependency error**: Update `requirements.txt` or `package.json`

3. **Test Locally**:
   ```bash
   # Install act (GitHub Actions local runner)
   brew install act  # macOS
   # OR
   choco install act  # Windows

   # Run workflow locally
   act -j backend-tests
   ```

---

## 🔄 UPDATING CONFIGURATION

### **Update Environment Variables**

**Backend (Render)**:
1. Render → hedge-api → Environment
2. Click "Edit" on variable
3. Update value
4. Click "Save Changes"
5. Render auto-restarts service

**Frontend (GitHub)**:
1. GitHub → Settings → Secrets → Actions
2. Click on secret name
3. Click "Update secret"
4. Enter new value
5. Trigger frontend re-deploy

### **Update Constraint Limits**

Via frontend UI (preferred):
1. Log in as admin
2. Settings → Constraints
3. Update values
4. Save changes

### **Add New User**

Via frontend UI:
1. Log in as admin
2. Settings → User Management
3. Click "Add User"
4. Fill form → Create

---

## 📊 MONITORING

### **Set Up Monitoring**

1. **Slack Notifications**:
   - Already configured via `SLACK_WEBHOOK_URL`
   - Alerts go to #fuel-hedging-alerts channel

2. **Render Monitoring**:
   - Render → hedge-api → Metrics
   - Monitor: CPU, Memory, Response Time, Error Rate

3. **GitHub Actions**:
   - Configure email notifications: GitHub → Settings → Notifications

4. **Nightly Validation**:
   - Runs Mon-Fri at 23:00 UTC
   - Checks all KPIs against thresholds
   - Posts to Slack

---

## ✅ DEPLOYMENT COMPLETE!

### **Next Steps**

1. **Change Admin Password**:
   - Log in with default credentials
   - Settings → User Management → Reset Password

2. **Add Team Members**:
   - Settings → User Management → Add User
   - Assign appropriate roles

3. **Configure N8N Workflow**:
   - Log in to N8N UI
   - Import workflow: n8n/workflows/fuel_hedge_advisor_v2.json
   - Activate workflow

4. **Set Up Monitoring Alerts**:
   - Test Slack webhook
   - Configure PagerDuty (optional)

5. **Run First Pipeline**:
   - N8N → fuel_hedge_advisor_v2 → Execute Workflow
   - Verify recommendation created
   - Dashboard shows new data

6. **Schedule Weekly LSTM Retrain**:
   - Verify `lstm-retrain.yml` runs Sunday 02:00 UTC
   - Check Slack for retrain notifications

### **Documentation**

- **Operations**: See `RUNBOOK.md`
- **Security**: See `SECURITY_CHECKLIST.md`
- **Testing**: See `TESTING_GUIDE.md`

---

## 💰 COST BREAKDOWN

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| GitHub Pages | Free | $0 |
| Render - PostgreSQL | Starter | $7 |
| Render - Redis | Free | $0 |
| Render - API Web Service | Starter | $7 |
| Render - N8N Worker | Starter | $7 |
| **TOTAL** | | **$21/month** |

**Free Tier Limitations**:
- Render Free plan: Services sleep after 15 min inactivity
- Not recommended for production
- Use Starter plan minimum for production

**Scaling Up**:
- Standard plan: $25/service (more resources)
- Pro plan: $85/service (dedicated instances)
- Custom: Enterprise plans available

---

## 📞 SUPPORT

If you encounter issues not covered in this guide:

- **Documentation**: Check `RUNBOOK.md` for operational procedures
- **Issues**: Open GitHub issue with deployment logs
- **Slack**: #fuel-hedging-support
- **Email**: platform-admin@airline.com

---

**Deployment Guide Version**: 1.0  
**Last Updated**: March 3, 2026  
**Next Review**: After successful production deployment

---

**END OF DEPLOYMENT GUIDE**
