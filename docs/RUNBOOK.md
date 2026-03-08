# Operations Runbook — Fuel Hedging Platform

## Adding a New User

1. SSH into Render (or use the Render shell): `render shell hedge-api`
2. Run: `python scripts/create_user.py --email user@example.com --role analyst`
3. User receives a reset-password email (if SMTP configured) or gets a temp password printed to console

## Rolling Back a Model Artifact

If LSTM retraining produces a degraded model:
1. Go to GitHub → commits → find last good `chore(models): weekly retrain` commit
2. Copy the commit SHA
3. Run locally: `git checkout <SHA> -- models/`
4. Commit: `git commit -m "fix: revert model artifacts to <SHA> due to MAPE regression"`
5. Push — triggers deploy-backend.yml which redeploys

## Updating Constraint Limits

Constraint limits (HR_HARD_CAP, COLLATERAL_LIMIT, etc.) are in:
- `python_engine/app/constants.py` — code defaults
- The `config` table in PostgreSQL — runtime overrides (admin can change via Settings page)

To update without redeployment:
1. Log in as admin at the platform URL
2. Navigate to Settings → Risk Constraints
3. Update values — changes take effect immediately (no restart needed)

To update the code defaults (requires redeployment):
1. Edit `python_engine/app/constants.py`
2. PR → merge to main → auto-deploys via deploy-backend.yml

## Handling a Nightly Validation Breach

When nightly-validation.yml fails:
1. Check the Actions run log for which threshold breached
2. Log in to the platform as risk_manager or admin
3. Navigate to Compliance page — the breached limit shows in red
4. Check Alerts — the alert system will have created an alert
5. If MAPE > 12%: trigger manual model retrain (workflow_dispatch on lstm-retrain.yml)
6. If VaR > limit: escalate to CFO — a recommendation review may be needed
7. If collateral > 15%: immediately review open positions via Positions page

## Manually Triggering the Daily Pipeline

Via the UI (recommended):
1. Log in as admin
2. Dashboard → "Run Pipeline" button

Via GitHub Actions:
1. Go to Actions → deploy-backend.yml → "Run workflow"

Via curl (direct n8n trigger):
```bash
curl -X POST https://YOUR-N8N-URL/webhook/fuel-hedge-trigger \
  -H "Content-Type: application/json" \
  -d '{"trigger_type": "manual", "run_id": "manual-'$(date +%s)'"}'
```

## If Render Health Check Fails

Symptoms: deploy-backend.yml shows "API did not become healthy" error.

Diagnosis:
1. Check Render dashboard → hedge-api → Logs tab
2. Look for: startup errors, missing env vars, DB connection failures

Common causes and fixes:
- **Missing env var**: Render dashboard → hedge-api → Environment → add the missing var → manual deploy
- **Migration failed**: Check migration logs. May need to run `alembic downgrade -1` then `alembic upgrade head`
- **Out of memory**: Starter plan has 512MB RAM. Check if LSTM model loading is causing OOM. Consider lazy loading.
- **DB connection refused**: Render Postgres may have restarted. Usually self-heals in < 2 min. Re-trigger deploy.

Emergency rollback:
1. Render dashboard → hedge-api → Deploys tab → find last successful deploy → "Rollback to this deploy"

## Required Render Secrets

Set these in Render dashboard for each service:

**hedge-api:**
- SECRET_KEY (same as JWT_SECRET_KEY in GitHub)
- N8N_WEBHOOK_SECRET
- OPENAI_API_KEY (optional)
- EIA_API_KEY (optional)

**hedge-n8n:**
- N8N_API_KEY (same value as N8N_WEBHOOK_SECRET)
- N8N_ENCRYPTION_KEY (run: `openssl rand -hex 32`)
- WEBHOOK_URL (your Render n8n service public URL)
- OPENAI_API_KEY (optional)

## GitHub Pages Base Path

For project sites, the frontend is served at `https://USERNAME.github.io/fuel-hedging-platform/`.
Set `VITE_BASE_PATH=/fuel-hedging-platform/` in GitHub Actions secrets when building for Pages.
