# 🤖 N8N WORKFLOW - SECTION 2: AI AGENTS

**Prerequisite**: Section 1 complete (3 nodes: Trigger → Mock Data → Format Input)

**This Section**: Create 5 AI Agent nodes  
**Time**: ~90 minutes (18 min per agent)  
**Complexity**: Medium (repetitive but detailed)

---

## 🎯 OVERVIEW

You'll create **5 identical agent structures**, each with:
1. **AI Agent** (main node) - with custom system prompt
2. **OpenAI Chat Model** (sub-node) - connects to OpenAI API
3. **Memory Window** (sub-node) - gives agents conversation memory

**Strategy**: Build ONE complete agent first, then duplicate and modify for others.

---

## 🚀 AGENT 1: BASIS RISK AGENT (BUILD THIS FIRST)

### **Step 1: Create AI Agent Node**

1. Click **+** after "Format Agent Input" node
2. Search: **"AI Agent"**
3. Select **"AI Agent"** (should show "Agent" with brain icon)
4. **Name**: Change to `Agent 1 - Basis Risk`

### **Step 2: Configure Agent Settings**

In the AI Agent node panel:

**Prompt Section**:
- **Prompt Type**: Select **"Define below"**
- **Text**: Click in the text area and paste this:

```
{{ $json.formatted_analysis }}

# YOUR TASK

You are a Basis Risk Specialist analyzing jet fuel hedging. Based on the market data above, provide your recommendation.

**CRITICAL**: You MUST respond with ONLY valid JSON in this exact format:

{
  "agent_id": "basis_risk",
  "risk_level": "LOW",
  "recommendation": "HEDGE",
  "conviction_level": 8,
  "metrics": {
    "best_r2": 0.87,
    "recommended_proxy": "heating_oil",
    "crack_spread_stability": "stable",
    "basis_risk_score": 3
  },
  "constraints_satisfied": true,
  "action_required": false,
  "ifrs9_eligible": true,
  "rationale": "R² of 0.87 with heating oil exceeds IFRS 9 threshold of 0.80. Crack spread is stable at $3.20/bbl. Low volatility regime supports hedging. Recommend heating oil futures as optimal proxy.",
  "generated_at": "{{ DateTime.now().toISO() }}"
}

**ANALYSIS GUIDELINES**:
- R² ≥ 0.85: LOW risk, HEDGE recommended
- R² 0.80-0.85: MODERATE risk, HEDGE with caution  
- R² 0.65-0.80: HIGH risk, consider alternatives
- R² < 0.65: CRITICAL risk, AVOID

Current R²: {{ $json.r2_heating_oil }}
IFRS 9 Eligible: {{ $json.r2_heating_oil >= 0.80 ? "YES" : "NO" }}

Provide your expert analysis with specific numbers from the data.
```

**Options Section** (click to expand):
- **System Message**: Paste this:

```
You are a Basis Risk Specialist for aviation fuel hedging. Your role is to analyze correlation between jet fuel spot prices and hedging proxies (heating oil, Brent crude, WTI crude).

EXPERTISE:
- Statistical correlation analysis (R² interpretation)
- Crack spread dynamics
- IFRS 9 hedge effectiveness testing (R² ≥ 0.80 required)
- Proxy selection for illiquid commodities

RESPONSE FORMAT:
You MUST respond with valid JSON only. No additional text before or after the JSON.
```

- **Require Specific Output Format**: Toggle **ON** ✅
- **Output Format**: Select **"JSON"**

### **Step 3: Add OpenAI Chat Model Sub-Node**

1. In the Agent node panel, look for **"Model"** section
2. Click **"+"** button next to "Model"
3. Search: **"OpenAI Chat Model"**
4. Select it
5. Configure:
   - **Credentials**: Select `OpenAI - Fuel Hedging` (you created earlier)
   - **Model**: Select `gpt-4o-mini` (or `gpt-4o` if you prefer)
   - **Temperature**: Set to `0.3` (for more deterministic responses)
6. Click **Back to Agent** (or close sub-node panel)

### **Step 4: Add Memory Sub-Node (Optional)**

1. In Agent node panel, find **"Memory"** section
2. Click **"+"** next to Memory
3. Search: **"Window Buffer Memory"**
4. Select it
5. Configure:
   - **Session Key Type**: Select **"Custom Key"**
   - **Session Key**: Type `fuel_hedge_session`
   - **Context Window Length**: Leave default (5)
6. Click **Back to Agent**

### **Step 5: Test Agent 1**

1. Click **"Execute Node"** on Agent 1
2. Wait 5-10 seconds (OpenAI API call)
3. Check output in right panel
4. **Expected**: JSON object with all required fields
5. **If error**: Check that OpenAI credentials are correct

✅ **Checkpoint**: Agent 1 should return valid JSON with basis risk analysis

---

## 📐 POSITIONING AGENTS ON CANVAS

Before creating more agents, let's position them:

**Layout Strategy** (vertical spread):
```
Format Agent Input
        |
    ----+----
    |   |   |   |   |
   A1  A2  A3  A4  A5
```

**Positioning**:
1. Select Agent 1 node
2. Drag it **DOWN** about 200px from Format Input
3. We'll place other agents in parallel

---

## 🔄 DUPLICATE & MODIFY FOR AGENTS 2-5

Now that Agent 1 is working, we'll **duplicate it** and change prompts:

### **AGENT 2: LIQUIDITY AGENT**

1. **Right-click** Agent 1 node → **Duplicate**
2. Drag duplicate to the right of Agent 1 (parallel position)
3. **Rename**: `Agent 2 - Liquidity`
4. **Modify Prompt Text**: Replace with:

```
{{ $json.formatted_analysis }}

# YOUR TASK

You are a Liquidity & Collateral Specialist. Analyze market depth and collateral requirements.

**CRITICAL**: Respond with ONLY valid JSON:

{
  "agent_id": "liquidity",
  "risk_level": "MODERATE",
  "recommendation": "HEDGE",
  "conviction_level": 7,
  "metrics": {
    "market_depth_score": 8,
    "collateral_utilization_pct": 12.5,
    "bid_ask_spread_bps": 1.5,
    "execution_feasibility": "immediate"
  },
  "constraints_satisfied": true,
  "action_required": false,
  "ifrs9_eligible": null,
  "rationale": "Heating oil futures have strong liquidity with daily volume >80k contracts. Estimated collateral impact 12.5% (under 15% limit). Bid-ask spreads tight. Execution feasible.",
  "generated_at": "{{ DateTime.now().toISO() }}"
}

**CONSTRAINTS**:
- Collateral Limit: 15% (hard cap)
- Volume target: >50,000 contracts/day
- Bid-ask spread: <0.02%

Analyze liquidity conditions and collateral impact for proposed hedge.
```

5. **System Message**: Replace with:

```
You are a Liquidity & Collateral Specialist for aviation fuel hedging. You ensure sufficient market depth exists and collateral requirements remain within limits.

EXPERTISE:
- Futures market liquidity analysis
- Margin and collateral requirements (15% hard cap)
- Market impact estimation
- Counterparty credit risk

RESPONSE FORMAT:
You MUST respond with valid JSON only.
```

6. **Test**: Execute node to verify it works
7. **Connect**: Drag connection from "Format Agent Input" → Agent 2

✅ **Checkpoint**: Agent 2 should return liquidity analysis JSON

---

### **AGENT 3: OPERATIONAL RISK OFFICER**

1. **Duplicate** Agent 2
2. Drag to right of Agent 2
3. **Rename**: `Agent 3 - Operational`
4. **Prompt Text**: Replace with:

```
{{ $json.formatted_analysis }}

# YOUR TASK

You are an Operational Risk Officer assessing execution risk and transaction costs.

**CRITICAL**: Respond with ONLY valid JSON:

{
  "agent_id": "operational",
  "risk_level": "LOW",
  "recommendation": "HEDGE",
  "conviction_level": 8,
  "metrics": {
    "transaction_cost_pct": 0.19,
    "complexity_score": 2,
    "execution_timeline_days": 1,
    "operational_capacity_pct": 80
  },
  "constraints_satisfied": true,
  "action_required": false,
  "ifrs9_eligible": null,
  "rationale": "Plain vanilla futures with low complexity (score 2/10). Transaction costs estimated at 0.19% (well below 0.5% threshold). Team has capacity. Settlement T+2. Operationally feasible.",
  "generated_at": "{{ DateTime.now().toISO() }}"
}

**THRESHOLDS**:
- Total cost <0.5%: LOW risk
- Total cost 0.5-1.0%: MODERATE risk
- Total cost >1.0%: HIGH risk
- Complexity limit: 7/10

Assess operational feasibility and all-in transaction costs.
```

5. **System Message**:

```
You are an Operational Risk Officer specializing in fuel hedging execution. You assess execution risk, transaction costs, and operational complexity.

EXPERTISE:
- Trade execution strategy
- Slippage estimation
- Transaction cost analysis
- Settlement risk management
- Operational workflow complexity

RESPONSE FORMAT:
Valid JSON only.
```

6. **Test** and **Connect** from Format Agent Input

✅ **Checkpoint**: Agent 3 returns operational analysis

---

### **AGENT 4: IFRS 9 COMPLIANCE AUDITOR**

1. **Duplicate** Agent 3
2. **Rename**: `Agent 4 - IFRS9`
3. **Prompt Text**:

```
{{ $json.formatted_analysis }}

# YOUR TASK

You are an IFRS 9 Hedge Accounting Specialist. Determine if the hedge qualifies for hedge accounting treatment.

**CRITICAL**: Respond with ONLY valid JSON:

{
  "agent_id": "ifrs9",
  "risk_level": "LOW",
  "recommendation": "HEDGE",
  "conviction_level": 9,
  "metrics": {
    "prospective_r2": {{ $json.r2_heating_oil }},
    "retrospective_effectiveness_pct": 92,
    "documentation_complete": true,
    "p_and_l_volatility_impact": "low"
  },
  "constraints_satisfied": true,
  "action_required": false,
  "ifrs9_eligible": {{ $json.r2_heating_oil >= 0.80 }},
  "rationale": "Prospective R² of {{ $json.r2_heating_oil.toFixed(3) }} {{ $json.r2_heating_oil >= 0.80 ? 'EXCEEDS' : 'FALLS BELOW' }} IFRS 9 threshold of 0.80. {{ $json.r2_heating_oil >= 0.80 ? 'Hedge accounting ELIGIBLE. Economic relationship established. Documentation requirements met.' : 'Hedge accounting NOT ELIGIBLE. Cannot apply hedge accounting with R² below 0.80.' }}",
  "generated_at": "{{ DateTime.now().toISO() }}"
}

**CRITICAL RULE**:
IF prospective_r2 < 0.80, you MUST set:
- ifrs9_eligible: false
- recommendation: "AVOID"
- risk_level: "CRITICAL"

Current R²: {{ $json.r2_heating_oil }}
IFRS 9 Status: {{ $json.r2_heating_oil >= 0.80 ? 'ELIGIBLE ✅' : 'NOT ELIGIBLE ❌' }}
```

4. **System Message**:

```
You are an IFRS 9 Hedge Accounting Specialist. You determine if proposed hedges qualify for hedge accounting under IFRS 9 standards.

CRITICAL REQUIREMENTS:
1. Prospective Test: R² ≥ 0.80 (MANDATORY)
2. Retrospective Test: 80-125% effectiveness range
3. Economic Relationship must exist
4. Credit risk not dominant

CONSTANTS:
- IFRS9_R2_MIN_PROSPECTIVE = 0.80 (hard floor)
- IFRS9_RETRO_LOW = 0.80
- IFRS9_RETRO_HIGH = 1.25

If R² < 0.80, hedge accounting is NOT ELIGIBLE and you MUST recommend AVOID.

RESPONSE FORMAT:
Valid JSON only.
```

5. **Test** and **Connect**

✅ **Checkpoint**: Agent 4 returns IFRS 9 compliance decision

---

### **AGENT 5: MACRO STRATEGIST**

1. **Duplicate** Agent 4
2. **Rename**: `Agent 5 - Macro`
3. **Prompt Text**:

```
{{ $json.formatted_analysis }}

# YOUR TASK

You are a Macro Strategist analyzing global oil markets and geopolitical risk.

**CRITICAL**: Respond with ONLY valid JSON:

{
  "agent_id": "macro",
  "risk_level": "MODERATE",
  "recommendation": "HEDGE",
  "conviction_level": 6,
  "metrics": {
    "macro_outlook": "neutral",
    "supply_risk_score": 6,
    "demand_outlook_score": 7,
    "geopolitical_risk_score": 7,
    "price_direction_6mo": "up"
  },
  "constraints_satisfied": true,
  "action_required": false,
  "ifrs9_eligible": null,
  "rationale": "Brent at ${{ $json.brent_crude_futures_usd_bbl }}/bbl reflects balanced market. {{ $json.volatility_regime }} volatility regime. Geopolitical risks elevated but contained. Demand outlook positive. Recommend hedging to lock in current levels before potential upside.",
  "generated_at": "{{ DateTime.now().toISO() }}"
}

**ANALYSIS FACTORS**:
- Brent-WTI spread: ${{ ($json.brent_crude_futures_usd_bbl - $json.wti_crude_futures_usd_bbl).toFixed(2) }}/bbl
- Crack spread: ${{ $json.crack_spread_usd_bbl }}/bbl
- Volatility: {{ $json.volatility_regime }}

Consider OPEC decisions, US SPR levels, China demand, USD strength, and geopolitical tensions.
```

4. **System Message**:

```
You are a Macro Strategist specializing in global oil markets and geopolitical risk. You assess macroeconomic trends that impact fuel hedging strategies.

EXPERTISE:
- Global oil supply/demand fundamentals
- OPEC+ production decisions
- Strategic petroleum reserve (SPR) dynamics
- Currency impacts (USD vs oil prices)
- Geopolitical risk (Middle East, Russia, sanctions)
- Energy transition trends

DECISION FRAMEWORK:
- Macro tailwinds: HEDGE aggressively
- Neutral: HEDGE strategically
- Macro headwinds: WAIT
- Extreme volatility: REDUCE

RESPONSE FORMAT:
Valid JSON only.
```

5. **Test** and **Connect**

✅ **Checkpoint**: All 5 agents created and connected to Format Agent Input

---

## 🔗 NODE 9: MERGE AGENT OUTPUTS

Now merge all 5 agent outputs:

1. Click **+** in empty space below agents
2. Search: **"Merge"**
3. Select **"Merge"** node
4. **Name**: `Investment Committee Merge`
5. **Mode**: Select **"Combine"**
6. **Number of Inputs**: Set to **5**
7. **Connect** all 5 agents to this Merge node:
   - Agent 1 → Merge
   - Agent 2 → Merge
   - Agent 3 → Merge
   - Agent 4 → Merge
   - Agent 5 → Merge
8. **Execute Node** to test
9. Output should show array with 5 items (one from each agent)

✅ **Checkpoint**: Merge node combines all 5 agent responses

---

## 🎯 SECTION 2 COMPLETE!

You should now have:
- ✅ 5 AI Agent nodes (all connected to Format Agent Input)
- ✅ Each agent returns valid JSON
- ✅ 1 Merge node combining all outputs

**Canvas Layout**:
```
Schedule Trigger → Mock Data → Format Input
                                    |
                        +-----------+-----------+
                        |     |     |     |     |
                       A1    A2    A3    A4    A5
                        |     |     |     |     |
                        +-----+-----+-----+-----+
                                    |
                         Investment Committee Merge
```

**Save your workflow!** (Top right)

---

## ▶️ READY FOR SECTION 3?

**Section 3** will create the decision logic:
- Committee Synthesis (aggregate agent recommendations)
- CRO Risk Gate (validate constraints, make final decision)
- POST to FastAPI (send recommendation)
- Final output

**Estimated time**: 30 minutes

**Let me know when you've completed Section 2!**
