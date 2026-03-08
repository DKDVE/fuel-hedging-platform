# 🚀 N8N WORKFLOW - QUICK START GUIDE

**Start Time**: ___:___ (track your progress)  
**Estimated Time**: 2-3 hours  
**N8N URL**: http://localhost:5678

---

## 📋 PRE-BUILD CHECKLIST

### **1. Access N8N (2 minutes)**
- [ ] Open browser: http://localhost:5678
- [ ] Create account (if first time) - use any email/password for local instance
- [ ] You should see the n8n dashboard

### **2. Set Up Credentials (5 minutes)**

Before building any nodes, add these credentials:

#### **A. OpenAI API Credential**
1. Click **Settings** (gear icon, top right)
2. Click **Credentials** → **New**
3. Search for: **"OpenAI"**
4. Fill in:
   - **Name**: `OpenAI - Fuel Hedging`
   - **API Key**: `your-openai-api-key` (get from https://platform.openai.com/api-keys)
5. Click **Save**

#### **B. Generic HTTP Auth (Optional - for later)**
For EIA, CME, ICE APIs when you're ready to connect real data sources.
- For now, we'll use **mock data** so you can test immediately.

### **3. Create New Workflow (1 minute)**
- [ ] Click **Workflows** (left sidebar)
- [ ] Click **+ Add workflow**
- [ ] Name it: **"Fuel Hedging Advisor - Production v1"**
- [ ] Click **Save** (top right)

---

## 🎯 BUILD STRATEGY

We'll build the workflow in **4 sections**:

### **Section 1: Trigger & Data (3 nodes)** - 15 minutes
1. Schedule Trigger
2. Mock Market Data (Code node)
3. Format Agent Input (Code node)

### **Section 2: AI Agents (15 nodes)** - 90 minutes
4-8. Five AI Agent nodes (each with OpenAI Chat Model + Memory sub-nodes)
9. Merge Agent Outputs

### **Section 3: Decision Logic (5 nodes)** - 30 minutes
10. Committee Synthesis (Code node)
11. CRO Risk Gate (Code node)
12. POST to FastAPI (HTTP Request)
13. IF node (check for success)
14. Final output

### **Section 4: Approval Loop (Optional)** - 30 minutes
Can be added later when FastAPI endpoints are ready

---

## 📍 SECTION 1: TRIGGER & DATA (START HERE)

### **NODE 1: Schedule Trigger**

**Purpose**: Run workflow daily at 06:00 UTC

**Steps**:
1. Click **+** button in canvas
2. Search: **"Schedule Trigger"**
3. Click on **Schedule Trigger** node
4. Configure:
   - **Trigger Interval**: Cron
   - **Cron Expression**: `0 6 * * *`
   - **Description**: "Triggers daily analytics pipeline at 06:00 UTC"
5. Click **Execute Node** to test (it won't execute on schedule, but will initialize)
6. **Position**: Drag to far left of canvas (start point)

✅ **Checkpoint**: You should see the Schedule Trigger node on canvas

---

### **NODE 2: Mock Market Data**

**Purpose**: Simulate market data (replace with real APIs later)

**Steps**:
1. Click **+** button in canvas (or drag from Schedule Trigger output)
2. Search: **"Code"**
3. Select **Code** node (JavaScript function)
4. **Name**: Change name to `Mock Market Data`
5. **Mode**: Ensure "Run Once for All Items" is selected
6. **JavaScript Code**: Copy-paste this:

```javascript
// Mock Market Data - Replace with real API calls later
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

7. Click **Execute Node** to test
8. You should see output data in the right panel
9. **Connect**: Drag line from Schedule Trigger → Mock Market Data

✅ **Checkpoint**: Mock data should show in output with all price fields

---

### **NODE 3: Format Agent Input**

**Purpose**: Format market data into readable text for AI agents

**Steps**:
1. Click **+** after Mock Market Data node
2. Search: **"Code"**
3. Select **Code** node
4. **Name**: Change to `Format Agent Input`
5. **JavaScript Code**: Copy-paste this:

```javascript
const data = $input.first().json;

// Format data for AI agents
const formattedAnalysis = `
# FUEL HEDGING MARKET DATA
Date: ${data.date}

## Spot & Futures Prices
- Jet Fuel Spot (US Gulf Coast): $${data.jet_fuel_spot_usd_bbl.toFixed(2)}/bbl
- Heating Oil Futures (NYMEX): $${data.heating_oil_futures_usd_bbl.toFixed(2)}/bbl
- Brent Crude Futures (ICE): $${data.brent_crude_futures_usd_bbl.toFixed(2)}/bbl
- WTI Crude Futures (NYMEX): $${data.wti_crude_futures_usd_bbl.toFixed(2)}/bbl

## Key Metrics
- Crack Spread: $${data.crack_spread_usd_bbl.toFixed(2)}/bbl
- Volatility Index: ${data.volatility_index_pct.toFixed(1)}% (${data.volatility_regime})

## Analytics
- R² Heating Oil: ${data.r2_heating_oil.toFixed(3)}
- R² Brent Crude: ${data.r2_brent.toFixed(3)}
- R² WTI Crude: ${data.r2_wti.toFixed(3)}
- Recommended Proxy: ${data.recommended_proxy}
- IFRS 9 Eligible: ${data.ifrs9_eligible ? 'YES' : 'NO'}
- Forecast MAPE: ${data.forecast_mape.toFixed(1)}%
`;

return [{
  json: {
    ...data,
    formatted_analysis: formattedAnalysis,
    timestamp: new Date().toISOString()
  }
}];
```

6. Click **Execute Node** to test
7. Check output - you should see all original data + `formatted_analysis` field
8. **Connect**: Mock Market Data → Format Agent Input

✅ **Checkpoint**: Output should show formatted markdown text in `formatted_analysis` field

---

## 🎯 PROGRESS TRACKER

Mark off as you complete:

### Section 1: Trigger & Data
- [ ] Node 1: Schedule Trigger ✓
- [ ] Node 2: Mock Market Data ✓
- [ ] Node 3: Format Agent Input ✓

### Section 2: AI Agents (Next)
- [ ] Node 4: Basis Risk Agent
- [ ] Node 5: Liquidity Agent
- [ ] Node 6: Operational Agent
- [ ] Node 7: IFRS9 Agent
- [ ] Node 8: Macro Agent
- [ ] Node 9: Merge Agents

### Section 3: Decision Logic
- [ ] Node 10: Committee Synthesis
- [ ] Node 11: CRO Risk Gate
- [ ] Node 12: POST to FastAPI
- [ ] Node 13: Final Check

---

## 🛑 PAUSE HERE - SECTION 1 COMPLETE

**Before continuing to Section 2 (AI Agents):**

1. ✅ Verify all 3 nodes execute successfully
2. ✅ Save your workflow (top right)
3. ✅ Take a screenshot (optional, for reference)

**Time Check**: Section 1 should take ~15 minutes

---

## ▶️ READY FOR SECTION 2?

When ready to continue, I'll guide you through creating the 5 AI agents.

**Each agent requires**:
- 1 AI Agent node (main)
- 1 OpenAI Chat Model sub-node
- 1 Memory Window sub-node (optional but recommended)

This is the most time-consuming part (~90 minutes) but I have all the prompts ready to copy-paste.

**Let me know when Section 1 is complete and you're ready for Section 2!**

---

## 💡 TIPS

- **Save frequently**: n8n auto-saves, but click Save button to be sure
- **Test each node**: Use "Execute Node" after creating each one
- **Check output**: Right panel shows node output data
- **Zoom in/out**: Use mouse wheel or touchpad to zoom canvas
- **Move canvas**: Click and drag on empty space
- **Undo**: Ctrl+Z (Cmd+Z on Mac)

---

## 🆘 TROUBLESHOOTING

**Issue**: Node execution fails  
**Fix**: Check the error message in right panel, verify input data

**Issue**: Can't find a node type  
**Fix**: Type exact name in search (e.g., "Schedule Trigger")

**Issue**: Connection line won't attach  
**Fix**: Drag from output circle (right side) to input circle (left side)

**Issue**: Lost on canvas  
**Fix**: Press F (fit to view) or use minimap (bottom right)

---

**🎯 YOUR CURRENT TASK: Complete Section 1 (3 nodes above)**

Report back when done, and I'll guide you through Section 2 (AI Agents)!
