# Deployment Guide — Fuel Hedging Platform

**Render (Backend) + GitHub Pages (Frontend)**  
**Repository:** https://github.com/DKDVE/fuel-hedging-platform

---

## Overview

You need to complete 4 manual steps in this order:

1. Generate secret values (terminal — 2 min)
2. Create Render services and get deploy hooks (Render dashboard — 10 min)
3. Add all GitHub Secrets (GitHub dashboard — 5 min)
4. Enable GitHub Pages and trigger first deploy (GitHub dashboard — 2 min)

Total time: ~20 minutes of clicking. Then CI/CD handles everything automatically.

---

## STEP 1 — Generate Secret Values (do this first, save them)

Open a terminal and run each command. Copy the output — you'll need it in Steps 2 and 3.

```bash
# JWT secret key (for cookie signing)
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"

# n8n webhook secret (must be DIFFERENT from JWT key)
echo "N8N_WEBHOOK_SECRET=$(openssl rand -hex 32)"

# n8n encryption key (must be exactly 32 chars)
echo "N8N_ENCRYPTION_KEY=$(openssl rand -hex 16)"

# GitHub PAT — generate this at:
# https://github.com/settings/tokens/new
# Scopes needed: repo (full), workflow
# Name it: fuel-hedging-deploy
# Expiry: 90 days
```

Save all four values somewhere safe (password manager). You will need them in the next steps.

---

## STEP 2 — Create Render Services

Go to https://dashboard.render.com

### 2A. Create the PostgreSQL database

1. Click **New → PostgreSQL**
2. Fill in:
   - Name: `hedge-postgres`
   - Database: `hedge_db`
   - User: `hedge_user`
   - Region: Oregon (US West) — or closest to you
   - Plan: **Starter ($7/mo)**
3. Click **Create Database**
4. Wait ~2 minutes for it to provision
5. Once ready, click on `hedge-postgres` → copy the **External Database URL** (starts with `postgresql://`)
   → Save this as `RENDER_DATABASE_URL`

### 2B. Create the Redis instance

1. Click **New → Redis**
2. Fill in:
   - Name: `hedge-redis`
   - Plan: **Free**
   - Region: same as your PostgreSQL
3. Click **Create Redis**

### 2C. Create the FastAPI web service

1. Click **New → Web Service**
2. Connect your GitHub repo: `DKDVE/fuel-hedging-platform`
3. Fill in:
   - Name: `hedge-api`
   - Region: same as database
   - Branch: `main`
   - Runtime: **Docker**
   - Dockerfile Path: `python_engine/Dockerfile.prod`
   - Docker Context: `.` (the root of the repo)
   - Plan: **Starter ($7/mo)**
4. Under **Environment Variables**, add these one by one:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | (click "From Database" → select `hedge-postgres` → `Internal Database URL`) |
   | `REDIS_URL` | (click "From Redis" → select `hedge-redis` → `Internal Redis URL`) |
   | `SECRET_KEY` | (paste the JWT_SECRET_KEY value you generated in Step 1) |
   | `N8N_WEBHOOK_SECRET` | (paste the n8n webhook secret from Step 1) |
   | `ENVIRONMENT` | `production` |
   | `LOG_LEVEL` | `INFO` |
   | `FRONTEND_ORIGIN` | `https://dkdve.github.io` |
   | `N8N_TRIGGER_PATH` | `/webhook/fuel-hedge-trigger` |
   | `OPENAI_API_KEY` | (your OpenAI key, or leave empty) |
   | `EIA_API_KEY` | (your EIA key, or leave empty) |

5. Under **Health Check Path**: enter `/health`
6. Under **Auto-Deploy**: set to **No** (CI controls deploys)
7. Click **Create Web Service**
8. Wait for the first deploy to complete (it will probably fail — that's OK, we need the deploy hook URL first)
9. Once the service is created, go to **Settings → Deploy Hook**
   → Copy the deploy hook URL → Save this as `RENDER_DEPLOY_HOOK_API`

### 2D. Create the n8n worker service

1. Click **New → Background Worker**
2. Connect your GitHub repo: `DKDVE/fuel-hedging-platform`
3. Fill in:
   - Name: `hedge-n8n`
   - Region: same as above
   - Branch: `main`
   - Runtime: **Docker**
   - Docker Image URL: `docker.io/n8nio/n8n:latest`
   - Plan: **Starter ($7/mo)**
4. Under **Environment Variables**, add:

   | Key | Value |
   |-----|-------|
   | `N8N_API_KEY` | (same value as `N8N_WEBHOOK_SECRET` from Step 1) |
   | `N8N_ENCRYPTION_KEY` | (paste the value you generated in Step 1) |
   | `N8N_SECURE_COOKIE` | `false` |
   | `OPENAI_API_KEY` | (your OpenAI key, or leave empty) |
   | `FASTAPI_INTERNAL_URL` | `https://hedge-api.onrender.com` |
   | `WEBHOOK_URL` | `https://hedge-n8n.onrender.com` (use your actual n8n service URL once created) |

5. Under **Disk**:
   - Click **Add Disk**
   - Mount Path: `/home/node/.n8n`
   - Size: `1 GB`
6. Under **Auto-Deploy**: set to **No**
7. Click **Create Background Worker**
8. Once created, go to **Settings → Deploy Hook**
   → Copy the URL → Save this as `RENDER_DEPLOY_HOOK_N8N`

---

## STEP 3 — Add GitHub Secrets

Go to https://github.com/DKDVE/fuel-hedging-platform/settings/secrets/actions

Click **New repository secret** for each row:

| Secret Name | Value |
|-------------|-------|
| `RENDER_DEPLOY_HOOK_API` | The deploy hook URL from Step 2C |
| `RENDER_DEPLOY_HOOK_N8N` | The deploy hook URL from Step 2D |
| `RENDER_DATABASE_URL` | The External DB URL from Step 2A |
| `JWT_SECRET_KEY` | The value you generated in Step 1 |
| `N8N_WEBHOOK_SECRET` | The value you generated in Step 1 |
| `VITE_API_BASE_URL` | `https://hedge-api.onrender.com` |
| `VITE_WS_URL` | `wss://hedge-api.onrender.com` |
| `VITE_BASE_PATH` | `/fuel-hedging-platform/` |
| `GH_PAT` | The GitHub PAT you created in Step 1 |
| `EIA_API_KEY` | Your EIA key (or skip — platform works without it) |
| `OPENAI_API_KEY` | Your OpenAI key (or skip — demo mode works without it) |
| `SLACK_WEBHOOK_URL` | Your Slack webhook (or skip — nightly alerts will be skipped) |

---

## STEP 4 — Enable GitHub Pages

1. Go to https://github.com/DKDVE/fuel-hedging-platform/settings/pages
2. Under **Source**: select **GitHub Actions**
3. Click **Save**

That's it. GitHub Pages will be deployed automatically by `deploy-frontend.yml`
on the next push to main.

---

## STEP 5 — Trigger First Deployment

Now that all secrets are set, trigger the CI/CD pipeline:

```bash
# In your local repo directory
git commit --allow-empty -m "ci: trigger first production deployment"
git push origin main
```

Then watch the Actions tab: https://github.com/DKDVE/fuel-hedging-platform/actions

You should see 3 workflows start:
- `CI` — runs tests + security scan (~3-5 min)
- `Deploy Backend` — waits for CI, runs migrations, deploys to Render (~8-10 min)
- `Deploy Frontend` — builds React app, deploys to GitHub Pages (~2-3 min)

**Expected outcome:**
- GitHub Pages URL live: `https://dkdve.github.io/fuel-hedging-platform`
- Render API healthy: `https://hedge-api.onrender.com/health` → `{"status":"healthy"}`

---

## STEP 6 — Seed Production Database (one-time)

Once the API is deployed and healthy, seed the analytics history:

1. Go to https://dashboard.render.com → `hedge-api` → **Shell** tab
2. Run:
```bash
python scripts/seed_analytics_history.py
```
Expected output: `52 analytics runs inserted`

This gives the dashboard real data to display from day one.

---

## STEP 7 — Import n8n Workflow (if using OpenAI)

If you have an OpenAI API key:

1. Open your n8n service URL (shown in Render dashboard for `hedge-n8n`)
2. Go to **Settings → Import from file**
3. Upload `n8n/workflows/fuel_hedge_advisor_v2.json`
4. Go to **Credentials → New → OpenAI API** → paste your key → Save
5. Open the imported workflow → toggle it **Active** (top right)
6. Test: log into the platform as admin → Dashboard → **Run Pipeline**

If you don't have OpenAI: use the demo recommendation script instead:
```bash
# From your local machine (requires the API to be running)
bash scripts/create_test_recommendation.sh
```

---

## What Your URLs Will Be

| Service | URL |
|---------|-----|
| Frontend (GitHub Pages) | `https://dkdve.github.io/fuel-hedging-platform` |
| API (Render) | `https://hedge-api.onrender.com` |
| API health check | `https://hedge-api.onrender.com/health` |
| API docs (Swagger) | `https://hedge-api.onrender.com/docs` |
| n8n (Render) | `https://hedge-n8n.onrender.com` |

---

## Vite Base Path Fix

**Important:** Because the frontend is deployed to a GitHub Pages subdirectory
(`/fuel-hedging-platform/`), the Vite build needs to know the base path.

In your local repo, check `frontend/vite.config.ts`. It should already have:
```typescript
base: process.env.VITE_BASE_PATH || '/',
```

If it doesn't, add it. The `VITE_BASE_PATH` GitHub Secret (`/fuel-hedging-platform/`)
injects this at build time so all assets load from the correct path.

Also check `frontend/src/App.tsx` — if using React Router with `BrowserRouter`,
you need to add the basename:
```typescript
<BrowserRouter basename={import.meta.env.BASE_URL}>
```

This ensures `/recommendations` routes correctly to
`/fuel-hedging-platform/recommendations` on GitHub Pages.

---

## Render Cold Start Warning

Render Starter plan services spin down after 15 minutes of inactivity and take
~30-50 seconds to cold-start on the next request. This affects the demo experience.

**Options:**
1. Accept it — fine for a portfolio project
2. Keep the service warm with a free uptime monitor (UptimeRobot pings `/health`
   every 5 minutes):
   - Go to https://uptimerobot.com → New Monitor → HTTP(s)
   - URL: `https://hedge-api.onrender.com/health`
   - Interval: 5 minutes
   - This keeps the service warm at no cost

---

## Monthly Cost Breakdown

| Service | Plan | Cost |
|---------|------|------|
| hedge-api (FastAPI) | Starter | $7/mo |
| hedge-postgres | Starter | $7/mo |
| hedge-n8n (worker) | Starter | $7/mo |
| hedge-redis | Free | $0 |
| Frontend (GitHub Pages) | Free | $0 |
| **Total** | | **$21/mo** |

---

## Troubleshooting

**CI fails on "backend-tests" — alembic can't connect to test postgres:**
The GitHub Actions service container needs to be healthy before alembic runs.
The `--health-cmd pg_isready` option handles this. If it still fails, check that
the test DATABASE_URL in ci.yml matches the service container credentials exactly.

**Deploy Backend fails — "API did not become healthy":**
1. Check Render dashboard → hedge-api → Logs
2. Most common causes:
   - Missing env var: the API crashes on startup with `ValueError: missing config`
   - Dockerfile.prod path wrong: check `dockerfilePath` in render.yaml matches actual file
   - Database not ready: the health poller waits up to 10 min, usually enough
3. Fix the issue in Render dashboard → manual deploy → watch logs

**Frontend loads but API calls fail (CORS error):**
The `FRONTEND_ORIGIN` env var on Render must exactly match the GitHub Pages URL.
Check: Render dashboard → hedge-api → Environment → `FRONTEND_ORIGIN`
It must be `https://dkdve.github.io` (no trailing slash, no path).

**GitHub Pages shows blank page or 404 on route:**
This is the React Router + GitHub Pages compatibility issue.
The `basename` fix in Step 7 above resolves it.
Also check: the `404.html` workaround for SPA routing on GitHub Pages may be needed:
Create `frontend/public/404.html` that redirects to `index.html` with the path
encoded as a query string. Search "github pages spa redirect" for the standard solution.

**n8n workflow isn't receiving pipeline triggers:**
1. Check the n8n service is running (Render dashboard → hedge-n8n → status)
2. Check `N8N_WEBHOOK_SECRET` in Render matches `N8N_WEBHOOK_SECRET` in the API env vars
3. Check `FASTAPI_INTERNAL_URL` in n8n env vars points to the correct API URL
4. Check the workflow is Active in n8n UI (green toggle)

---

## Security Post-Deploy Checklist

- [ ] `git log --oneline -5` shows no commit with "password", "secret", or "key" in message
- [ ] https://github.com/DKDVE/fuel-hedging-platform has no `.env` file in the file browser
- [ ] All 12 GitHub Secrets visible in Settings → Secrets → Actions
- [ ] Render env vars for `SECRET_KEY` and `N8N_WEBHOOK_SECRET` are set to unique generated values
- [ ] EIA API key rotated if it was ever accidentally committed (check git log)
- [ ] `https://hedge-api.onrender.com/docs` does NOT expose internal endpoints (test-n8n-trigger should be 404 in production)

---

*Deployment guide v1.0 — Aviation Fuel Hedging Platform*
*Repo: https://github.com/DKDVE/fuel-hedging-platform*
