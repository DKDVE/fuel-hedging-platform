# Fuel Hedging Platform — Render Deployment

---

## Add n8n to existing Render setup

Use this when **hedge-api, hedge-postgres, hedge-redis** already run on Render and you only need to add n8n.

### 1. Create hedge-n8n web service

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Web Service**
2. **Connect repository:** Choose **Existing Image**
3. **Image URL:** `docker.io/n8nio/n8n:latest`
4. **Name:** `hedge-n8n`
5. **Region:** Same as hedge-api (required for internal networking)
6. **Instance Type:** Starter (or Free for testing; Free spins down after 15 min)

### 2. Add disk

1. **Disks** → **Add Disk**
2. **Name:** `n8n-data`
3. **Mount Path:** `/home/node/.n8n`
4. **Size:** 1 GB

### 3. Environment variables

In **Environment** → **Add Environment Variable**:

| Key | Value |
|-----|-------|
| `PORT` | `5678` |
| `N8N_PROXY_HOPS` | `1` (required for Render — fixes X-Forwarded-For / trust proxy error) |
| `N8N_API_KEY` | Same value as `N8N_WEBHOOK_SECRET` in hedge-api |
| `N8N_ENCRYPTION_KEY` | Generate: `openssl rand -hex 16` |
| `N8N_SECURE_COOKIE` | `false` |
| `OPENAI_API_KEY` | Your OpenAI key (optional) |
| `FASTAPI_INTERNAL_URL` | From **hedge-api** → **Info** → **Internal URL** (e.g. `http://hedge-api:10000`) |
| `WEBHOOK_URL` | Leave blank for now; set after first deploy (see step 6) |

### 4. Link hedge-api to hedge-n8n

1. Open **hedge-api** → **Environment**
2. Add variable: **Key** `N8N_INTERNAL_URL`, **Value** = one of:
   - **Option A (internal):** hedge-n8n → **Connect** → **Internal** tab → copy the address (e.g. `http://hedge-n8n-xxxx:5678`). Both services must be in the **same region**.
   - **Option B (public, always works):** `https://hedge-n8n.onrender.com` (use your actual hedge-n8n public URL, no trailing slash)
3. Save (hedge-api will redeploy)

### 5. Deploy hook and GitHub secret

1. **hedge-n8n** → **Settings** → **Deploy Hook** → copy URL
2. GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
3. **Name:** `RENDER_DEPLOY_HOOK_N8N`, **Value:** the deploy hook URL

The **Deploy Backend** workflow already includes a `deploy-n8n` job. Once this secret is set, every push to `main` will deploy both hedge-api and hedge-n8n.

### 6. After first deploy

1. Get hedge-n8n URL from the dashboard (e.g. `https://hedge-n8n-xxxx.onrender.com`)
2. **hedge-n8n** → **Environment** → add `WEBHOOK_URL` = that URL
3. Redeploy hedge-n8n
4. Open the n8n URL → **Workflows** → **Import** → `n8n/workflows/fuel_hedge_advisor_v2.json`
5. Add OpenAI credential, then **Activate** the workflow

---

## Full Blueprint deployment (fresh setup)

Step-by-step guide to deploy the full stack via Render Blueprint.

---

## Prerequisites

- [Render](https://render.com) account
- GitHub repo connected to Render
- OpenAI API key (for n8n AI agents; optional — platform works without it)

---

## Step 1: Create Blueprint

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Blueprint**
3. Connect your GitHub account if not already connected
4. Select the **fuel-hedging-platform** repository
5. Render will detect `render.yaml` and show the services to create:
   - **hedge-api** (web)
   - **hedge-n8n** (worker)
   - **hedge-postgres** (database)
   - **hedge-redis** (redis)
6. Choose a name for the Blueprint (e.g. `fuel-hedging-platform`)
7. Select the same **region** for all services (required for internal networking)
8. Click **Apply**

---

## Step 2: Set Secrets (Required Before First Deploy)

All services with `sync: false` require manual secret values. Set these in the Render dashboard **before** the first deploy.

### hedge-api

| Secret | Where to get it | Notes |
|--------|-----------------|-------|
| `SECRET_KEY` | Generate: `openssl rand -hex 32` | JWT signing; min 32 chars |
| `N8N_WEBHOOK_SECRET` | Generate: `openssl rand -hex 24` | Must match `N8N_API_KEY` in hedge-n8n |
| `OPENAI_API_KEY` | [OpenAI](https://platform.openai.com/api-keys) | Optional; for n8n AI agents |
| `EIA_API_KEY` | [EIA](https://www.eia.gov/opendata/register.php) | Optional; for live fuel prices |

**How to set:** hedge-api → **Environment** → find keys with "secret" icon → paste values

### hedge-n8n

| Secret | Value | Notes |
|--------|-------|-------|
| `N8N_API_KEY` | Same as `N8N_WEBHOOK_SECRET` | Must match FastAPI |
| `OPENAI_API_KEY` | Same as hedge-api | For AI agents in workflow |
| `N8N_ENCRYPTION_KEY` | Generate: `openssl rand -hex 16` | Encrypts n8n credentials |
| `WEBHOOK_URL` | `https://hedge-n8n-<your-id>.onrender.com` | **Set after first deploy** — use your hedge-n8n public URL from Render dashboard |

**Note:** hedge-n8n is a **web service** so it can receive HTTP triggers from the API and expose the n8n UI for workflow import.

---

## Step 3: Get Deploy Hooks

After the Blueprint creates the services:

1. **hedge-api** → **Settings** → **Deploy Hook** → copy URL
2. **hedge-n8n** → **Settings** → **Deploy Hook** → copy URL (if available)

---

## Step 4: Add GitHub Secrets

In your repo: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Value |
|--------|-------|
| `RENDER_DATABASE_URL` | hedge-postgres → **Connect** → **External Database URL** |
| `RENDER_DEPLOY_HOOK_API` | hedge-api Deploy Hook URL |
| `RENDER_DEPLOY_HOOK_N8N` | hedge-n8n Deploy Hook URL (optional) |

**Important:** Convert the database URL for asyncpg before using in migrations. The deploy workflow does this automatically. Use the URL exactly as shown in Render (it may be `postgres://` or `postgresql://`).

---

## Step 5: Import n8n Workflow

After hedge-n8n is running:

1. Get the n8n URL from **hedge-n8n** → top of the page (e.g. `https://hedge-n8n-xxxx.onrender.com`)
2. Set `WEBHOOK_URL` in hedge-n8n Environment to that URL (if not already set)
3. **Workflow import:**
   - Open the n8n URL in your browser
   - **Workflows** → **Import from file** → select `n8n/workflows/fuel_hedge_advisor_v2.json` (from the repo)
   - Add **OpenAI** credential: **Credentials** → **New** → **OpenAI API** → paste your key
   - **Activate** the workflow (toggle in top-right)

---

## Step 6: Trigger First Deploy

1. Push to `main` (or run the **Deploy Backend** workflow manually)
2. The workflow will:
   - Run migrations
   - Deploy hedge-api via deploy hook
   - Deploy hedge-n8n via deploy hook (if `RENDER_DEPLOY_HOOK_N8N` is set)
3. Wait for health check: `https://hedge-api-o9t3.onrender.com/health` (or your API URL)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| hedge-api 500 on login | Ensure `DATABASE_URL` is set (from hedge-postgres link) |
| Cookies not sent (401 after login) | `SameSite=None` is set for production; verify `FRONTEND_ORIGIN` |
| n8n not found | Ensure `RENDER_DEPLOY_HOOK_N8N` is set and hedge-n8n exists |
| `n8n_trigger_failed` "Name or service not known" | `N8N_INTERNAL_URL` must be the **exact** URL from hedge-n8n dashboard (top of page). Render URLs include a random suffix, e.g. `https://hedge-n8n-abc123.onrender.com` — not `hedge-n8n.onrender.com` |
| Migrations fail | Use External Database URL; allow `0.0.0.0/0` in Postgres Networking for GitHub Actions |
| CSV not found | Data is at `/app/data/`; ensure `data/fuel_hedging_dataset.csv` is in repo |

---

## Service URLs (After Deploy)

| Service | URL |
|---------|-----|
| hedge-api | `https://hedge-api-<your-id>.onrender.com` |
| hedge-n8n | `https://hedge-n8n-<your-id>.onrender.com` |
| hedge-postgres | Internal connection string (from dashboard) |
| hedge-redis | Internal connection string (from dashboard) |
