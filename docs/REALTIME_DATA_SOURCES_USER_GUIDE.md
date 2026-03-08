# Real-Time Data Sources - User Guide

**Date**: March 4, 2026  
**Version**: 1.0  
**Status**: ✅ IMPLEMENTATION COMPLETE

---

## 🎯 Overview

Your fuel hedging platform now supports **three data sources** for real-time price feeds:

1. **Yahoo Finance** - Real-time futures quotes (15-min delay, free)
2. **EIA API** - Official U.S. government petroleum data (1-day lag, free)
3. **Simulation** - Geometric Brownian Motion fallback (always available)

The system **automatically selects** the best available source based on:
- Data freshness
- Source availability
- Configured priorities
- Instrument type

---

## 🚀 Quick Start

### Step 1: Get API Keys

#### Yahoo Finance ✅ NO KEY NEEDED
**No API key needed!** The `yfinance` library provides free access with no authentication.

#### EIA API (Optional - For Official Government Data)
⚠️ **Registration Required** (despite being free):
1. Visit https://www.eia.gov/opendata/register.php
2. Fill out registration form (takes 2 minutes)
3. Receive API key via email instantly
4. **Free tier**: 160 requests/hour
5. **Limitation**: Weekly updates only (not real-time)

#### OilPriceAPI (Recommended Alternative)
✅ **Better for Real-Time Data**:
1. Visit https://www.oilpriceapi.com/
2. Sign up for **free 7-day trial** (10,000 requests)
3. Get API key instantly
4. **Real-time updates**: Every 5 minutes
5. **Coverage**: WTI, Brent, Diesel, Heating Oil, Jet Fuel, Gasoline

### Step 2: Configure Environment

Edit your `.env` file or `docker-compose.yml`:

```bash
# Enable live data feeds
USE_LIVE_FEED=true

# Data source priorities
USE_YAHOO_FINANCE=true       # Real-time futures
USE_EIA_API=true             # Official spot prices
USE_SIMULATION_FALLBACK=true # Backup if APIs fail

# API Keys
EIA_API_KEY=your_eia_key_here_or_leave_empty

# Update intervals (seconds)
YAHOO_FINANCE_UPDATE_INTERVAL=60  # How often to refresh
YAHOO_FINANCE_CACHE_TTL=60        # Cache lifetime

# Rate limits (requests per hour)
MAX_YAHOO_REQUESTS_PER_HOUR=100
MAX_EIA_REQUESTS_PER_HOUR=150
```

### Step 3: Restart Services

```bash
# If using Docker
docker compose restart api

# If running locally
cd python_engine
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Step 4: Verify in UI

1. Open http://localhost:5173
2. Login and go to Dashboard
3. Look for the **Data Source Badge** (top of price chart)
4. You should see:
   - 🟢 Green dot = Yahoo Finance active
   - 🟡 Yellow dot = EIA API active
   - 🔵 Blue dot = Simulation mode

---

## 📊 Data Source Comparison

| Feature | Yahoo Finance | OilPriceAPI | EIA API | Simulation |
|---------|--------------|-------------|---------|------------|
| **Cost** | Free | Free trial (7 days) | Free | Free |
| **Speed** | Real-time (15-min delay) | Real-time (5-min) | Weekly | Instant |
| **Reliability** | High | Very High | Very High | 100% |
| **Coverage** | Futures | Spot prices | Spot + Futures | All |
| **API Key** | ❌ Not needed | ✅ Required | ✅ Required | ❌ Not needed |
| **Rate Limit** | ~100/hour | 10,000/week (trial) | 160/hour | Unlimited |
| **Best For** | Futures trading | Real-time spot prices | Compliance/Reporting | Dev/Demo |

---

## 🔧 Configuration Guide

### Scenario 1: Production (Real Money)

```bash
USE_LIVE_FEED=true
USE_YAHOO_FINANCE=true
USE_EIA_API=true
USE_SIMULATION_FALLBACK=false  # Don't fallback in prod

EIA_API_KEY=your_production_key

# Conservative rate limits
MAX_YAHOO_REQUESTS_PER_HOUR=80
MAX_EIA_REQUESTS_PER_HOUR=120
```

**Why?**
- Yahoo Finance gives you real-time market prices
- EIA validates official data
- No simulation fallback ensures data quality

### Scenario 2: Development/Testing

```bash
USE_LIVE_FEED=false  # Use simulation only

# Simulation parameters
SIMULATION_INTERVAL_SECONDS=2
SIMULATION_INITIAL_PRICE=85.0
SIMULATION_VOLATILITY=0.02
```

**Why?**
- No external API dependencies
- Predictable, reproducible behavior
- Fast iteration cycles

### Scenario 3: Demo/Presentation

```bash
USE_LIVE_FEED=true
USE_YAHOO_FINANCE=true
USE_EIA_API=false  # Skip to avoid key requirement
USE_SIMULATION_FALLBACK=true

# No API keys needed
```

**Why?**
- Shows real-time data without EIA registration
- Looks professional with live prices
- Falls back gracefully if network issues

---

## 📈 Instrument Coverage

### What Data Comes from Where?

```
┌───────────────────┬──────────────────┬────────────────┐
│ Instrument        │ Primary Source   │ Fallback       │
├───────────────────┼──────────────────┼────────────────┤
│ Heating Oil       │ Yahoo Finance    │ Simulation     │
│ Brent Crude       │ Yahoo Finance    │ Simulation     │
│ WTI Crude         │ Yahoo Finance    │ Simulation     │
│ Jet Fuel          │ EIA API          │ Yahoo (proxy)  │
└───────────────────┴──────────────────┴────────────────┘
```

**Yahoo Finance Ticker Symbols**:
- `HO=F` - NYMEX Heating Oil Futures
- `BZ=F` - ICE Brent Crude Futures
- `CL=F` - NYMEX WTI Crude Futures
- `RB=F` - NYMEX RBOB Gasoline (jet fuel proxy)

**EIA API Series IDs**:
- `PET.EER_EPJK_PF4_RGC_DPG.D` - Jet Fuel U.S. Gulf Coast
- `PET.EER_EPD2F_PF4_Y35NY_DPG.D` - Heating Oil No. 2
- `PET.RBRTE.D` - Brent Crude Spot
- `PET.RWTC.D` - WTI Crude Spot

---

## 🎨 UI Indicators

### Data Source Badge States

| Badge | Meaning | Action Needed |
|-------|---------|---------------|
| 🟢 **Yahoo Finance** | Real-time data flowing | ✅ None - optimal state |
| 🟡 **EIA Official** | Official data, slight lag | ✅ None - good for compliance |
| 🟣 **Mixed Sources** | Using multiple feeds | ℹ️ Check source breakdown |
| 🔵 **Simulated** | Using GBM simulation | ⚠️ Not for production trading |
| 🔴 **Disconnected** | No data source available | ❌ Check network/API keys |

### Source Breakdown View

Click the badge to see which instrument uses which source:

```
Data Sources:
✓ Heating Oil: Yahoo Finance (real-time)
✓ Brent Crude: Yahoo Finance (real-time)
✓ WTI Crude: Yahoo Finance (real-time)
✓ Jet Fuel: EIA API (official, 1-day lag)
```

---

## 🔍 Monitoring & Health

### Check System Health

```bash
# Via API
curl http://localhost:8000/api/v1/stream/status | jq

# Expected response:
{
  "mode": "live",
  "sources": {
    "yahoo_finance": {
      "available": true,
      "success_rate": 0.98,
      "avg_latency_ms": 245.67
    },
    "eia_api": {
      "available": true,
      "success_rate": 1.0,
      "avg_latency_ms": 523.12
    }
  }
}
```

### Dashboard Indicators

Watch for these signals:

✅ **Healthy**:
- Badge is green or yellow
- "Updated Xs ago" shows recent time (< 2 minutes)
- Price chart updates smoothly

⚠️ **Warning**:
- Badge occasionally flickers to blue
- "Updated Xs ago" shows 2-5 minutes
- Occasional reconnection messages

❌ **Critical**:
- Badge stuck on red "Disconnected"
- "Updated Xs ago" > 10 minutes
- Chart frozen

---

## 🛠️ Troubleshooting

### Issue: "Yahoo Finance rate limited"

**Symptoms**: Badge switches to simulation mode frequently

**Solution**:
```bash
# Increase cache TTL to reduce API calls
YAHOO_FINANCE_CACHE_TTL=300  # 5 minutes instead of 1

# Reduce request frequency
YAHOO_FINANCE_UPDATE_INTERVAL=120  # Update every 2 minutes
```

### Issue: "EIA API returns 401 Unauthorized"

**Symptoms**: EIA data unavailable, jet fuel shows simulation

**Solution**:
1. Verify API key is correct: `echo $EIA_API_KEY`
2. Check key is active: https://www.eia.gov/opendata/
3. Ensure key has no extra spaces or quotes
4. Restart backend after updating key

### Issue: "All sources showing simulation"

**Symptoms**: Blue badge, all prices from GBM

**Check**:
```bash
# 1. Verify settings
echo $USE_LIVE_FEED  # Should be 'true'
echo $USE_YAHOO_FINANCE  # Should be 'true'

# 2. Check network
curl https://finance.yahoo.com  # Should return HTML
curl https://api.eia.gov/v2/  # Should return JSON

# 3. Check logs
docker logs hedge-api --tail 100 | grep -i "yahoo\|eia"
```

### Issue: "Prices seem stale"

**Symptoms**: Same price for > 5 minutes during market hours

**Solution**:
```bash
# Clear cache and force refresh
curl -X POST http://localhost:8000/api/v1/stream/refresh

# Or restart the service
docker compose restart api
```

---

## 📚 API Reference

### Stream Status Endpoint

```http
GET /api/v1/stream/status
```

**Response**:
```json
{
  "mode": "live",
  "data_source": "yahoo_finance",
  "tick_rate_seconds": 2,
  "health": {
    "yahoo_finance": {
      "available": true,
      "success_rate": 0.98,
      "avg_latency_ms": 245.67,
      "last_success": "2026-03-04T10:30:45Z"
    },
    "eia_api": {
      "available": true,
      "success_rate": 1.0,
      "avg_latency_ms": 523.12,
      "last_success": "2026-03-04T06:00:00Z"
    },
    "simulation": {
      "available": true,
      "success_rate": 1.0,
      "avg_latency_ms": 0.5
    }
  },
  "latest_prices": {
    "heating_oil": {
      "price": 2.75,
      "change_percent": 1.2,
      "source": "yahoo_finance",
      "timestamp": "2026-03-04T10:30:45Z"
    }
  }
}
```

### Source Breakdown Endpoint

```http
GET /api/v1/stream/sources
```

**Response**:
```json
{
  "heating_oil": ["yahoo_finance", "simulation"],
  "brent_crude": ["yahoo_finance", "simulation"],
  "wti_crude": ["yahoo_finance", "simulation"],
  "jet_fuel": ["eia_api", "yahoo_finance", "simulation"]
}
```

---

## 🔐 Security Best Practices

### API Key Management

❌ **Don't**:
```python
EIA_API_KEY = "abc123"  # Hardcoded in code
```

✅ **Do**:
```bash
# In .env file (gitignored)
EIA_API_KEY=abc123

# Or in Docker secrets
docker secret create eia_api_key api_key.txt
```

### Rate Limit Protection

The system automatically:
- ✅ Tracks requests per hour
- ✅ Blocks requests when limit reached
- ✅ Returns cached data if available
- ✅ Falls back to alternative source
- ✅ Logs rate limit violations

**You don't need to do anything!** The circuit breaker handles it.

---

## 📊 Performance Optimization

### Recommended Settings by Environment

**Development** (fastest iteration):
```bash
USE_LIVE_FEED=false  # Simulation only
SIMULATION_INTERVAL_SECONDS=1
```

**Staging** (realistic testing):
```bash
USE_LIVE_FEED=true
YAHOO_FINANCE_UPDATE_INTERVAL=30  # Frequent updates
YAHOO_FINANCE_CACHE_TTL=60
MAX_YAHOO_REQUESTS_PER_HOUR=150  # Higher limit
```

**Production** (optimal reliability):
```bash
USE_LIVE_FEED=true
YAHOO_FINANCE_UPDATE_INTERVAL=60  # Balanced
YAHOO_FINANCE_CACHE_TTL=120        # Longer cache
MAX_YAHOO_REQUESTS_PER_HOUR=80    # Conservative
```

---

## 🎓 Advanced Topics

### Custom Source Priority

Edit `data_source_manager.py`:

```python
INSTRUMENT_SOURCE_MAP = {
    'jet_fuel': [
        DataSourceType.YAHOO_FINANCE,  # Try Yahoo first
        DataSourceType.EIA_API,         # Then EIA
        DataSourceType.SIMULATION       # Finally simulation
    ],
}
```

### Adding New Data Sources

1. Create client in `app/services/your_client.py`
2. Implement `get_price()` method
3. Add to `DataSourceManager._fetch_from_source()`
4. Update `INSTRUMENT_SOURCE_MAP`
5. Add to `config.py` settings

### Custom Simulation Models

Edit simulation logic in `data_source_manager.py`:

```python
async def _fetch_simulation(self, instrument: str):
    # Your custom pricing model here
    # e.g., Mean reversion, Jump diffusion, etc.
    pass
```

---

## ✅ Checklist: Going Live

Before enabling live data in production:

- [ ] Obtained EIA API key (if using EIA)
- [ ] Tested all sources in staging environment
- [ ] Verified rate limits are appropriate
- [ ] Set up monitoring/alerts for source failures
- [ ] Documented which instruments use which sources
- [ ] Trained team on data source indicators
- [ ] Set up backup/fallback procedures
- [ ] Tested circuit breaker behavior
- [ ] Verified data quality matches expectations
- [ ] Configured logging for audit trail

---

## 🆘 Support

### Getting Help

1. **Check logs**:
   ```bash
   docker logs hedge-api --tail 200 | grep -i "error\|warning"
   ```

2. **Verify configuration**:
   ```bash
   docker exec hedge-api env | grep "USE_\|API_KEY\|YAHOO\|EIA"
   ```

3. **Test connectivity**:
   ```bash
   curl http://localhost:8000/api/v1/stream/status
   ```

### Common Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| `yfinance_not_installed` | Missing dependency | `pip install yfinance` |
| `circuit_breaker_open` | Too many failures | Wait 60s, check network |
| `rate_limit_exceeded` | Too many requests | Increase cache TTL |
| `eia_api_key_missing` | No API key set | Add to .env file |
| `unknown_instrument` | Invalid symbol | Check TICKER_MAP |

---

## 📖 Additional Resources

- **EIA API Docs**: https://www.eia.gov/opendata/documentation.php
- **Yahoo Finance Docs**: https://pypi.org/project/yfinance/
- **Project Plan**: `docs/REALTIME_DATA_INTEGRATION_PLAN.md`
- **Implementation Details**: `docs/REALTIME_DATA_IMPLEMENTATION.md`

---

**Congratulations!** Your fuel hedging platform now has enterprise-grade real-time data feeds! 🎉

*Guide last updated: March 4, 2026*
