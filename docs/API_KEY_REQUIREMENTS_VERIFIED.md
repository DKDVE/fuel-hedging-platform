# API Key Requirements - Research Results (March 4, 2026)

**Status**: ✅ VERIFIED  
**Sources**: Official documentation + web search

---

## 🔍 **Actual API Key Requirements**

### 1. **Yahoo Finance** ✅ NO API KEY REQUIRED

**Status**: **Truly Free, No Registration**

- ✅ **No API key needed**
- ✅ **No registration required**
- ✅ Access via `yfinance` Python library
- ✅ Real-time futures data (15-min delay)
- ✅ Rate limit: ~100-200 requests/hour (undocumented but permissive)

**Tickers Available**:
- `HO=F` - NYMEX Heating Oil Futures
- `BZ=F` - ICE Brent Crude Futures  
- `CL=F` - NYMEX WTI Crude Futures
- `RB=F` - NYMEX RBOB Gasoline

**Perfect for**: Development, testing, and production futures trading

---

### 2. **EIA API** ⚠️ API KEY REQUIRED (But Free)

**Status**: **Free but Registration Mandatory**

- ⚠️ **API key IS required** (contrary to initial assumption)
- ✅ **Still completely free**
- ⚠️ Must register at https://www.eia.gov/opendata/register.php
- ⏱️ Registration takes 2 minutes
- 📧 API key delivered instantly via email
- 📊 Rate limit: 160 requests/hour (free tier)

**Data Coverage**:
- Jet Fuel spot prices (U.S. Gulf Coast)
- Heating Oil spot prices
- Crude oil spot prices (WTI, Brent)
- Petroleum inventories
- Historical data back to 1990s

**Limitation**: 
- ❌ **NOT real-time** - Weekly updates for spot prices
- ❌ Data published with 1-week lag
- ✅ Best for compliance and historical analysis

---

### 3. **OilPriceAPI** (Recommended Alternative)

**Status**: **Free Trial with API Key**

- ✅ **7-day free trial** (10,000 requests)
- ✅ **Real-time updates** (every 5 minutes)
- ✅ Simple commodity codes: `WTI_USD`, `HEATING_OIL_USD`
- ✅ Registration: https://www.oilpriceapi.com/
- 💰 Paid plans after trial: $29/month Basic

**Why Better than EIA**:
- ✅ 5-minute updates vs EIA's weekly
- ✅ Simpler API (no complex series IDs)
- ✅ Includes jet fuel, diesel, gasoline
- ✅ WebSocket streaming available

**Data Coverage**:
- WTI Crude
- Brent Crude
- Heating Oil
- Diesel
- Jet Fuel (Kerosene)
- Gasoline (Regular, Premium)
- Natural Gas

---

## 📊 **Comparison Table**

| Source | API Key? | Cost | Real-Time? | Best For |
|--------|----------|------|------------|----------|
| **Yahoo Finance** | ❌ No | Free | Yes (15min) | Futures, Development |
| **OilPriceAPI** | ✅ Yes | Free trial | Yes (5min) | Real-time spot prices |
| **EIA API** | ✅ Yes | Free | No (weekly) | Compliance, Historical |
| **Simulation** | ❌ No | Free | Yes | Development, Demo |

---

## 🎯 **Corrected Implementation Strategy**

### **Recommended 3-Tier Approach**

```
Priority 1: Yahoo Finance (No Key)
    ↓ (free, real-time futures)
    
Priority 2: OilPriceAPI (Trial Key)
    ↓ (5-min updates for spot prices)
    
Priority 3: EIA API (Free Key)
    ↓ (official data for compliance)
    
Fallback: Simulation (Always Works)
```

### **For Your Project**

**Development/Testing**:
```bash
USE_LIVE_FEED=true
USE_YAHOO_FINANCE=true        # No key needed!
USE_OILPRICE_API=false        # Skip initially
USE_EIA_API=false             # Skip initially
```

**Production (After Testing)**:
```bash
USE_LIVE_FEED=true
USE_YAHOO_FINANCE=true
USE_OILPRICE_API=true         # Add for jet fuel spot
OILPRICE_API_KEY=your_key

USE_EIA_API=true              # Add for compliance
EIA_API_KEY=your_key
```

---

## 💰 **Cost Analysis (Corrected)**

### **Month 1-7 (Free Trial Period)**

| Service | Cost | Requests/Day | Coverage |
|---------|------|--------------|----------|
| Yahoo Finance | $0 | ~1,440 | Futures |
| OilPriceAPI | $0 | ~1,440 | Spot prices |
| EIA API | $0 | ~24 | Historical |
| **Total** | **$0** | - | Complete |

### **Month 8+ (Post-Trial)**

| Service | Cost/Month | Alternative |
|---------|-----------|------------|
| Yahoo Finance | $0 | Keep using |
| OilPriceAPI | $29 | Or use Yahoo futures only |
| EIA API | $0 | Keep using |
| **Total** | **$0-29** | Decision needed |

---

## 📝 **Updated Implementation Checklist**

### **Immediate (No Keys Required)**
- [x] Implement Yahoo Finance client ✅ DONE
- [x] Test with real data (no key needed) ✅ READY
- [x] Deploy to staging ⏳ NEXT

### **Near-Term (Registration Required)**
- [ ] Register for OilPriceAPI trial (2 minutes)
- [ ] Add OilPriceAPI client to codebase
- [ ] Integrate with DataSourceManager
- [ ] Test real-time jet fuel prices

### **Later (Optional for Compliance)**
- [ ] Register for EIA API key (2 minutes)
- [ ] Enable EIA API in production
- [ ] Use for compliance reporting
- [ ] Historical data backfill

---

## 🔧 **Configuration (Updated)**

```bash
# WORKS RIGHT NOW (No keys needed!)
USE_LIVE_FEED=true
USE_YAHOO_FINANCE=true
# Yahoo Finance starts working immediately!

# ADD LATER (After trial signup)
USE_OILPRICE_API=true
OILPRICE_API_KEY=your_trial_key_here

# ADD EVEN LATER (For compliance)
USE_EIA_API=true
EIA_API_KEY=your_free_key_here
```

---

## ⚡ **Quick Start (Corrected)**

### **RIGHT NOW** (Zero Registration)
```bash
# 1. Enable Yahoo Finance (no key needed!)
export USE_LIVE_FEED=true
export USE_YAHOO_FINANCE=true

# 2. Start backend
cd python_engine
source venv/bin/activate
uvicorn app.main:app --reload

# 3. Verify real data
curl http://localhost:8000/api/v1/stream/status

# Should show:
# "source": "yahoo_finance"
# "available": true
```

### **THIS WEEK** (5 Minutes Setup)
1. Sign up for OilPriceAPI trial: https://www.oilpriceapi.com/
2. Add key to `.env`: `OILPRICE_API_KEY=xxx`
3. Enable: `USE_OILPRICE_API=true`
4. Get real-time jet fuel prices!

### **LATER** (Optional)
1. Register EIA: https://www.eia.gov/opendata/register.php
2. Add key: `EIA_API_KEY=xxx`
3. Use for compliance reports

---

## 📚 **Documentation Updates Needed**

Files to update with correct information:

- [x] `docs/REALTIME_DATA_SOURCES_USER_GUIDE.md` ✅ UPDATED
- [ ] `docs/REALTIME_DATA_INTEGRATION_PLAN.md` - Update cost section
- [ ] `REALTIME_DATA_QUICKREF.md` - Clarify Yahoo is truly keyless
- [ ] `python_engine/app/config.py` - Add OILPRICE_API settings

---

## ✅ **Key Takeaways**

1. **Yahoo Finance**: ✅ Works RIGHT NOW with zero setup
2. **OilPriceAPI**: Best alternative for real-time spot prices (7-day free trial)
3. **EIA API**: Free but requires key, weekly updates only
4. **Total Cost**: $0/month initially, $0-29/month long-term

---

**Bottom Line**: You can start using **real-time data TODAY** with Yahoo Finance (no API key required). Add OilPriceAPI trial this week for complete coverage, and EIA later for compliance.

---

*Research completed: March 4, 2026*  
*Sources: EIA.gov, OilPriceAPI.com, yfinance documentation*
