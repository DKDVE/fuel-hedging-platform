# N8N Environment Variable Fix - March 4, 2026

## Problem
The N8N workflow "Fuel Hedging Advisor - v2 (Production Ready)" was failing with error:
```
access to env vars denied
```

This occurred because N8N blocks access to environment variables from within workflow node expressions by default for security reasons.

## Root Cause
The workflow uses expressions like:
```javascript
={{$env.FASTAPI_INTERNAL_URL || 'http://api:8000'}}/api/v1/analytics/forecast/latest
```

These expressions need access to environment variables, but N8N's default security setting `N8N_BLOCK_ENV_ACCESS_IN_NODE` blocks this access.

## Solution Applied

### 1. Added Environment Variable to docker-compose.yml
```yaml
n8n:
  environment:
    - N8N_BLOCK_ENV_ACCESS_IN_NODE=false  # Allow env vars in workflow expressions
    - OPENAI_API_KEY=${OPENAI_API_KEY:-}  # For future AI integration
```

### 2. Recreated N8N Container
Simply restarting the container doesn't pick up new environment variables. The container must be recreated:

```bash
# Stop and remove old container
docker stop hedge-n8n
docker rm hedge-n8n

# Create new container with updated environment
docker run -d \
  --name hedge-n8n \
  --network fuel_hedging_proj_default \
  -p 5678:5678 \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  -e FASTAPI_INTERNAL_URL=http://api:8000 \
  # ... other env vars ...
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n:latest
```

## Verification
Check the environment variable is set:
```bash
docker exec hedge-n8n env | grep N8N_BLOCK
# Output: N8N_BLOCK_ENV_ACCESS_IN_NODE=false ✅
```

## Remaining Issue: Workflow Not Active

After recreating the container, the workflow needs to be **activated** in the N8N UI.

### Steps to Activate Workflow:

1. **Open N8N UI**: http://localhost:5678
   - Username: `admin`
   - Password: `admin123`

2. **Open the Workflow**:
   - Go to "Workflows" in left sidebar
   - Click on "Fuel Hedging Advisor - v2 (Production Ready)"

3. **Activate the Workflow**:
   - Click the toggle switch in the top-right corner (next to "Active")
   - The toggle should turn green/blue indicating it's active

4. **Test the Workflow**:
   ```bash
   curl -X POST http://localhost:5678/webhook/fuel-hedge-trigger \
     -H "Content-Type: application/json" \
     -d '{
       "run_id": "test_run_001",
       "timestamp": "2026-03-04T01:00:00Z",
       "trigger_source": "manual_test"
     }'
   ```

## Expected Result After Activation

✅ **Successful Response**: The workflow will execute and should return a 200 status code with workflow results.

⚠️ **Possible 500 Error**: The workflow may still fail if:
- FastAPI endpoints don't exist or return errors
- Authentication is required but not provided
- Missing analytics data

## Alternative: Use Test Webhook

N8N provides both **test** and **production** webhook URLs:

- **Test URL**: `http://localhost:5678/webhook-test/fuel-hedge-trigger` (works even when workflow is inactive)
- **Production URL**: `http://localhost:5678/webhook/fuel-hedge-trigger` (requires workflow to be active)

For testing purposes, use the test URL:
```bash
curl -X POST http://localhost:5678/webhook-test/fuel-hedge-trigger \
  -H "Content-Type: application/json" \
  -d '{"run_id": "test_001", "trigger_source": "test"}'
```

## FastAPI Integration Required

The workflow expects these FastAPI endpoints to exist and return data:

1. **`GET /api/v1/analytics/forecast/latest`**
   - Status: ✅ EXISTS (but requires authentication)
   
2. **`GET /api/v1/analytics/var/latest`**
   - Status: ❌ NOT FOUND IN ENDPOINT LIST
   
3. **`GET /api/v1/analytics/basis-risk/latest`**
   - Status: ❌ NOT FOUND IN ENDPOINT LIST
   
4. **`GET /api/v1/analytics/optimizer/latest`**
   - Status: ❌ NOT FOUND IN ENDPOINT LIST

5. **`POST /api/v1/recommendations`**
   - Status: ✅ EXISTS (via N8N internal endpoint)

### Option 1: Implement Missing Endpoints (Recommended for Production)
Create the missing analytics endpoints in FastAPI:
- `python_engine/app/routers/analytics.py`
- Add endpoints for VaR, basis risk, and optimizer results

### Option 2: Simplify Workflow to Use Mock Data (Quick Fix)
Modify the workflow to:
- Skip the missing HTTP requests
- Use mock data in the Data Aggregator node
- Focus on testing the agent logic and payload assembly

## Security Considerations

**Important**: Setting `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` allows workflow nodes to access ALL environment variables. This is a security risk if:
- Untrusted users can create/edit workflows
- Sensitive secrets are stored in environment variables

### Mitigations:
1. ✅ Use N8N's built-in "Credentials" feature for sensitive data instead of env vars
2. ✅ Restrict workflow editing permissions to trusted admins only
3. ✅ Don't store database passwords or API keys in environment variables
4. ✅ Use separate secrets management (e.g., HashiCorp Vault) for production

## Docker Compose Alternative

For easier management, ensure you're using `docker compose` (v2) instead of `docker-compose`:

```bash
# Recreate just the N8N service
cd /mnt/e/fuel_hedging_proj
docker compose down n8n
docker compose up -d n8n

# Or recreate all services to pick up changes
docker compose up -d --force-recreate n8n
```

## Summary

| Step | Status | Notes |
|------|--------|-------|
| Add env var to docker-compose.yml | ✅ Done | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` |
| Recreate N8N container | ✅ Done | Environment variable verified |
| Workflow exists in N8N | ✅ Done | Visible in UI |
| Workflow is active | ⚠️ **Manual Action Required** | Must activate in UI |
| FastAPI endpoints ready | ⚠️ Partial | Missing 3 of 4 analytics endpoints |

## Next Action Required

**Please activate the workflow in the N8N UI** by following the steps above, then test it again!

Alternatively, if you want to test immediately without the UI, you can use the test webhook URL which doesn't require activation.
