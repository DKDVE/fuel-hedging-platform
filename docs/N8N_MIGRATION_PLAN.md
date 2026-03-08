# 🔄 N8N WORKFLOW MIGRATION PLAN
**From**: TSLA AI Hedge Fund  
**To**: Fuel Hedging Advisor  
**Date**: March 3, 2026

---

## 📊 EXISTING WORKFLOW ANALYSIS

### **Current Structure (TSLA)**
- **Trigger**: Telegram (ticker symbol input)
- **Data Sources** (4 HTTP nodes):
  1. Daily Market data (Polygon.io stock prices)
  2. Company Fundamentals (Polygon.io ticker info)
  3. Financial Statements (Polygon.io financials)
  4. News & Sentiment (NewsAPI)
- **Data Aggregator**: Merge node (combines 4 sources)
- **Market Intelligence Hub**: Aggregate node
- **Code Node**: Formats data for agents
- **5 AI Agents** (investment personas):
  1. Warren Buffett (value investing)
  2. Charlie Munger (mental models)
  3. Bill Ackman (activist investing)
  4. Steve Cohen (multi-strategy trading)
  5. Ray Dalio (macro/risk parity)
- **Wait Nodes** (4): Stagger agent execution (15s, 25s, 35s, 45s)
- **Investment Committee**: Merge 5 agent outputs
- **Code1**: Summarize committee recommendations
- **Risk Management**: CRO synthesis
- **Code2**: Format for Telegram output
- **Telegram Output** (4 nodes): Summary + 3 parts

### **Total Nodes**: 37
- HTTP Request: 4
- Merge: 2
- Aggregate: 1
- Code: 3
- AI Agent: 6 (5 investors + 1 CRO)
- OpenAI Chat Model: 6
- Memory: 6
- Wait: 4
- Telegram: 5 (1 trigger + 4 output)

---

## 🎯 TARGET WORKFLOW (FUEL HEDGING)

### **New Structure**
- **Trigger**: Schedule (daily 06:00 UTC) OR Webhook (manual trigger)
- **Data Sources** (3 HTTP nodes):
  1. EIA API → Jet fuel spot prices
  2. CME API → Heating oil + WTI futures
  3. ICE API → Brent crude futures
- **Data Aggregator**: Code node (computes crack spread, volatility regime)
- **Market Intelligence Hub**: HTTP GET to FastAPI (forecast + basis risk)
- **5 AI Agents** (fuel hedging personas):
  1. **Basis Risk Agent** → Proxy selection, R² analysis
  2. **Liquidity Agent** → Market depth, collateral management
  3. **Operational Agent** → Execution risk, transaction costs
  4. **IFRS9 Compliance Agent** → Hedge accounting eligibility
  5. **Macro Agent** → Oil market trends, geopolitics
- **Investment Committee**: Merge 5 agent outputs + synthesize
- **CRO Risk Gate**: Validates constraints (HR ≤ 80%, collateral ≤ 15%)
- **Post-Committee Webhook**: HTTP POST to FastAPI `/api/v1/recommendations`
- **Approval Polling Loop**: GET `/api/v1/recommendations/{id}` every 60s
- **Escalation Wait**: 4 hours → PATCH escalation endpoint if still PENDING
- **Error Handler**: Workflow-level catch-all

### **Total Nodes**: ~30-35
- Schedule Trigger: 1
- HTTP Request (data): 4 (EIA, CME, ICE, FastAPI)
- Code (aggregator): 1
- AI Agent: 6 (5 domain + 1 CRO)
- OpenAI Chat Model: 6
- Memory: 6
- HTTP Request (webhook): 2 (POST recommendation, GET status)
- IF: 2 (status check, escalation check)
- Wait: 2 (approval poll 60s, escalation 4h)
- Error Handler: 1

---

## 🔄 NODE-BY-NODE MIGRATION MAP

| Old Node | Old Purpose | New Node | New Purpose | Status |
|----------|-------------|----------|-------------|--------|
| **Telegram Trigger** | User input (ticker) | **Schedule Trigger** | Daily 06:00 UTC + Webhook | ⏳ |
| **Daily Market data** | Polygon API (TSLA prices) | **EIA API** | Jet fuel spot prices | ⏳ |
| **Company Fundamentals** | Polygon API (TSLA info) | **CME API** | Heating oil + WTI futures | ⏳ |
| **Financial Statements** | Polygon API (TSLA financials) | **ICE API** | Brent crude futures | ⏳ |
| **News & Sentiment** | NewsAPI | **Volatility Calc** | Compute volatility index | ⏳ |
| **Data aggregator** (Merge) | Combines 4 sources | **Data aggregator** (Code) | Merge + compute crack spread | ⏳ |
| **Market intelligence hub** (Aggregate) | Aggregate data | **Market Intelligence Hub** (HTTP GET) | FastAPI forecast + basis risk | ⏳ |
| **Code** | Format for agents | **Code** (Format) | Format for fuel agents | ⏳ |
| **Warren Buffett** (Agent) | Value investing | **Basis Risk Agent** | Proxy selection, R² | ⏳ |
| **Charlie Munger** (Agent) | Mental models | **Liquidity Agent** | Market depth, collateral | ⏳ |
| **Bill Ackman** (Agent) | Activist investing | **Operational Agent** | Execution, transaction costs | ⏳ |
| **Steve Cohen** (Agent) | Multi-strategy trading | **IFRS9 Agent** | Hedge accounting compliance | ⏳ |
| **Ray Dalio** (Agent) | Macro/risk parity | **Macro Agent** | Oil markets, geopolitics | ⏳ |
| **Wait1-4** | Stagger execution (15-45s) | **Remove** | Parallel execution | ❌ |
| **Investment Committee** (Merge) | Combine agent outputs | **Investment Committee** (Merge) | Combine 5 agent outputs | ⏳ |
| **Code1** | Summarize committee | **Code1** (Committee Summary) | Synthesize consensus | ⏳ |
| **Risk Management** (Agent) | CRO final decision | **CRO Risk Gate** (Code) | Validate constraints | ⏳ |
| **Code2** | Format Telegram output | **Code2** (Webhook Payload) | Format FastAPI payload | ⏳ |
| **Telegram Output** (4 nodes) | Send to Telegram | **HTTP POST** | Send to FastAPI | ⏳ |
| **N/A** | N/A | **Approval Poll Loop** | GET status every 60s | ➕ NEW |
| **N/A** | N/A | **Escalation Wait** | 4h → escalate if PENDING | ➕ NEW |
| **N/A** | N/A | **Error Handler** | Workflow-level catch | ➕ NEW |

---

## 📝 DETAILED MIGRATION TASKS

### **TASK 7.1: Replace HTTP Request Nodes** ✅ NEXT

#### **Node 1: EIA API (Jet Fuel Spot)**
```javascript
// HTTP Request Node Configuration
{
  "name": "EIA - Jet Fuel Spot",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "url": "https://api.eia.gov/v2/petroleum/pri/spt/data/",
    "authentication": "genericCredentialType",
    "genericAuthType": "queryAuth",
    "sendQuery": true,
    "queryParameters": {
      "parameters": [
        {
          "name": "api_key",
          "value": "={{ $credentials.eia_api_key }}"
        },
        {
          "name": "frequency",
          "value": "daily"
        },
        {
          "name": "data[0]",
          "value": "value"
        },
        {
          "name": "facets[product][]",
          "value": "EPD2F"  // Jet Fuel, US Gulf Coast
        },
        {
          "name": "start",
          "value": "={{ DateTime.now().minus({days: 365}).toFormat('yyyy-MM-dd') }}"
        },
        {
          "name": "sort[0][column]",
          "value": "period"
        },
        {
          "name": "sort[0][direction]",
          "value": "desc"
        }
      ]
    }
  }
}
```

#### **Node 2: CME API (Heating Oil + WTI)**
```javascript
{
  "name": "CME - Heating Oil & WTI",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "url": "https://www.cmegroup.com/market-data/delayed-quotes/energy.json",
    "authentication": "headerAuth",
    "sendQuery": true,
    "queryParameters": {
      "parameters": [
        {
          "name": "codes",
          "value": "HO,CL"  // HO=Heating Oil, CL=WTI Crude
        }
      ]
    },
    "headerParameters": {
      "parameters": [
        {
          "name": "X-API-Key",
          "value": "={{ $credentials.cme_api_key }}"
        }
      ]
    }
  }
}
```

#### **Node 3: ICE API (Brent Crude)**
```javascript
{
  "name": "ICE - Brent Crude",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "url": "https://www.theice.com/marketdata/DelayedMarkets.shtml",
    "authentication": "headerAuth",
    "sendQuery": true,
    "queryParameters": {
      "parameters": [
        {
          "name": "contractCode",
          "value": "B"  // Brent Crude
        }
      ]
    },
    "headerParameters": {
      "parameters": [
        {
          "name": "Authorization",
          "value": "Bearer ={{ $credentials.ice_api_key }}"
        }
      ]
    }
  }
}
```

#### **Node 4: Volatility Calculation (Derived)**
```javascript
// Code Node
{
  "name": "Calculate Volatility Index",
  "type": "n8n-nodes-base.code",
  "parameters": {
    "jsCode": `
// Get recent price data from previous 30 days
const prices = $input.all().map(item => item.json.value);

// Calculate daily returns
const returns = [];
for (let i = 1; i < prices.length; i++) {
  returns.push((prices[i] - prices[i-1]) / prices[i-1]);
}

// Calculate volatility (standard deviation of returns * sqrt(252) for annualized)
const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length;
const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100;

return [{
  json: {
    volatility_index: volatility,
    volatility_regime: volatility < 20 ? 'LOW' : volatility < 40 ? 'MODERATE' : 'HIGH'
  }
}];
    `
  }
}
```

---

### **TASK 7.2: Update Data Aggregator** ⏳

#### **Code Node: Compute Crack Spread**
```javascript
{
  "name": "Data Aggregator & Crack Spread",
  "type": "n8n-nodes-base.code",
  "parameters": {
    "jsCode": `
const items = $input.all();

// Extract prices from each API response
let jetFuelSpot = 0;
let heatingOilFutures = 0;
let brentFutures = 0;
let wtiFutures = 0;
let volatilityIndex = 0;

for (const item of items) {
  if (item.json.source === 'eia') {
    jetFuelSpot = item.json.data.response.data[0].value;
  } else if (item.json.source === 'cme_ho') {
    heatingOilFutures = item.json.last;
  } else if (item.json.source === 'cme_wti') {
    wtiFutures = item.json.last;
  } else if (item.json.source === 'ice_brent') {
    brentFutures = item.json.settlementPrice;
  } else if (item.json.source === 'volatility') {
    volatilityIndex = item.json.volatility_index;
  }
}

// Calculate crack spread (Jet Fuel Spot - Heating Oil Futures)
const crackSpread = jetFuelSpot - heatingOilFutures;

// Classify volatility regime
const volatilityRegime = volatilityIndex < 20 ? 'LOW' : 
                          volatilityIndex < 40 ? 'MODERATE' : 
                          volatilityIndex < 60 ? 'HIGH' : 'CRITICAL';

// Return aggregated dataset
return [{
  json: {
    date: new Date().toISOString(),
    jet_fuel_spot_usd_bbl: jetFuelSpot,
    heating_oil_futures_usd_bbl: heatingOilFutures,
    brent_crude_futures_usd_bbl: brentFutures,
    wti_crude_futures_usd_bbl: wtiFutures,
    crack_spread_usd_bbl: crackSpread,
    volatility_index_pct: volatilityIndex,
    volatility_regime: volatilityRegime,
    formatted_analysis: \`
# FUEL HEDGING MARKET DATA
Date: \${new Date().toISOString().split('T')[0]}

## Spot & Futures Prices
- Jet Fuel Spot (US Gulf Coast): $\${jetFuelSpot.toFixed(2)}/bbl
- Heating Oil Futures (NYMEX): $\${heatingOilFutures.toFixed(2)}/bbl
- Brent Crude Futures (ICE): $\${brentFutures.toFixed(2)}/bbl
- WTI Crude Futures (NYMEX): $\${wtiFutures.toFixed(2)}/bbl

## Key Metrics
- Crack Spread: $\${crackSpread.toFixed(2)}/bbl
- Volatility Index: \${volatilityIndex.toFixed(1)}% (\${volatilityRegime})

## Market Context
\${volatilityRegime === 'CRITICAL' ? 
  '⚠️ ALERT: Volatility in CRITICAL range - consider defensive positioning' :
  volatilityRegime === 'HIGH' ?
  '⚠️ CAUTION: High volatility - monitor closely' :
  '✅ Normal market conditions'
}
\`
  }
}];
    `
  }
}
```

---

### **TASK 7.3: Market Intelligence Hub** ⏳

#### **HTTP GET to FastAPI**
```javascript
{
  "name": "Market Intelligence Hub",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "url": "={{ $env.FASTAPI_INTERNAL_URL }}/api/v1/analytics/forecast/latest",
    "method": "GET",
    "authentication": "none",
    "options": {
      "timeout": 30000
    }
  }
}
```

#### **Code Node: Combine Market Data + Analytics**
```javascript
{
  "name": "Combine Market Data + Analytics",
  "type": "n8n-nodes-base.code",
  "parameters": {
    "jsCode": `
const marketData = $('Data Aggregator & Crack Spread').first().json;
const forecast = $input.first().json;

// Fetch basis risk separately
const basisRiskResponse = await fetch(\`\${process.env.FASTAPI_INTERNAL_URL}/api/v1/analytics/basis-risk/latest\`);
const basisRisk = await basisRiskResponse.json();

return [{
  json: {
    ...marketData,
    forecast_30day: forecast.forecast_values,
    forecast_mape: forecast.mape,
    var_hedged: forecast.var_hedged || 0,
    var_unhedged: forecast.var_unhedged || 0,
    r2_heating_oil: basisRisk.r2_heating_oil,
    r2_brent: basisRisk.r2_brent,
    r2_wti: basisRisk.r2_wti,
    recommended_proxy: basisRisk.recommended_proxy,
    ifrs9_eligible: basisRisk.ifrs9_eligible
  }
}];
    `
  }
}
```

---

### **TASK 7.4: Replace All 5 Agent System Prompts** ⏳

Will continue in next response...

---

**Migration Status**: 🔄 **IN PROGRESS**  
**Completed Tasks**: 0 / 10  
**Next Task**: 7.1 - Replace HTTP Request nodes
