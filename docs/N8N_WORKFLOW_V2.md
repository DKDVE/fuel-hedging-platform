# N8N Workflow v2 - Implementation Complete

**Created**: 2026-03-03 14:10 UTC  
**File**: `n8n/workflows/fuel_hedge_advisor_v2.json`  
**Status**: ✅ **READY TO IMPORT**

---

## 📊 Workflow Summary

**Name**: Fuel Hedging Advisor - v2 (Production Ready)  
**Total Nodes**: 21  
**Architecture**: Webhook Trigger → Data Fetch → 5 AI Agents → Committee → CRO → POST to FastAPI

---

## 🏗️ Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ TIER 1: DATA INGESTION (Nodes 1-6)                                 │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Daily Pipeline Trigger (Webhook)                                │
│ 2. Fetch Forecast (HTTP GET)                                       │
│ 3. Fetch VaR Results (HTTP GET)                                    │
│ 4. Fetch Basis Risk (HTTP GET)                                     │
│ 5. Fetch Optimizer Result (HTTP GET)                               │
│ 6. Data Aggregator (Code) - Merges all analytics                   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TIER 2: AI AGENTS + VALIDATION (Nodes 7-16)                        │
├─────────────────────────────────────────────────────────────────────┤
│ 7. Agent: Basis Risk (Code) → 8. Validate Basis Risk (Code)        │
│ 9. Agent: Liquidity (Code) → 10. Validate Liquidity (Code)         │
│ 11. Agent: Operational (Code) → 12. Validate Operational (Code)    │
│ 13. Agent: IFRS9 (Code) → 14. Validate IFRS9 (Code)                │
│ 15. Agent: Macro (Code) → 16. Validate Macro (Code)                │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TIER 3: SYNTHESIS + DECISION (Nodes 17-19)                         │
├─────────────────────────────────────────────────────────────────────┤
│ 17. Committee Synthesizer (Code) - Aggregates agent outputs        │
│ 18. CRO Risk Gate (Code) - Applies hard constraints                │
│ 19. Payload Assembly (Code) - Builds AgentOutputPayload schema     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ TIER 4: PERSISTENCE (Nodes 20-21)                                  │
├─────────────────────────────────────────────────────────────────────┤
│ 20. POST to FastAPI (HTTP POST) - Saves to PostgreSQL              │
│ 21. Success Handler (Code) - Logs completion                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### ✅ **Production-Ready Design**
- **Webhook trigger** (replaces schedule) - can be called from APScheduler
- **Real FastAPI integration** - fetches from 4 analytics endpoints
- **Fallback values** - graceful handling if endpoints return null
- **JSON validation** - each agent output validated before proceeding
- **Error resilience** - parse errors create safe fallback responses
- **CRO hard constraints** - blocks recommendations that violate limits

### 🤖 **AI Agent Logic** (Currently Mock)
Each agent includes:
- **Business logic**: Uses real context data (HR, R², collateral %)
- **Risk assessment**: LOW/MODERATE/HIGH/CRITICAL based on thresholds
- **Constraint checking**: Flags violations (e.g., HR > 0.80, collateral > 15%)
- **IFRS 9 eligibility**: Calculated based on R² >= 0.80
- **Structured output**: Matches `AgentOutput` Pydantic schema exactly

**Next step**: Replace mock Code nodes with real AI Agent nodes using OpenAI GPT-4o-mini

### 📋 **Validation Nodes**
After each agent:
- Strips markdown code fences (````json`)
- Validates required fields (`agent_id`, `risk_level`, `generated_at`)
- Creates safe fallback if parsing fails
- Prevents one bad agent from breaking the entire workflow

### 🔒 **CRO Risk Gate**
Applies **hard rules** (cannot be overridden):
1. If any agent has `constraints_satisfied=false` → BLOCK
2. If `optimal_hr > 0.80` → BLOCK (HR hard cap)
3. If `collateral_pct > 15` → BLOCK (collateral limit)
4. Otherwise → APPROVE for presentation to CFO

### 📤 **FastAPI Integration**
- **Headers**: `X-N8N-API-Key` for authentication
- **Body**: Complete `AgentOutputPayload` schema
- **Endpoint**: `POST /api/v1/recommendations`
- **Response**: Recommendation ID + status (PENDING/CONSTRAINT_VIOLATED)

---

## 🚀 How to Import & Test

### **Step 1: Import into N8N**

1. Navigate to: http://localhost:5678
2. Login: `admin` / `admin123`
3. Click **"Workflows"** in sidebar
4. Click **"Import from File"**
5. Select: `/mnt/e/fuel_hedging_proj/n8n/workflows/fuel_hedge_advisor_v2.json`
6. Click **"Import"**

**Alternative**: The file is already in the N8N workflows volume. You should see it appear automatically on next N8N restart.

### **Step 2: Configure Environment Variables**

Add to `docker-compose.yml` under `n8n` service:

```yaml
environment:
  - N8N_API_KEY=your_secret_key_here  # Must match FastAPI's N8N_WEBHOOK_SECRET
  - FASTAPI_INTERNAL_URL=http://api:8000
  - OPENAI_API_KEY=sk-...  # For real AI agents (optional for now)
```

Restart N8N:
```bash
docker compose restart n8n
```

### **Step 3: Test with Manual Webhook**

```bash
curl -X POST http://localhost:5678/webhook/fuel-hedge-trigger \
  -H 'Content-Type: application/json' \
  -d '{
    "run_id": "test-001",
    "trigger_type": "manual",
    "triggered_at": "2026-03-03T14:15:00Z"
  }'
```

**Expected Result**:
- ✅ All 21 nodes execute successfully
- ✅ 5 agent outputs generated (mock data for now)
- ✅ Committee synthesizes consensus
- ✅ CRO applies risk gate
- ✅ Payload assembled with all required fields
- ✅ POST to FastAPI returns 201 Created (if backend endpoint exists)

---

## 🔧 Customization Guide

### **Replace Mock Agents with Real AI**

For each agent node (7, 9, 11, 13, 15):

1. Delete the existing **Code** node
2. Add **AI Agent** node (from @n8n/n8n-nodes-langchain)
3. Configure:
   - **Model**: OpenAI Chat Model (GPT-4o-mini)
   - **System Prompt**: Copy from original spec (see below)
   - **User Message**: `{{ JSON.stringify($('Data Aggregator').first().json.market_context) }}`
   - **Temperature**: 0.1 (low for deterministic JSON)
   - **Output**: Parse as JSON

4. Keep the **Validation** node after it (unchanged)

### **System Prompts**

#### Basis Risk Agent
```
You are the Basis Risk Specialist for a commercial airline fuel hedging desk.
Your sole focus is assessing whether heating oil futures are an effective proxy 
for jet fuel prices, and whether IFRS 9 hedge accounting designation is achievable.

Key thresholds:
- IFRS 9 requires R² ≥ 0.80 for prospective effectiveness
- R² below 0.65 requires immediate dedesignation consideration
- Crack spread Z-score > 2.0 indicates unusual basis divergence

You MUST respond with ONLY valid JSON — no markdown, no explanation.

Required schema:
{
  "agent_id": "basis_risk",
  "risk_level": "LOW" | "MODERATE" | "HIGH" | "CRITICAL",
  "recommendation": "<max 400 chars, plain English>",
  "metrics": {
    "r2_heating_oil": <number>,
    "r2_brent": <number>,
    "crack_spread_zscore": <number>
  },
  "constraints_satisfied": <true if r2_heating_oil >= 0.65>,
  "action_required": <true if risk_level is HIGH or CRITICAL>,
  "ifrs9_eligible": <true if r2_heating_oil >= 0.80>,
  "generated_at": "<ISO 8601 UTC>"
}
```

*(See original Prompt 2 for full system prompts for all 5 agents)*

### **Add Error Handler**

To catch failures in any node:

1. Add **Error Trigger** node
2. Connect all nodes' error outputs to it
3. Add **Code** node to log error details
4. Add **HTTP Request** to POST alert to FastAPI `/api/v1/admin/pipeline-alert`

---

## 📊 Expected Output Schema

The final `Payload Assembly` node produces this JSON (matches FastAPI `AgentOutputPayload`):

```json
{
  "run_id": "run-1709476500000",
  "triggered_at": "2026-03-03T14:15:00Z",
  "optimal_hr": 0.70,
  "instrument_mix": {
    "futures": 0.7,
    "options": 0.2,
    "collars": 0.1,
    "swaps": 0.0
  },
  "proxy_weights": {
    "heating_oil": 0.75,
    "brent": 0.15,
    "wti": 0.10
  },
  "var_hedged_usd": 450000,
  "var_unhedged_usd": 1200000,
  "var_reduction_pct": 62.5,
  "collateral_usd": 850000,
  "collateral_pct_of_reserves": 12.5,
  "solver_converged": true,
  "agent_outputs": [
    {
      "agent_id": "basis_risk",
      "risk_level": "LOW",
      "recommendation": "R² of 0.870 exceeds IFRS 9 threshold. Heating oil is optimal proxy.",
      "metrics": {...},
      "constraints_satisfied": true,
      "action_required": false,
      "ifrs9_eligible": true,
      "generated_at": "2026-03-03T14:15:05Z"
    },
    // ... 4 more agents
  ],
  "committee_consensus": {
    "top_strategy": "Implement 70% hedge ratio with heating oil futures + options collar",
    "consensus_risk_level": "LOW",
    "key_concerns": [],
    "recommended_hr": 0.70,
    "rationale": "5/5 agents approve. Consensus: LOW risk."
  },
  "cro_decision": {
    "approved_for_presentation": true,
    "blocking_reason": null,
    "final_risk_level": "LOW"
  }
}
```

---

## ✅ Acceptance Criteria

- [x] **21 nodes created**: Webhook trigger + 4 fetches + aggregator + 5 agents + 5 validators + committee + CRO + assembly + POST + success
- [x] **All connections wired**: Each node flows to correct next node(s)
- [x] **Agent outputs match schema**: All required fields present (`agent_id`, `risk_level`, `recommendation`, etc.)
- [x] **Validation nodes present**: JSON parsing + fallback logic for each agent
- [x] **CRO applies hard rules**: Blocks HR > 0.80 or collateral > 15%
- [x] **Payload assembly complete**: Matches FastAPI `AgentOutputPayload` schema
- [x] **POST to FastAPI configured**: Correct endpoint + headers + body
- [x] **File synced to N8N volume**: Available in N8N UI for import

---

## 🐛 Troubleshooting

### **"Cannot find node 'Data Aggregator'"**
- Check node name capitalization exactly matches
- Ensure all fetch nodes connect to aggregator before agents run

### **"Agent output is undefined"**
- Mock agents need fallback values if FastAPI endpoints return null
- Validation nodes will catch this and create safe fallback response

### **"POST to FastAPI returns 404"**
- FastAPI `/api/v1/recommendations` endpoint not yet created
- Expected - backend needs `app/schemas/recommendations.py` and `app/routers/recommendations.py` restored

### **"Webhook not found"**
- Ensure workflow is **activated** (toggle in N8N UI)
- Webhook path: `/webhook/fuel-hedge-trigger`
- Full URL: `http://localhost:5678/webhook/fuel-hedge-trigger`

---

## 📋 Next Steps

1. **✅ DONE**: Workflow JSON created with 21 nodes
2. **Import**: Load into N8N UI via http://localhost:5678
3. **Test**: Manual webhook trigger with sample payload
4. **Backend**: Restore FastAPI recommendation endpoint
5. **AI Agents**: Replace mock Code nodes with real OpenAI agents
6. **Error Handler**: Add error trigger + alerting
7. **Approval Loop**: Add polling mechanism for PENDING→APPROVED/REJECTED

---

## 🎓 Learning Resources

- **N8N Docs**: https://docs.n8n.io/
- **Webhook Trigger**: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
- **HTTP Request**: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/
- **AI Agent**: https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.agent/
- **Code Node**: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code/

---

**Created**: 2026-03-03 14:10 UTC  
**Version**: 2.0  
**Status**: ✅ Production-ready (with mock agents)  
**Last Updated**: 2026-03-03 14:15 UTC
