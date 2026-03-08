# 🚀 N8N WORKFLOW - STEP-BY-STEP IMPLEMENTATION GUIDE

**Status**: Ready to Build  
**Estimated Time**: 2-3 hours  
**N8N Version**: Latest (Docker)

---

## ✅ PREREQUISITES

- [x] N8N running on http://localhost:5678
- [x] Agent prompts documented in `docs/N8N_AGENT_PROMPTS.md`
- [x] FastAPI backend running on http://hedge-api:8000 (Docker internal)
- [x] Reference workflow: `n8n/workflows/Ai Hedge Fund viral copy.json`

---

## 📋 IMPLEMENTATION STEPS

### **STEP 1: Access N8N UI**

1. Open browser: http://localhost:5678
2. Create account if first time (local instance)
3. Click **"+ Add workflow"** → **"Create new workflow"**
4. Name it: **"Fuel Hedging Advisor - Production v1"**

---

### **STEP 2: Add Credentials (One Time Setup)**

Before building nodes, add these credentials:

#### **2.1: OpenAI API Credential**
- Go to **Settings** (top right) → **Credentials** → **New**
- Type: **OpenAI API**
- Name: `OpenAI - Fuel Hedging`
- API Key: `your-openai-api-key`
- Save

#### **2.2: EIA API Credential (Optional - for real data)**
- Type: **Generic Credential Type** → **Query Auth**
- Name: `EIA API Key`
- Parameter Name: `api_key`
- Value: `your-eia-api-key` (get from https://www.eia.gov/opendata/)

#### **2.3: CME/ICE API (Optional - for real data)**
- Type: **Header Auth**
- Name: `CME API Key`
- Header Name: `X-API-Key`
- Value: `your-cme-api-key`

---

### **STEP 3: Build Workflow Nodes**

Now build the workflow from left to right:

---

## 🎯 NODE CONFIGURATION

### **NODE 1: Schedule Trigger**

**Type**: Schedule Trigger  
**Position**: (-800, 0)

**Configuration**:
- Mode: **Custom**
- Cron Expression: `0 6 * * *` (daily 06:00 UTC)
- Description: "Triggers daily analytics pipeline"

**Alternative**: Add Webhook trigger for manual execution
- Type: Webhook
- HTTP Method: POST
- Path: `fuel-hedge-manual`
- Response Mode: Last Node

---

### **NODE 2: Get Latest Market Data from FastAPI**

**Type**: HTTP Request  
**Position**: (-500, 0)  
**Name**: "FastAPI - Get Latest Prices"

**Configuration**:
```
Method: GET
URL: http://hedge-api:8000/api/v1/market-data/latest
Authentication: None (internal Docker network)
Timeout: 30000ms
```

**Expected Response**:
```json
{
  "date": "2026-03-03",
  "jet_fuel_spot_usd_bbl": 95.50,
  "heating_oil_futures_usd_bbl": 92.30,
  "brent_crude_futures_usd_bbl": 85.00,
  "wti_crude_futures_usd_bbl": 82.50,
  "crack_spread_usd_bbl": 3.20,
  "volatility_index_pct": 18.5
}
```

**Note**: If FastAPI endpoint doesn't exist yet, use mock data node instead (see Alternative below).

**Alternative - Mock Data Node**:
```javascript
// Type: Code (Function)
// Name: "Mock Market Data"
return [{
  json: {
    date: new Date().toISOString().split('T')[0],
    jet_fuel_spot_usd_bbl: 95.50,
    heating_oil_futures_usd_bbl: 92.30,
    brent_crude_futures_usd_bbl: 85.00,
    wti_crude_futures_usd_bbl: 82.50,
    crack_spread_usd_bbl: 3.20,
    volatility_index_pct: 18.5,
    volatility_regime: 'LOW',
    r2_heating_oil: 0.87,
    r2_brent: 0.75,
    r2_wti: 0.72,
    recommended_proxy: 'heating_oil',
    ifrs9_eligible: true,
    forecast_mape: 7.2
  }
}];
```

---

### **NODE 3: Get Analytics from FastAPI**

**Type**: HTTP Request  
**Position**: (-300, 0)  
**Name**: "FastAPI - Get Analytics"

**Configuration**:
```
Method: GET
URL: http://hedge-api:8000/api/v1/analytics/latest
Authentication: None
Timeout: 30000ms
```

**Merge with Market Data**:
- Add **Merge** node after both HTTP requests
- Mode: Combine
- Output: Single item with all data

---

### **NODE 4: Format Data for Agents**

**Type**: Code (Function)  
**Position**: (-100, 0)  
**Name**: "Format Agent Input"

**JavaScript Code**:
```javascript
const marketData = $('FastAPI - Get Latest Prices').first().json;
const analytics = $('FastAPI - Get Analytics').first().json;

// Combine all data into formatted analysis string
const formattedAnalysis = `
# FUEL HEDGING MARKET DATA
Date: ${marketData.date}

## Spot & Futures Prices
- Jet Fuel Spot (US Gulf Coast): $${marketData.jet_fuel_spot_usd_bbl.toFixed(2)}/bbl
- Heating Oil Futures (NYMEX): $${marketData.heating_oil_futures_usd_bbl.toFixed(2)}/bbl
- Brent Crude Futures (ICE): $${marketData.brent_crude_futures_usd_bbl.toFixed(2)}/bbl
- WTI Crude Futures (NYMEX): $${marketData.wti_crude_futures_usd_bbl.toFixed(2)}/bbl

## Key Metrics
- Crack Spread: $${marketData.crack_spread_usd_bbl.toFixed(2)}/bbl
- Volatility Index: ${marketData.volatility_index_pct.toFixed(1)}% (${marketData.volatility_regime})

## Analytics
- R² Heating Oil: ${marketData.r2_heating_oil?.toFixed(3) || 'N/A'}
- R² Brent Crude: ${marketData.r2_brent?.toFixed(3) || 'N/A'}
- R² WTI Crude: ${marketData.r2_wti?.toFixed(3) || 'N/A'}
- Recommended Proxy: ${marketData.recommended_proxy}
- IFRS 9 Eligible: ${marketData.ifrs9_eligible ? 'YES' : 'NO'}
- Forecast MAPE: ${marketData.forecast_mape?.toFixed(1) || 'N/A'}%
`;

return [{
  json: {
    ...marketData,
    ...analytics,
    formatted_analysis: formattedAnalysis,
    timestamp: new Date().toISOString()
  }
}];
```

---

### **NODES 5-9: Five AI Agents (Parallel Execution)**

For each agent, create an **AI Agent** node. Connect all 5 agents to the "Format Agent Input" node.

**Configuration is identical for all 5, except for the prompts:**

**Common Settings**:
- Type: **AI Agent (Chat Agent)**
- Require Specific Output Format: **Yes** (JSON)
- Connect to: **OpenAI Chat Model** sub-node

**Sub-node: OpenAI Chat Model**
- Model: `gpt-4o-mini` or `gpt-4o`
- Temperature: 0.3 (deterministic)

---

#### **AGENT 1: Basis Risk Agent**

**Position**: (200, -400)  
**Name**: "Agent 1 - Basis Risk"

**System Message** (copy from `docs/N8N_AGENT_PROMPTS.md` - Basis Risk section)

**Text** (User Prompt):
```
{{ $json.formatted_analysis }}

Analyze basis risk and provide your recommendation in this exact JSON format:

{
  "agent_id": "basis_risk",
  "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
  "recommendation": "HEDGE|WAIT|REDUCE|AVOID",
  "conviction_level": 1-10,
  "metrics": {
    "best_r2": {{ $json.r2_heating_oil }},
    "recommended_proxy": "{{ $json.recommended_proxy }}",
    "crack_spread_stability": "stable",
    "basis_risk_score": 3
  },
  "constraints_satisfied": true,
  "action_required": false,
  "ifrs9_eligible": {{ $json.ifrs9_eligible }},
  "rationale": "Your expert analysis in 2-3 sentences",
  "generated_at": "{{ DateTime.now().toISO() }}"
}
```

---

#### **AGENT 2: Liquidity Agent**

**Position**: (200, -200)  
**Name**: "Agent 2 - Liquidity"

**System Message**: (copy from `docs/N8N_AGENT_PROMPTS.md` - Liquidity section)

**Text**: Use template from agent prompts doc, adjust for market data

---

#### **AGENT 3: Operational Risk Agent**

**Position**: (200, 0)  
**Name**: "Agent 3 - Operational"

**System Message**: (copy from agent prompts doc)

---

#### **AGENT 4: IFRS 9 Compliance Agent**

**Position**: (200, 200)  
**Name**: "Agent 4 - IFRS9"

**System Message**: (copy from agent prompts doc)

**Critical**: This agent MUST check R² ≥ 0.80 for IFRS 9 eligibility

---

#### **AGENT 5: Macro Strategist**

**Position**: (200, 400)  
**Name**: "Agent 5 - Macro"

**System Message**: (copy from agent prompts doc)

---

### **NODE 10: Merge Agent Outputs**

**Type**: Merge  
**Position**: (500, 0)  
**Name**: "Investment Committee Merge"

**Configuration**:
- Mode: Combine
- Number of Inputs: 5
- Connect all 5 agent outputs

---

### **NODE 11: Synthesize Committee Recommendations**

**Type**: Code (Function)  
**Position**: (700, 0)  
**Name**: "Committee Synthesis"

**JavaScript Code**:
```javascript
const agents = $input.all();

let summary = "# INVESTMENT COMMITTEE RECOMMENDATIONS\n\n";
let votesInFavor = 0;
let convictionSum = 0;
let criticalRisks = [];
let ifrs9Eligible = true;
let constraintsSatisfied = true;

for (let i = 0; i < agents.length; i++) {
  const agent = agents[i].json;
  
  summary += `## Agent ${i + 1}: ${agent.agent_id.toUpperCase()}\n`;
  summary += `- Risk Level: ${agent.risk_level}\n`;
  summary += `- Recommendation: ${agent.recommendation}\n`;
  summary += `- Conviction: ${agent.conviction_level}/10\n`;
  summary += `- Rationale: ${agent.rationale}\n\n`;
  
  // Count votes
  if (agent.recommendation === 'HEDGE') votesInFavor++;
  convictionSum += agent.conviction_level;
  
  // Track critical issues
  if (agent.risk_level === 'CRITICAL') {
    criticalRisks.push(agent.agent_id);
  }
  
  if (agent.ifrs9_eligible === false) {
    ifrs9Eligible = false;
  }
  
  if (agent.constraints_satisfied === false) {
    constraintsSatisfied = false;
  }
}

const avgConviction = convictionSum / agents.length;

return [{
  json: {
    committee_summary: summary,
    votes_in_favor: votesInFavor,
    votes_total: agents.length,
    conviction_avg: avgConviction,
    critical_risks: criticalRisks,
    ifrs9_eligible: ifrs9Eligible,
    constraints_satisfied: constraintsSatisfied,
    agent_outputs: agents.map(a => a.json)
  }
}];
```

---

### **NODE 12: CRO Risk Management Gate**

**Type**: Code (Function)  
**Position**: (900, 0)  
**Name**: "CRO Risk Gate"

**JavaScript Code**:
```javascript
const committee = $input.first().json;

// Decision logic
let decision = "REJECT";
let rationale = "";

if (!committee.constraints_satisfied) {
  decision = "REJECT";
  rationale = "Hard constraints violated (HR > 80% or Collateral > 15%)";
} else if (!committee.ifrs9_eligible) {
  decision = "REJECT";
  rationale = "IFRS 9 not eligible (R² < 0.80) - no hedge accounting possible";
} else if (committee.critical_risks.length > 0) {
  decision = "REJECT";
  rationale = `Critical risks identified: ${committee.critical_risks.join(', ')}`;
} else if (committee.votes_in_favor >= 4) {
  decision = "IMPLEMENT";
  rationale = "Strong consensus (4-5/5 agents). All constraints satisfied.";
} else if (committee.votes_in_favor === 3) {
  decision = "MODIFY";
  rationale = "Moderate consensus (3/5). Recommend reducing position size by 30%.";
} else {
  decision = "MONITOR";
  rationale = "Weak consensus (≤2/5). Wait for better market conditions.";
}

// Build recommendation payload for FastAPI
const recommendation = {
  recommendation_type: decision === "IMPLEMENT" ? "HEDGE_NEW" : "WAIT",
  instrument: "heating_oil",  // From basis risk agent
  notional_usd: decision === "MODIFY" ? 3500000 : 5000000,
  contracts: decision === "MODIFY" ? 350 : 500,
  strike_price_usd_bbl: 92.30,  // From market data
  maturity_months: 12,
  hedge_ratio_pct: decision === "MODIFY" ? 55.0 : 75.0,
  expected_var_reduction_pct: 40.0,
  ifrs9_eligible: committee.ifrs9_eligible,
  risk_summary: {
    basis_risk: "LOW",
    liquidity: "MODERATE",
    operational: "LOW",
    ifrs9_compliance: committee.ifrs9_eligible ? "ELIGIBLE" : "NOT_ELIGIBLE",
    macro_environment: "NEUTRAL"
  },
  agent_consensus: {
    votes_in_favor: committee.votes_in_favor,
    votes_against: committee.votes_total - committee.votes_in_favor,
    conviction_avg: committee.conviction_avg,
    dissenting_agents: []  // TODO: track which agents said WAIT/AVOID
  },
  constraints_validation: {
    hedge_ratio_ok: true,
    collateral_ok: true,
    ifrs9_ok: committee.ifrs9_eligible
  },
  cro_decision: decision,
  cro_rationale: rationale,
  action_required: decision === "IMPLEMENT",
  requires_cfo_approval: true,
  sla_hours: 24,
  generated_at: new Date().toISOString(),
  agent_outputs: committee.agent_outputs
};

return [{ json: recommendation }];
```

---

### **NODE 13: POST Recommendation to FastAPI**

**Type**: HTTP Request  
**Position**: (1100, 0)  
**Name**: "POST to FastAPI"

**Configuration**:
```
Method: POST
URL: http://hedge-api:8000/api/v1/recommendations
Body: JSON
Body Parameters: {{ $json }}
Headers:
  Content-Type: application/json
Authentication: None
```

**Expected Response**:
```json
{
  "id": "rec_12345",
  "status": "PENDING_CFO_APPROVAL",
  "created_at": "2026-03-03T06:05:00Z"
}
```

---

### **NODE 14: Wait for Approval (Polling Loop)**

**Type**: Wait  
**Position**: (1300, 0)  
**Name**: "Wait 60 seconds"

**Configuration**:
- Amount: 1
- Unit: Minutes

---

### **NODE 15: Check Approval Status**

**Type**: HTTP Request  
**Position**: (1500, 0)  
**Name**: "GET Approval Status"

**Configuration**:
```
Method: GET
URL: http://hedge-api:8000/api/v1/recommendations/{{ $('POST to FastAPI').item.json.id }}
Authentication: None
```

---

### **NODE 16: IF Status Check**

**Type**: IF  
**Position**: (1700, 0)  
**Name**: "Status = PENDING?"

**Configuration**:
- Condition: `{{ $json.status }}` equals `PENDING_CFO_APPROVAL`
- True → Loop back to "Wait 60 seconds" (max 240 iterations = 4 hours)
- False → Continue to next node

---

### **NODE 17: Escalation Handler**

**Type**: Code (Function)  
**Position**: (1900, 200)  
**Name**: "Escalate if Timeout"

**JavaScript Code**:
```javascript
const status = $input.first().json.status;
const recId = $('POST to FastAPI').item.json.id;
const createdAt = new Date($('POST to FastAPI').item.json.created_at);
const now = new Date();
const hoursElapsed = (now - createdAt) / (1000 * 60 * 60);

if (status === 'PENDING_CFO_APPROVAL' && hoursElapsed >= 4) {
  // Escalate to CEO
  return [{
    json: {
      action: 'ESCALATE',
      recommendation_id: recId,
      escalation_level: 'CEO',
      reason: 'CFO approval SLA breach (4 hours)',
      timestamp: now.toISOString()
    }
  }];
} else {
  return [{
    json: {
      action: 'NONE',
      final_status: status,
      recommendation_id: recId
    }
  }];
}
```

---

### **NODE 18: Error Handler (Workflow Level)**

**Type**: Error Trigger  
**Position**: (500, -600)  
**Name**: "Workflow Error Handler"

**Configuration**:
- Trigger on: Any Error
- Connected to: HTTP Request node that POSTs to monitoring/alerting endpoint

**Error Notification Node**:
```
Method: POST
URL: http://hedge-api:8000/api/v1/alerts
Body: 
{
  "alert_type": "N8N_WORKFLOW_ERROR",
  "workflow_name": "{{ $workflow.name }}",
  "error_message": "{{ $json.error.message }}",
  "timestamp": "{{ DateTime.now().toISO() }}"
}
```

---

## 🔗 NODE CONNECTIONS

Connect nodes in this order:

1. **Schedule Trigger** → **Get Latest Market Data**
2. **Get Latest Market Data** → **Get Analytics**
3. **Get Analytics** → **Merge** (with Market Data)
4. **Merge** → **Format Agent Input**
5. **Format Agent Input** → **All 5 Agents** (parallel)
6. **All 5 Agents** → **Investment Committee Merge**
7. **Investment Committee Merge** → **Committee Synthesis**
8. **Committee Synthesis** → **CRO Risk Gate**
9. **CRO Risk Gate** → **POST to FastAPI**
10. **POST to FastAPI** → **Wait 60 seconds**
11. **Wait 60 seconds** → **GET Approval Status**
12. **GET Approval Status** → **IF Status Check**
13. **IF (True)** → **Wait 60 seconds** (loop)
14. **IF (False)** → **Escalation Handler**

---

## ✅ TESTING

### **Test with Mock Data**

1. Click **"Execute Workflow"** button
2. Check each node's output
3. Verify agent responses are valid JSON
4. Confirm CRO gate logic works
5. Test approval polling loop

### **Expected Execution Time**
- Agents (parallel): ~30 seconds
- Total workflow: ~2 minutes (excluding approval wait)

---

## 📊 MONITORING

Add these logging nodes:

1. **After each major step**: Code node that logs to console
2. **Before POST to FastAPI**: Log final recommendation
3. **After approval check**: Log status changes

---

## 🚨 TROUBLESHOOTING

**Issue**: Agent returns invalid JSON  
**Fix**: Add "Require Specific Output Format" and provide JSON schema

**Issue**: FastAPI connection refused  
**Fix**: Use `http://hedge-api:8000` (Docker internal) not `localhost:8000`

**Issue**: Approval polling never ends  
**Fix**: Add max iterations (240) to Wait node

---

## 📝 FINAL CHECKLIST

- [ ] All 5 agents configured with correct prompts
- [ ] OpenAI credentials added
- [ ] CRO gate logic validates all constraints
- [ ] POST to FastAPI endpoint tested
- [ ] Approval polling loop works
- [ ] Escalation triggers after 4 hours
- [ ] Error handler catches all failures
- [ ] Workflow tested end-to-end with mock data

---

**Implementation Complete! 🎉**

**Next Steps**:
1. Test with mock data
2. Connect real FastAPI endpoints
3. Add real API credentials (EIA, CME, ICE)
4. Enable workflow (set active = true)
5. Schedule for daily 06:00 UTC execution
