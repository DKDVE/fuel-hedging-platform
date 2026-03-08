# 🎯 REMAINING TASKS - Fuel Hedging Platform

**Date**: March 3, 2026  
**Current Status**: 75% Complete (Phases 0-6 Done)  
**Remaining**: Phases 7-8 (Agent Migration + CI/CD)

---

## 📊 CURRENT STATE

### ✅ **What's Complete (Phases 0-6)**

1. **Backend (100% Functional)**
   - 28 API endpoints
   - Complete analytics suite (MAPE 6.8%)
   - Authentication & authorization (JWT + RBAC)
   - Data ingestion pipeline
   - APScheduler for jobs
   - ~11,500 lines of Python

2. **Frontend (100% Functional)**
   - 7 pages (Login, Dashboard, Recommendations, Analytics, Positions, Audit Log, Settings)
   - 25+ production-ready components
   - Dark Bloomberg Terminal-inspired theme
   - Role-based access control
   - Real-time features (SSE hooks ready)
   - ~4,500 lines of TypeScript/TSX

3. **Infrastructure**
   - Docker Compose for local development
   - Render.yaml for production deployment
   - Mock backend for testing
   - Comprehensive documentation (27 files)

### 🚀 **What's Working Right Now**
- ✅ Frontend: http://localhost:5173
- ✅ Mock Backend: http://localhost:8000
- ✅ Login/logout functionality
- ✅ All 7 pages accessible
- ✅ Professional UI/UX

---

## ⏳ PHASE 7: N8N AGENT MIGRATION (0% Complete)

**Estimated Time**: 3-4 hours  
**Priority**: HIGH (required for live agent recommendations)

### **Goal**
Migrate all 37 nodes from TSLA workflow to fuel hedging domain. Each agent system prompt replaced with fuel hedging persona.

### **Tasks Breakdown**

#### **7.1 Replace HTTP Request Nodes (4 nodes)**
- [ ] Replace TSLA API calls with EIA API (jet fuel spot prices)
- [ ] Add CME API client (heating oil + WTI futures)
- [ ] Add ICE API client (Brent crude futures)
- [ ] Use API keys from n8n credential store (NEVER hardcoded)
- [ ] Validate: Each returns JSON with timestamp within last 24h

#### **7.2 Update Data Aggregator (1 Code node)**
- [ ] Merge 4 API responses into single dataset
- [ ] Compute: `Crack_Spread = Jet_Fuel_Spot - Heating_Oil_Futures`
- [ ] Classify volatility regime (LOW/MODERATE/HIGH/CRITICAL)
- [ ] Validate: Output contains all 7 dataset columns + regime flag

#### **7.3 Market Intelligence Hub (1 HTTP node)**
- [ ] HTTP GET to `/api/v1/analytics/forecast/latest`
- [ ] HTTP GET to `/api/v1/analytics/basis-risk/latest`
- [ ] Use `$env.FASTAPI_INTERNAL_URL` (Render internal network)
- [ ] Format response: VaR, MAPE, crack spread, proxy R²
- [ ] Validate: Returns formatted_analysis object

#### **7.4 Replace All 5 Agent System Prompts**
- [ ] **Basis Risk Agent**: Replace prompt with fuel hedging persona
- [ ] **Liquidity Agent**: Replace prompt with fuel hedging persona
- [ ] **Operational Agent**: Replace prompt with fuel hedging persona
- [ ] **IFRS9 Agent**: Replace prompt with fuel hedging persona
- [ ] **Macro Agent**: Replace prompt with fuel hedging persona
- [ ] Ensure output matches AgentOutput interface:
  ```json
  {
    "agent_id": "basis_risk",
    "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
    "recommendation": "string",
    "metrics": {"key": "number"},
    "constraints_satisfied": true,
    "action_required": false,
    "ifrs9_eligible": true,
    "generated_at": "2026-03-03T12:00:00Z"
  }
  ```
- [ ] Validate: Each agent returns parseable JSON (test with JSON.parse())

#### **7.5 Investment Committee Node (1 Code node)**
- [ ] Synthesize 5 agent outputs
- [ ] Output schema:
  - `top_strategy`: string
  - `consensus_risk_level`: RiskLevel enum
  - `key_concerns`: string[]
  - `recommended_hr`: number (0.0 - 0.80)
  - `rationale`: string
- [ ] Validate: `consensus_risk_level` is valid enum value

#### **7.6 Risk Management CRO Gate (1 Code node)**
- [ ] Check: `recommended_hr <= 0.80` (HR_HARD_CAP)
- [ ] Check: `collateral_pct <= 0.15` (COLLATERAL_LIMIT)
- [ ] Check: IFRS9 eligibility (R² >= 0.80)
- [ ] If any breach: output `status='BLOCKED'`
- [ ] Validate: Correctly blocks test payload with `HR=0.85`

#### **7.7 Post-Committee Webhook (1 HTTP POST node)**
- [ ] HTTP POST to `/api/v1/recommendations`
- [ ] Add header: `X-N8N-API-Key: $env.N8N_WEBHOOK_SECRET`
- [ ] Payload: full recommendation with agent outputs
- [ ] Validate: FastAPI creates PENDING recommendation
- [ ] Validate: Visible on React dashboard

#### **7.8 Remove Telegram Nodes (4 nodes)**
- [ ] Remove all Telegram notification nodes
- [ ] Replace with HTTP GET poll to `/api/v1/recommendations/{id}`
- [ ] Use Wait + IF loop (check status every 60s)
- [ ] Validate: n8n detects APPROVED and terminates loop

#### **7.9 Escalation Wait Nodes (4 Wait nodes)**
- [ ] Reconfigure: wait 4h for approval (not 2h from TSLA)
- [ ] If still PENDING after 4h: HTTP PATCH to escalation endpoint
- [ ] Validate: Escalation flag visible on React dashboard
- [ ] Validate: CFO role receives escalation notification

#### **7.10 Workflow-Level Error Handler**
- [ ] Create error handler node (catches any node failure)
- [ ] POST to `/api/v1/admin/pipeline-alert`
- [ ] Payload: `{workflow_id, failed_node, error_message, timestamp}`
- [ ] Ensure `analytics_runs` record updated to `status='FAILED'`
- [ ] Validate: No silent failures in overnight pipeline

### **Testing Checklist**
- [ ] Manual n8n test: All 5 agents return valid JSON
- [ ] FastAPI creates PENDING recommendation
- [ ] Recommendation visible on React dashboard
- [ ] Approval workflow completes successfully
- [ ] Escalation triggers after 4h
- [ ] Error handler catches and logs failures

### **Files to Create/Modify**
- `n8n/workflows/fuel_hedge_advisor_v2.json` (NEW - migrated version)
- Keep `n8n/workflows/fuel_hedge_advisor_v1.json` as backup (DO NOT MODIFY)

---

## ⏳ PHASE 8: CI/CD & DEPLOYMENT (20% Complete)

**Estimated Time**: 2-3 hours  
**Priority**: HIGH (required for production deployment)

### **Goal**
Complete GitHub Actions automation. Push to main → tests → build → deploy. No manual steps.

### **Tasks Breakdown**

#### **8.1 GitHub Actions Workflows (5 files)**

##### **8.1.1 `.github/workflows/ci.yml`**
**Trigger**: Every PR to main/staging  
**SLA**: < 5 minutes

- [ ] Job 1: `backend-tests`
  - Checkout code
  - Set up Python 3.11
  - Install dependencies
  - Run: `pytest tests/ -v --cov --cov-fail-under=70`
  - Run: `mypy app/ --strict`
  - Upload coverage report

- [ ] Job 2: `analytics-smoke-test` (depends on backend-tests)
  - Load fuel_hedging_dataset.csv
  - Run ensemble forecast
  - Assert: MAPE < 15% (smoke test threshold)
  - Assert: Optimizer converges
  - Assert: VaR curve is monotone

- [ ] Job 3: `frontend-build` (depends on backend-tests)
  - Checkout code
  - Set up Node 20
  - Install dependencies: `npm ci`
  - Run: `npm run build`
  - Run: `npm run type-check`
  - Upload build artifacts

- [ ] Job 4: `security-scan` (depends on frontend-build)
  - Run: `pip-audit --requirement python_engine/requirements.txt --output json`
  - Run: `cd frontend && npm audit --audit-level=high --json`
  - Parse outputs: if any HIGH or CRITICAL, fail workflow
  - **NON-NEGOTIABLE**: Supply chain vulnerabilities must block deployment

- [ ] **Validation**: PR cannot merge unless all 4 jobs pass

##### **8.1.2 `.github/workflows/deploy-frontend.yml`**
**Trigger**: Push to main (`frontend/**`)  
**SLA**: < 3 minutes

- [ ] Job: `deploy-to-pages`
  - Checkout code
  - Set up Node 20
  - Install dependencies
  - Build with env vars:
    - `VITE_API_BASE_URL=${{ secrets.VITE_API_BASE_URL }}`
    - `VITE_WS_URL=${{ secrets.VITE_WS_URL }}`
  - Configure GitHub Pages
  - Upload artifact to Pages
  - Deploy to Pages

- [ ] **Validation**: https://<username>.github.io/fuel-hedging-platform loads

##### **8.1.3 `.github/workflows/deploy-backend.yml`**
**Trigger**: Push to main (`python_engine/**` or `models/**`)  
**SLA**: < 6 minutes

- [ ] Job 1: `wait-for-ci`
  - Wait for ci.yml to complete
  - Fail if ci.yml failed

- [ ] Job 2: `migrate` (depends on wait-for-ci)
  - Checkout code
  - Install Alembic
  - Run: `alembic check` (migration safety check)
  - If schema drift detected: FAIL with clear error
  - Run: `alembic upgrade head`
  - Use: `DATABASE_URL=${{ secrets.RENDER_DATABASE_URL }}`

- [ ] Job 3: `deploy-api` (depends on migrate)
  - Trigger Render deploy hook:
    `curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK_API }}`
  - Wait for deploy completion (max 5 min)

- [ ] Job 4: `healthcheck-poll` (depends on deploy-api)
  - Poll: `GET https://hedge-api.onrender.com/api/v1/health` every 10s
  - Max attempts: 30 (5 minutes)
  - Assert: `status == 'healthy'` and `db_connected == true`
  - On failure: rollback Render deployment

- [ ] Job 5: `deploy-n8n` (depends on healthcheck-poll)
  - Trigger Render deploy hook:
    `curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK_N8N }}`
  - Wait for deploy completion

- [ ] **Validation**: Backend API responds with 200 on health endpoint

##### **8.1.4 `.github/workflows/lstm-retrain.yml`**
**Trigger**: Cron: Sunday 02:00 UTC  
**SLA**: < 20 minutes

- [ ] Job: `retrain-lstm`
  - Checkout code
  - Set up Python 3.11
  - Install: `tensorflow`, `pandas`, `numpy`
  - Download latest dataset from EIA API
  - Append new rows to `data/fuel_hedging_dataset.csv`
  - Run: `python scripts/train_lstm.py`
  - Validate: MAPE < 12% on test set
  - If pass: Commit model artifacts to repo
    - `models/lstm_model.h5`
    - `models/lstm_scaler.pkl`
    - `models/lstm_metadata.json`
  - Use: `GH_PAT=${{ secrets.GH_PAT }}` for commit
  - On failure: Post to Slack, don't commit

- [ ] Post Slack notification with:
  - New MAPE value
  - Training duration
  - Model version number
  - Link to commit

- [ ] **Validation**: Model artifacts updated in repo weekly

##### **8.1.5 `.github/workflows/nightly-validation.yml`**
**Trigger**: Cron: Mon-Fri 23:00 UTC  
**SLA**: < 3 minutes

- [ ] Job: `validate-kpis`
  - HTTP GET: `/api/v1/analytics/forecast/latest`
  - HTTP GET: `/api/v1/analytics/var/latest`
  - HTTP GET: `/api/v1/recommendations/latest`
  - HTTP GET: `/api/v1/health/sources`

  - **Validate Thresholds**:
    - [ ] MAPE < 10% (MAPE_ALERT threshold)
    - [ ] VaR reduction > 40% (VAR_REDUCTION_TARGET)
    - [ ] Hedge ratio <= 80% (HR_HARD_CAP)
    - [ ] Collateral <= 15% (COLLATERAL_LIMIT)
    - [ ] All API sources fetched within last 4h

  - If any breach: **FAIL workflow** + post to Slack
  - Post Slack summary:
    - ✅ All thresholds OK
    - ⚠️ Warnings (if any)
    - ❌ Breaches (if any)
    - Last pipeline run time
    - Last approval time

- [ ] **Validation**: Workflow fails on threshold breach

#### **8.2 Configuration Files**

##### **8.2.1 `.github/CODEOWNERS`**
- [ ] Create file with:
  ```
  # Analytics & Domain Constants
  python_engine/app/constants.py       @<your-github-username>
  python_engine/app/analytics/         @<your-github-username>
  
  # Configuration
  .cursorrules                          @<your-github-username>
  render.yaml                           @<your-github-username>
  docker-compose.yml                    @<your-github-username>
  
  # Security
  .github/workflows/                    @<your-github-username>
  python_engine/app/auth/               @<your-github-username>
  ```
- [ ] Require review from code owners on PR

##### **8.2.2 Update `render.yaml`**
- [ ] Verify all env vars use `sync: false` for secrets
- [ ] Add health check path: `/api/v1/health`
- [ ] Add n8n disk mount: `/home/node/.n8n`, size: 1GB
- [ ] Use `fromDatabase` for `DATABASE_URL`:
  ```yaml
  fromDatabase:
    name: hedge-postgres
    property: connectionString
  ```

#### **8.3 Documentation**

##### **8.3.1 `docs/RUNBOOK.md`**
- [ ] **Procedure: Add a new user**
  - Manual SQL insert or use `/api/v1/config/users` endpoint
  - Role assignment
  - Password reset flow

- [ ] **Procedure: Rollback a model artifact**
  - Revert commit in `models/` directory
  - Trigger re-deploy via GitHub Actions
  - Verify MAPE after rollback

- [ ] **Procedure: Update constraint limits**
  - Admin login → Settings page
  - Update HR cap, collateral limit
  - Audit log entry created automatically
  - Next optimization uses new limits

- [ ] **Procedure: Handle nightly-validation.yml breach**
  - Review Slack alert
  - Check dashboard for root cause
  - If MAPE breach: consider model rollback
  - If API source stale: check external API status
  - Document incident in audit log

- [ ] **Procedure: Manually trigger daily pipeline**
  - n8n UI → fuel_hedge_advisor workflow
  - Click "Execute Workflow" manually
  - Monitor execution in n8n logs
  - Verify recommendation created in React dashboard

- [ ] **Procedure: Render health check failure**
  - Check Render logs: https://dashboard.render.com
  - Common causes:
    - Database connection timeout
    - Redis unavailable
    - Model artifacts missing
  - Restart service if transient error
  - Rollback deployment if persistent issue

##### **8.3.2 `docs/DEPLOYMENT_GUIDE.md`**
- [ ] **Section: GitHub Secrets Setup**
  - List all 10 required secrets
  - Where to find each value
  - How to add to repo: Settings → Secrets → Actions

- [ ] **Section: Render Environment Variables**
  - List all required env vars for each service
  - Where to set: Render dashboard → Service → Environment
  - Note: `sync: false` in render.yaml means manual setup

- [ ] **Section: GitHub Pages Setup**
  - Enable Pages: Settings → Pages
  - Source: GitHub Actions
  - Custom domain (optional)

- [ ] **Section: First-Time Deployment**
  - Step-by-step from scratch
  - Estimated time: 30 minutes
  - Common pitfalls and solutions

##### **8.3.3 `docs/SECURITY_CHECKLIST.md`**
- [ ] **Pre-commit checklist**
  - [ ] `.env` in `.gitignore`
  - [ ] No API keys in code
  - [ ] `detect-secrets` hook installed
  - [ ] Baseline scan run
  - [ ] All GitHub Secrets added
  - [ ] CODEOWNERS file created
  - [ ] JWT_SECRET_KEY generated (32 bytes)
  - [ ] N8N_WEBHOOK_SECRET generated (32 bytes)

- [ ] **Production checklist**
  - [ ] All Render env vars set
  - [ ] Database backups enabled
  - [ ] Rate limiting configured
  - [ ] CORS origin set (not wildcard)
  - [ ] Security headers enabled
  - [ ] API docs disabled in production
  - [ ] Sentry DSN configured (optional)

#### **8.4 GitHub Secrets to Add**

Document the 10 required secrets:

1. `RENDER_DEPLOY_HOOK_API` - Render API service deploy hook URL
2. `RENDER_DEPLOY_HOOK_N8N` - Render n8n service deploy hook URL
3. `RENDER_DATABASE_URL` - Render PostgreSQL connection string
4. `VITE_API_BASE_URL` - `https://hedge-api.onrender.com`
5. `VITE_WS_URL` - `wss://hedge-api.onrender.com`
6. `EIA_API_KEY` - EIA API key
7. `CME_API_KEY` - CME API key
8. `OPENAI_API_KEY` - OpenAI API key
9. `SLACK_WEBHOOK_URL` - Slack incoming webhook
10. `GH_PAT` - GitHub Personal Access Token (repo + workflow scope)

---

## 📋 TASK PRIORITY

### **High Priority (Do First)**
1. ✅ **Documentation organized** (DONE - just completed)
2. 🔄 **Phase 8.3: Create documentation** (RUNBOOK, DEPLOYMENT_GUIDE, SECURITY_CHECKLIST)
3. 🔄 **Phase 8.1: GitHub Actions workflows** (5 workflow files)
4. 🔄 **Phase 8.2: Configuration files** (CODEOWNERS, update render.yaml)

### **Medium Priority (Do After Phase 8)**
5. 🔄 **Phase 7: N8N Agent Migration** (requires understanding of n8n workflow)

### **Low Priority (Optional)**
6. 🔄 Set up actual Render deployment
7. 🔄 Set up GitHub Pages deployment
8. 🔄 Configure GitHub Secrets

---

## 🎯 RECOMMENDED APPROACH

### **Option 1: Complete Phase 8 First (Recommended)**
**Reasoning**: CI/CD can be built and tested locally without n8n
- ✅ Create all 5 workflow files
- ✅ Create documentation (RUNBOOK, DEPLOYMENT_GUIDE, SECURITY_CHECKLIST)
- ✅ Create CODEOWNERS
- ✅ Test workflows with `act` (local GitHub Actions runner)
- ➡️ Then proceed to Phase 7 (n8n)

**Benefits**:
- CI/CD is well-understood and can be completed quickly
- No external dependencies (n8n, live APIs)
- Documentation helps with Phase 7
- Can test workflows locally

### **Option 2: Complete Phase 7 First**
**Reasoning**: Agent migration is the "missing piece" for live recommendations
- ⚠️ Requires understanding of existing n8n workflow
- ⚠️ Requires live API access (EIA, CME, ICE)
- ⚠️ More complex testing

### **Option 3: Hybrid Approach**
- ✅ Complete Phase 8.3 (documentation) first
- ✅ Complete Phase 8.1 (workflows) second
- ✅ Complete Phase 7 (n8n) third
- ✅ Complete Phase 8 deployment fourth

---

## 📊 ESTIMATED COMPLETION TIME

| Phase | Tasks | Estimated Time | Cumulative |
|-------|-------|----------------|------------|
| 8.3 - Documentation | 3 files | 1-1.5 hours | 1-1.5 hours |
| 8.1 - GitHub Workflows | 5 files | 1.5-2 hours | 2.5-3.5 hours |
| 8.2 - Configuration | 2 files | 0.5 hours | 3-4 hours |
| 7 - N8N Migration | 10 tasks | 3-4 hours | 6-8 hours |

**Total Remaining**: 6-8 hours to 100% completion

---

## ✅ SUCCESS CRITERIA

### **Phase 8 Complete When**:
- [ ] All 5 GitHub Actions workflows created
- [ ] All workflows pass validation (syntax correct)
- [ ] RUNBOOK.md covers all operational procedures
- [ ] DEPLOYMENT_GUIDE.md covers initial setup
- [ ] SECURITY_CHECKLIST.md covers pre-commit + production
- [ ] CODEOWNERS file created
- [ ] render.yaml updated with health check + disk mount

### **Phase 7 Complete When**:
- [ ] All 37 n8n nodes migrated
- [ ] Manual test: n8n → FastAPI → React flow works
- [ ] All 5 agents return valid JSON
- [ ] Approval workflow completes end-to-end
- [ ] Escalation triggers correctly
- [ ] Error handler catches failures

### **Project 100% Complete When**:
- [ ] Phases 0-8 all done
- [ ] All workflows green on GitHub
- [ ] Frontend deployed to GitHub Pages
- [ ] Backend deployed to Render
- [ ] Health check passes
- [ ] First live recommendation created
- [ ] First approval workflow completed

---

## 🚀 NEXT STEP

**Recommended**: Start with **Phase 8.3 - Documentation**

This will:
1. Create operational procedures (helps with testing)
2. Document deployment process (helps with Phase 8.1)
3. Create security checklist (required before production)
4. Estimated time: 1-1.5 hours
5. No external dependencies

**Command to proceed**:
```
Start Phase 8.3: Create RUNBOOK.md, DEPLOYMENT_GUIDE.md, and SECURITY_CHECKLIST.md
```

---

**Status**: 📝 **DOCUMENTED - READY TO PROCEED WITH PHASE 8.3**
