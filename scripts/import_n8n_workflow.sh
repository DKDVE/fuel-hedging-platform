#!/bin/bash
# import_n8n_workflow.sh
# Imports the fuel hedge advisor workflow into n8n via API
# Run: bash scripts/import_n8n_workflow.sh

set -e

N8N_URL="${N8N_URL:-http://localhost:5678}"
WORKFLOW_FILE="n8n/workflows/fuel_hedge_advisor_v2.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Load N8N_WEBHOOK_SECRET from .env if present
if [ -f "python_engine/.env" ]; then
  export $(grep -v '^#' python_engine/.env | xargs)
fi
N8N_API_KEY="${N8N_WEBHOOK_SECRET:-$N8N_API_KEY}"

echo "Waiting for n8n to be ready..."
until curl -s "$N8N_URL/healthz" > /dev/null 2>&1 || curl -s "$N8N_URL" > /dev/null 2>&1; do
  sleep 2
done
echo "✓ n8n is ready"

echo "Importing workflow..."
RESPONSE=$(curl -s -X POST "$N8N_URL/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d @"$WORKFLOW_FILE" 2>/dev/null || echo "{}")

WORKFLOW_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")

if [ -n "$WORKFLOW_ID" ]; then
  echo "✓ Workflow imported with ID: $WORKFLOW_ID"
  curl -s -X PATCH "$N8N_URL/api/v1/workflows/$WORKFLOW_ID" \
    -H "Content-Type: application/json" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -d '{"active": true}' > /dev/null 2>&1 || true
  echo "✓ Workflow activated"
else
  echo "Workflow may already exist or API key not configured."
  echo "Manual setup: open $N8N_URL, import $WORKFLOW_FILE, activate"
fi

echo ""
echo "To test: curl -X POST http://localhost:8000/api/v1/analytics/trigger \\"
echo "  -b cookies.txt  (must be logged in as admin)"
