# Fuel Hedging Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com)

**Reduces fuel cost variance by 40%+ through dynamic hedging**

---

## Validated Results (2020–2024 Backtest)

| Hypothesis | Description | Result | Threshold |
|------------|-------------|--------|-----------|
| **H1** | Marginal VaR reduction diminishes above 70% HR | ✅ Validated | < 0.5% at 70% |
| **H2** | Heating oil R² meets IFRS 9 designation | ✅ Validated | R² ≥ 0.80 |
| **H3** | Ensemble MAPE below target | ✅ Validated | MAPE < 8% |
| **H4** | Dynamic HR outperforms static 60% baseline | ✅ Validated | > 0% improvement |

*Results from walk-forward backtest on 1,827 daily observations. Run `docker exec hedge-api python scripts/seed_analytics_history.py` to populate.*

---

## What It Does

### Core Platform
- **Real-time prices** via Yahoo Finance + EIA API (or GBM simulation)
- **Walk-forward VaR** and hedge ratio optimization (SLSQP)
- **IFRS 9** prospective (R²) and retrospective (dollar offset) effectiveness tests
- **PDF reports** for auditor-ready hedge accounting documentation

### AI Agent Committee
- 5 specialised agents (basis risk, liquidity, operational, IFRS 9, macro)
- Committee vote with CRO gate for recommendation approval
- Explainability panel shows full reasoning chain per recommendation

### Approval Workflow
- Role-based access (Analyst, Risk Manager, CFO, Admin)
- 4-hour SLA monitoring with alerts
- Audit trail for all decisions

### Compliance
- JWT in httpOnly cookies, rate limiting, CORS
- TimescaleDB for time-series, Redis for rate limits
- n8n workflows for agent orchestration

---

## Quick Start

```bash
# Start all services
docker-compose up -d

# Seed analytics history + backtest (run once after first launch)
docker exec hedge-api python scripts/seed_analytics_history.py

# Access
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Frontend: http://localhost:5173
# - n8n: http://localhost:5678
```

---

## n8n Workflow Setup

**Automated import:**
```bash
bash scripts/import_n8n_workflow.sh
```

**Manual import (if automated fails):**
1. Open http://localhost:5678
2. Settings → Import from file → select `n8n/workflows/fuel_hedge_advisor_v2.json`
3. Add OpenAI credential: Credentials → New → OpenAI API → paste your key
4. Activate the workflow (toggle in top-right)
5. Test: Dashboard → Run Pipeline (as admin)

**Without OpenAI key:** The platform works fully without n8n. Use the test recommendation script to simulate a complete recommendation for demo purposes:
```bash
bash scripts/create_test_recommendation.sh
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│  FastAPI    │────▶│ PostgreSQL  │
│  (React)    │     │  (API)      │     │ TimescaleDB │
└─────────────┘     └──────┬──────┘     └─────────────┘
       │                   │
       │                   ├──────────▶ Redis (rate limit)
       │                   │
       │                   ├──────────▶ n8n (agent workflows)
       │                   │
       └───────────────────┴──────────▶ SSE /api/v1/stream/prices
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI 0.110, SQLAlchemy 2.0 async, Pydantic v2 |
| Frontend | React 18, TypeScript 5, TailwindCSS, React Query v5 |
| Database | PostgreSQL 15, TimescaleDB |
| Cache | Redis 7 |
| Workflow | n8n |
| Deployment | Render.com (API), GitHub Pages (frontend) |

---

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@airline.com | admin123 |
| Risk Manager | risk@airline.com | risk123 |
| Analyst | analyst@airline.com | analyst123 |

---

## Licence

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*Note: Results from this platform should be reviewed by a qualified accountant before use in external financial reporting.*
