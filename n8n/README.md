## Demand Strategy Advisor Workflow

### Import
1. Open n8n dashboard → Workflows → Import from file
2. Select `n8n/workflows/demand_strategy_advisor.json`
3. Activate the workflow (toggle at top right)
4. The webhook path is: `/webhook/demand-strategy-advisor`

### Required environment variable
Set `GROQ_API_KEY` in the n8n service environment variables on Render.
This is the same key used by the existing fuel_hedge_advisor_v2 workflow.

### How it works
The workflow receives a POST from FastAPI's `/analytics/demand-strategy`
endpoint containing the CFO's chosen hedge ratio, consumption volume,
and the optimizer result. It passes this to Groq (`llama-3.3-70b-versatile`) with a
treasury-analyst system prompt and returns a 3-sentence CFO briefing.

If the workflow is inactive or n8n is unreachable, the endpoint falls
back to a templated narrative automatically — the feature degrades
gracefully.

### Testing
```bash
curl -X POST https://<your-n8n-url>/webhook/demand-strategy-advisor \
  -H "Content-Type: application/json" \
  -d '{
    "hedge_ratio": 0.65,
    "consumption_bbl": 85000,
    "instruments": ["futures", "options"],
    "current_var_usd": 2870000,
    "what_if_result": {
      "what_if": {
        "hedge_ratio": 0.65,
        "instrument_mix": {"futures": 0.80, "options": 0.10, "collars": 0.05, "swaps": 0.05},
        "var_usd": 2740000,
        "collateral_usd": 950000,
        "collateral_pct_of_reserves": 7.5,
        "solver_converged": true
      },
      "comparison": {
        "original_var_hedged": 2870000,
        "what_if_var": 2740000,
        "var_difference": 130000,
        "var_better": true,
        "collateral_delta_usd": 0,
        "monthly_saving_vs_unhedged": 380000
      }
    }
  }'
```
Expected response: `{"success": true, "narrative": "...", "what_if": {...}, ...}`
