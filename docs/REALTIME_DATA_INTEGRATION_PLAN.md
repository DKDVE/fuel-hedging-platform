# Real-Time Data Sources Integration Plan

**Date**: March 4, 2026  
**Status**: 📋 PLANNING  
**Goal**: Integrate EIA API and Yahoo Finance for real-time fuel price data

---

## 🎯 Executive Summary

Integrate two free/low-cost data sources into the existing real-time architecture:
1. **EIA API** (U.S. Energy Information Administration) - Official petroleum data
2. **Yahoo Finance API** (via yfinance library) - Real-time futures prices

**Current State**: Simulation mode with GBM (Geometric Brownian Motion)  
**Target State**: Live data feeds with fallback to simulation

---

## 📊 Data Sources Analysis

### 1. EIA API (Official U.S. Government Data)

**Coverage**:
- ✅ Jet Fuel Spot Prices (U.S. Gulf Coast)
- ✅ Heating Oil Spot Prices
- ✅ Crude Oil Spot Prices (Brent, WTI)
- ✅ Historical data back to 1990s
- ✅ Daily updates (published 4:00 PM ET)

**API Details**:
- **Base URL**: `https://api.eia.gov/v2`
- **Authentication**: Query parameter `api_key`
- **Rate Limit**: 160 requests/hour (free tier)
- **Registration**: https://www.eia.gov/opendata/register.php (free)
- **Documentation**: https://www.eia.gov/opendata/documentation.php

**Key Series IDs** (from swagger):
```
Jet Fuel (U.S. Gulf Coast):
  - Series: PET.EER_EPJK_PF4_RGC_DPG.D
  - Frequency: Daily
  - Unit: Dollars per Gallon

Heating Oil (No. 2 Fuel Oil):
  - Series: PET.EER_EPD2F_PF4_Y35NY_DPG.D
  - Frequency: Daily
  - Unit: Dollars per Gallon

WTI Crude Oil:
  - Series: PET.RWTC.D
  - Frequency: Daily
  - Unit: Dollars per Barrel

Brent Crude Oil:
  - Series: PET.RBRTE.D
  - Frequency: Daily
  - Unit: Dollars per Barrel
```

**Limitations**:
- ❌ NOT real-time (daily snapshots only)
- ❌ 1-day lag (data published next day)
- ⚠️ Best for historical analysis, not live trading

---

### 2. Yahoo Finance (Free Real-Time Futures)

**Coverage**:
- ✅ NYMEX Heating Oil Futures (HO=F)
- ✅ ICE Brent Crude Futures (BZ=F)
- ✅ NYMEX WTI Crude Futures (CL=F)
- ✅ Real-time quotes (15-min delay for free tier)
- ✅ Intraday tick data
- ✅ Historical OHLCV data

**API Details**:
- **Library**: `yfinance` (Python package)
- **Authentication**: None required
- **Rate Limit**: Unofficial (generally permissive for reasonable use)
- **Cost**: FREE
- **Documentation**: https://pypi.org/project/yfinance/

**Ticker Symbols**:
```python
SYMBOLS = {
    'heating_oil': 'HO=F',      # NYMEX Heating Oil Futures
    'brent_crude': 'BZ=F',      # ICE Brent Crude Futures
    'wti_crude': 'CL=F',        # NYMEX WTI Crude Futures
    'rbob_gasoline': 'RB=F',    # NYMEX RBOB Gasoline (related to jet fuel)
}
```

**Data Quality**:
- ✅ Real-time (15-min delay)
- ✅ Sub-second granularity available
- ✅ High reliability (powered by Yahoo Finance infrastructure)
- ⚠️ No official SLA (unofficial API)

---

### 3. Hybrid Strategy (RECOMMENDED)

**Approach**: Use both sources with smart fallback logic

```
┌─────────────────────────────────────────────────────┐
│              DATA SOURCE PRIORITY                    │
├─────────────────────────────────────────────────────┤
│  1. Yahoo Finance (Primary - Real-time futures)     │
│     └─> For: HO, Brent, WTI                        │
│                                                      │
│  2. EIA API (Secondary - Official spot prices)      │
│     └─> For: Jet Fuel spot, validation data        │
│                                                      │
│  3. Simulation (Fallback - Always available)        │
│     └─> When: APIs unavailable or rate limited     │
└─────────────────────────────────────────────────────┘
```

**Why Hybrid?**:
- Yahoo Finance = Real-time but unofficial
- EIA = Official but delayed
- Combined = Best of both worlds
- Simulation = Always works (dev/demo)

---

## 🏗️ Architecture Design

### Current Architecture (Already Implemented)
```
Frontend (SSE Client)
    ↓
GET /api/v1/stream/prices
    ↓
PriceService
    ↓
[SIMULATION MODE] ← Currently here
    GBM Price Generation
```

### New Architecture (To Implement)
```
Frontend (SSE Client)
    ↓
GET /api/v1/stream/prices
    ↓
PriceService (Smart Router)
    ↓
    ├─→ [LIVE MODE - Priority 1]
    │       YahooFinanceClient
    │       └─> Get real-time futures
    │
    ├─→ [LIVE MODE - Priority 2]
    │       EIAClient (already exists)
    │       └─> Get official jet fuel spot
    │
    └─→ [FALLBACK]
            Simulation (GBM)
            └─> Always available
```

---

## 📝 Implementation Tasks

### Phase 1: Yahoo Finance Integration (Priority: HIGH)
**Estimated Time**: 2-3 hours

#### Task 1.1: Install Dependencies
- [ ] Add `yfinance>=0.2.36` to requirements.txt
- [ ] Add `pandas>=2.0.0` (required by yfinance)
- [ ] Update Dockerfile

#### Task 1.2: Create YahooFinanceClient
**File**: `python_engine/app/services/yahoo_finance_client.py`

Features:
- Async wrapper around yfinance
- Circuit breaker pattern (reuse from EIAClient)
- Ticker symbol mapping
- Unit conversion (gallons to barrels)
- Error handling with fallback
- Rate limiting (100 requests/hour conservative)

#### Task 1.3: Update PriceService
**File**: `python_engine/app/services/price_service.py`

Changes:
- Add YahooFinanceClient initialization
- Implement smart source selection
- Add health monitoring per source
- Keep simulation fallback
- Log data source switches

#### Task 1.4: Configuration
**File**: `python_engine/app/config.py`

Add settings:
```python
# Data source priority
USE_YAHOO_FINANCE: bool = True
USE_EIA_API: bool = True
USE_SIMULATION_FALLBACK: bool = True

# Yahoo Finance config
YAHOO_FINANCE_UPDATE_INTERVAL: int = 60  # seconds
YAHOO_FINANCE_CACHE_TTL: int = 300  # 5 minutes

# Rate limiting
MAX_YAHOO_REQUESTS_PER_HOUR: int = 100
MAX_EIA_REQUESTS_PER_HOUR: int = 150
```

---

### Phase 2: Enhanced EIA Integration (Priority: MEDIUM)
**Estimated Time**: 1-2 hours

#### Task 2.1: Update EIAClient
**File**: `python_engine/app/services/external_apis.py`

Enhancements:
- [ ] Add all series IDs from swagger
- [ ] Implement batch fetching
- [ ] Add caching with Redis
- [ ] Daily refresh schedule
- [ ] Better error messages

#### Task 2.2: EIA Data Mapping
**File**: `python_engine/app/services/eia_mapper.py` (NEW)

Features:
- Map EIA series to instrument types
- Unit conversions (gallons ↔ barrels)
- Date/time normalization
- Quality checks

---

### Phase 3: Smart Data Fusion (Priority: HIGH)
**Estimated Time**: 2-3 hours

#### Task 3.1: Create DataSourceManager
**File**: `python_engine/app/services/data_source_manager.py` (NEW)

Responsibilities:
- Source priority management
- Health monitoring per source
- Automatic failover
- Data quality scoring
- Source selection algorithm

#### Task 3.2: Implement Fallback Logic
```python
async def get_latest_price(instrument: str) -> Price:
    """Get latest price with smart fallback."""
    
    # Try Yahoo Finance first (real-time)
    try:
        if USE_YAHOO_FINANCE:
            price = await yahoo_client.get_price(instrument)
            if is_valid(price):
                return price
    except Exception as e:
        logger.warning(f"yahoo_finance_failed: {e}")
    
    # Try EIA API second (official data)
    try:
        if USE_EIA_API and instrument == "jet_fuel":
            price = await eia_client.get_latest_price()
            if is_valid(price):
                return price
    except Exception as e:
        logger.warning(f"eia_api_failed: {e}")
    
    # Fallback to simulation
    return await simulation.generate_price(instrument)
```

---

### Phase 4: Frontend Enhancements (Priority: MEDIUM)
**Estimated Time**: 1 hour

#### Task 4.1: Update DataSourceBadge
**File**: `frontend/src/components/ui/DataSourceBadge.tsx`

New statuses:
- 🟢 "Live Feed" - Yahoo Finance active
- 🟡 "Official Data" - EIA API active
- 🔵 "Simulated" - Fallback mode
- 🔴 "Disconnected" - No data
- ⚪ "Mixed Sources" - Using multiple

#### Task 4.2: Add Source Breakdown
Show which instruments come from which source:
```
Data Sources:
✓ Heating Oil: Yahoo Finance (real-time)
✓ Brent Crude: Yahoo Finance (real-time)
✓ WTI Crude: Yahoo Finance (real-time)
✓ Jet Fuel: EIA API (official, 1-day lag)
```

---

### Phase 5: Testing & Validation (Priority: HIGH)
**Estimated Time**: 2-3 hours

#### Task 5.1: Unit Tests
- [ ] Test YahooFinanceClient with mocked responses
- [ ] Test EIAClient with fixture data
- [ ] Test fallback logic all scenarios
- [ ] Test rate limiting behavior

#### Task 5.2: Integration Tests
- [ ] Test full data pipeline
- [ ] Test API failures and recovery
- [ ] Test rate limit handling
- [ ] Test data quality checks

#### Task 5.3: Manual Testing
- [ ] Verify real-time updates in UI
- [ ] Test with actual API keys
- [ ] Simulate network failures
- [ ] Monitor for 24 hours

---

## 📦 New Files to Create

```
python_engine/app/services/
├── yahoo_finance_client.py          # NEW - Yahoo Finance wrapper
├── data_source_manager.py           # NEW - Smart routing
├── eia_mapper.py                    # NEW - EIA data mapping
└── external_apis.py                 # MODIFY - Enhance EIAClient

python_engine/tests/services/
├── test_yahoo_finance_client.py     # NEW
├── test_data_source_manager.py      # NEW
└── test_eia_mapper.py               # NEW

docs/
└── REALTIME_DATA_SOURCES_GUIDE.md   # NEW - User guide
```

---

## 🔧 Configuration Examples

### Development (.env)
```bash
# Data Sources
USE_YAHOO_FINANCE=true
USE_EIA_API=true
USE_SIMULATION_FALLBACK=true

# API Keys
EIA_API_KEY=your_eia_key_here
# Yahoo Finance needs no key

# Update intervals
YAHOO_FINANCE_UPDATE_INTERVAL=60
EIA_UPDATE_INTERVAL=86400  # Once per day

# Feature flags
ENABLE_DATA_QUALITY_CHECKS=true
ENABLE_SOURCE_HEALTH_MONITORING=true
```

### Production (.env.production)
```bash
# More aggressive caching in production
USE_YAHOO_FINANCE=true
USE_EIA_API=true
USE_SIMULATION_FALLBACK=false  # Don't fallback in prod

# Production keys
EIA_API_KEY=${EIA_API_KEY_SECRET}

# Conservative rate limits
MAX_YAHOO_REQUESTS_PER_HOUR=80
MAX_EIA_REQUESTS_PER_HOUR=120

# Monitoring
ENABLE_DATA_QUALITY_ALERTS=true
ENABLE_PROMETHEUS_METRICS=true
```

---

## 📊 Success Metrics

### Technical Metrics
- [ ] Data latency < 1 minute (Yahoo Finance)
- [ ] API success rate > 99%
- [ ] Fallback activations < 5/day
- [ ] Zero rate limit violations

### User Experience
- [ ] Real-time badge shows correct source
- [ ] Price updates smooth (no jumps)
- [ ] No blank charts on load
- [ ] Clear error messages if data unavailable

---

## 🚀 Rollout Plan

### Week 1: Development
- Day 1-2: Implement YahooFinanceClient
- Day 3: Integrate with PriceService
- Day 4: Testing and bug fixes
- Day 5: Documentation

### Week 2: Staging
- Deploy to staging environment
- Monitor for 3 days
- Gather feedback
- Performance tuning

### Week 3: Production
- Gradual rollout (10% → 50% → 100%)
- Monitor metrics closely
- Keep simulation as kill switch

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Yahoo Finance API changes | HIGH | Multiple fallbacks, monitoring |
| Rate limits exceeded | MEDIUM | Conservative limits, caching |
| Data quality issues | HIGH | Validation layer, sanity checks |
| Increased costs (if paid tier needed) | LOW | Start with free tier, monitor |
| Legal/ToS concerns | MEDIUM | Review Yahoo ToS, use yfinance library |

---

## 💰 Cost Analysis

| Service | Free Tier | Paid Tier | Our Usage | Cost |
|---------|-----------|-----------|-----------|------|
| EIA API | 160 req/hr | N/A | ~24 req/day | $0/month |
| Yahoo Finance | Unlimited* | N/A | ~1440 req/day | $0/month |
| Total | - | - | - | **$0/month** |

*Reasonable use via yfinance library

---

## 📚 Resources

### EIA API
- Registration: https://www.eia.gov/opendata/register.php
- Documentation: https://www.eia.gov/opendata/documentation.php
- Swagger: See `docs/eia-api-swagger.yaml`
- Query Browser: https://www.eia.gov/opendata/browser/

### Yahoo Finance
- yfinance docs: https://pypi.org/project/yfinance/
- GitHub: https://github.com/ranaroussi/yfinance
- Ticker lookup: https://finance.yahoo.com/lookup

### Related Docs
- `REALTIME_DATA_IMPLEMENTATION.md` - Current architecture
- `REALTIME_DATA_QUICKSTART.md` - Quick reference
- `N8N_AGENT_PROMPTS.md` - Agent integration

---

## 🎯 Next Steps

1. **Get API Keys**
   - Register for EIA API key (5 minutes)
   - No key needed for Yahoo Finance

2. **Review This Plan**
   - Approve architecture decisions
   - Prioritize phases
   - Allocate resources

3. **Start Implementation**
   - Begin with Phase 1 (Yahoo Finance)
   - Test thoroughly before moving to Phase 2
   - Document as you go

4. **Monitor & Iterate**
   - Track success metrics
   - Gather user feedback
   - Optimize based on usage

---

**Ready to proceed? Let's start with Phase 1!**

*Plan created: March 4, 2026*  
*Estimated total time: 8-12 hours*  
*Risk level: LOW (all fallbacks in place)*
