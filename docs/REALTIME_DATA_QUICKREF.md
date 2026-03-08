# Real-Time Data Integration - Quick Reference

**Status**: ✅ READY TO USE  
**Cost**: $0/month  
**Time to Deploy**: 5 minutes

---

## ⚡ Quick Start

### 1. Get EIA API Key (Optional, 2 minutes)
```bash
# Visit: https://www.eia.gov/opendata/register.php
# Receive key instantly via email
```

### 2. Enable Live Data
```bash
# Edit .env or docker-compose.yml
USE_LIVE_FEED=true
USE_YAHOO_FINANCE=true
USE_EIA_API=true
EIA_API_KEY=your_key_or_leave_empty
```

### 3. Restart & Verify
```bash
docker compose restart api
curl http://localhost:8000/api/v1/stream/status
```

---

## 📊 Data Sources

| Source | Cost | Speed | Instruments |
|--------|------|-------|-------------|
| **Yahoo Finance** | Free | Real-time (15min delay) | HO, Brent, WTI |
| **EIA API** | Free | Daily (1-day lag) | Jet Fuel, All |
| **Simulation** | Free | Instant | All |

---

## 🎨 UI Indicators

- 🟢 **Yahoo Finance** - Real-time, optimal
- 🟡 **EIA Official** - Official data, slight lag
- 🔵 **Simulated** - GBM fallback
- 🔴 **Disconnected** - Check network

---

## 🔧 Configuration Quick Reference

```bash
# Data Sources
USE_LIVE_FEED=true|false
USE_YAHOO_FINANCE=true|false
USE_EIA_API=true|false
USE_SIMULATION_FALLBACK=true|false

# API Keys
EIA_API_KEY=your_key

# Performance
YAHOO_FINANCE_UPDATE_INTERVAL=60     # seconds
YAHOO_FINANCE_CACHE_TTL=60           # seconds
MAX_YAHOO_REQUESTS_PER_HOUR=100
MAX_EIA_REQUESTS_PER_HOUR=150
```

---

## 🛠️ Common Commands

```bash
# Check status
curl http://localhost:8000/api/v1/stream/status

# View logs
docker logs hedge-api --tail 100

# Restart service
docker compose restart api

# Run tests
cd python_engine && pytest tests/services/test_yahoo_finance_client.py
```

---

## 📚 Documentation

- **Full Plan**: `docs/REALTIME_DATA_INTEGRATION_PLAN.md`
- **User Guide**: `docs/REALTIME_DATA_SOURCES_USER_GUIDE.md`
- **Summary**: `docs/REALTIME_DATA_IMPLEMENTATION_SUMMARY.md`

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Rate limited | Increase `YAHOO_FINANCE_CACHE_TTL=300` |
| EIA 401 error | Check API key, no spaces/quotes |
| Stuck on simulation | Verify `USE_LIVE_FEED=true` |
| Stale prices | `docker compose restart api` |

---

## ✅ Files Created

```
python_engine/app/services/
├── yahoo_finance_client.py       ✅ 450 lines
├── data_source_manager.py        ✅ 450 lines

python_engine/tests/services/
└── test_yahoo_finance_client.py  ✅ 300 lines

docs/
├── REALTIME_DATA_INTEGRATION_PLAN.md        ✅
├── REALTIME_DATA_SOURCES_USER_GUIDE.md      ✅
└── REALTIME_DATA_IMPLEMENTATION_SUMMARY.md  ✅
```

---

**Everything is ready! Just enable `USE_LIVE_FEED=true` and go! 🚀**

*Quick ref updated: March 4, 2026*
