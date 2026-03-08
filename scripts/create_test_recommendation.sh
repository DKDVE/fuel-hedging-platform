#!/bin/bash
# create_test_recommendation.sh
# Creates a test recommendation via API (simulates n8n output)
# Use when n8n/OpenAI is not available — for demo purposes.
# Run: bash scripts/create_test_recommendation.sh

set -e

API_URL="${API_URL:-http://localhost:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Load env
if [ -f "python_engine/.env" ]; then
  export $(grep -v '^#' python_engine/.env | xargs)
fi
N8N_KEY="${N8N_WEBHOOK_SECRET:-2b4855c6a760b42c399a335b0b6644b3073ee3b0}"

RUN_ID="test-$(date +%s)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "Posting test recommendation (using X-N8N-API-Key)..."
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/recommendations" \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-Key: $N8N_KEY" \
  -d "{
    \"run_id\": \"$RUN_ID\",
    \"triggered_at\": \"$TIMESTAMP\",
    \"optimal_hr\": 0.68,
    \"instrument_mix\": {\"futures\": 0.70, \"options\": 0.20, \"collars\": 0.05, \"swaps\": 0.05},
    \"proxy_weights\": {\"heating_oil\": 0.70, \"brent\": 0.20, \"wti\": 0.10},
    \"var_hedged_usd\": 2100000,
    \"var_unhedged_usd\": 3360000,
    \"var_reduction_pct\": 37.5,
    \"collateral_usd\": 1937500,
    \"collateral_pct_of_reserves\": 12.9,
    \"solver_converged\": true,
    \"agent_outputs\": [
      {\"agent_id\": \"basis_risk\", \"risk_level\": \"MODERATE\", \"recommendation\": \"Heating oil R² of 0.8517 meets IFRS 9 threshold. Crack spread within normal range.\", \"metrics\": {\"r2_heating_oil\": 0.8517, \"r2_brent\": 0.7823, \"crack_spread_zscore\": 0.8}, \"constraints_satisfied\": true, \"action_required\": false, \"ifrs9_eligible\": true, \"generated_at\": \"$TIMESTAMP\"},
      {\"agent_id\": \"liquidity\", \"risk_level\": \"MODERATE\", \"recommendation\": \"Collateral at 12.9% is within limits. Monitor approaching 15% cap.\", \"metrics\": {\"collateral_pct_of_reserves\": 0.129, \"collateral_usd\": 1937500, \"estimated_margin_headroom_usd\": 312500}, \"constraints_satisfied\": true, \"action_required\": true, \"ifrs9_eligible\": null, \"generated_at\": \"$TIMESTAMP\"},
      {\"agent_id\": \"operational\", \"risk_level\": \"LOW\", \"recommendation\": \"Hedge ratio of 68% is well within the 80% hard cap. All operational constraints satisfied.\", \"metrics\": {\"optimal_hr\": 0.68, \"hr_hard_cap\": 0.80, \"coverage_ratio_estimate\": 0.85}, \"constraints_satisfied\": true, \"action_required\": false, \"ifrs9_eligible\": null, \"generated_at\": \"$TIMESTAMP\"},
      {\"agent_id\": \"ifrs9\", \"risk_level\": \"LOW\", \"recommendation\": \"Hedge qualifies for IFRS 9 designation. Prospective R² of 0.8517 exceeds minimum.\", \"metrics\": {\"r2_prospective\": 0.8517, \"ifrs9_eligible\": true, \"retrospective_ratio_estimate\": 0.962}, \"constraints_satisfied\": true, \"action_required\": false, \"ifrs9_eligible\": true, \"generated_at\": \"$TIMESTAMP\"},
      {\"agent_id\": \"macro\", \"risk_level\": \"MODERATE\", \"recommendation\": \"Volatility elevated at 17.3%. Recommend hedging now before option premiums rise further.\", \"metrics\": {\"volatility_index\": 17.32, \"vol_regime\": \"MODERATE\", \"geopolitical_risk\": \"MODERATE\", \"hedge_timing_signal\": \"HEDGE_NOW\"}, \"constraints_satisfied\": true, \"action_required\": false, \"ifrs9_eligible\": null, \"generated_at\": \"$TIMESTAMP\"}
    ],
    \"committee_consensus\": {
      \"top_strategy\": \"Hedge 68% using Futures\",
      \"consensus_risk_level\": \"MODERATE\",
      \"key_concerns\": [\"Collateral approaching 15% limit\"],
      \"recommended_hr\": 0.68,
      \"rationale\": \"4 approve, 1 caution. Moderate risk with all constraints satisfied.\"
    },
    \"cro_decision\": {
      \"approved_for_presentation\": true,
      \"blocking_reason\": null,
      \"final_risk_level\": \"MODERATE\"
    }
  }")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
REC_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('recommendation_id',''))" 2>/dev/null || echo "")
if [ -n "$REC_ID" ]; then
  echo ""
  echo "✓ Recommendation created: $REC_ID"
  echo "Open http://localhost:5173/recommendations to view"
fi
