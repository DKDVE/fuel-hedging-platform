# Fuel Hedging Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com)

Production-focused aviation fuel hedging platform for optimizing hedge ratio,
reducing VaR, improving IFRS 9 readiness, and streamlining recommendation
approval workflows.

## Why This Project Exists

Airlines face high earnings volatility from jet fuel price swings. This platform
combines quantitative analytics, policy constraints, and AI-assisted committee
outputs to support faster, auditable, and risk-aware hedging decisions.

## Key Capabilities

- Real-time price ingest (Yahoo Finance/EIA) with simulation fallback
- Forecasting + VaR + basis risk analytics with optimizer-driven hedge ratio
- IFRS 9 prospective/retrospective effectiveness support and report generation
- n8n-orchestrated multi-agent recommendation pipeline with CRO risk gate
- Role-based workflow for Analyst, Risk Manager, CFO, and Admin
- Full audit trail and operational alerts

## Validated Backtest Outcomes (2020-2024)

| Hypothesis | Description | Result | Target |
|---|---|---|---|
| H1 | Marginal VaR reduction diminishes above 70% HR | Validated | < 0.5% at 70% |
| H2 | Heating oil R2 meets IFRS 9 prospective threshold | Validated | R2 >= 0.80 |
| H3 | Ensemble forecast error remains below target | Validated | MAPE < 8% |
| H4 | Dynamic HR outperforms static 60% baseline | Validated | Improvement > 0% |

Dataset: 1,827 daily observations.  
Bootstrap history once after first start:

```bash
docker exec hedge-api python scripts/seed_analytics_history.py
```

## Architecture

```text
Frontend (React/TS) -> FastAPI -> PostgreSQL/TimescaleDB
                           |-> Redis (rate limiting/caching)
                           |-> n8n (agent workflow orchestration)
                           |-> SSE stream (/api/v1/stream/prices)
```

## Quick Start (Local)

### Prerequisites

- Docker + Docker Compose
- Git

### 1) Configure environment

```bash
cp .env.example .env
cp .env.example python_engine/.env
```

Set required secrets and values in the env files:

- `SECRET_KEY`
- `N8N_WEBHOOK_SECRET`
- `N8N_ENCRYPTION_KEY` (must stay stable once n8n data exists)
- `GROQ_API_KEY` (used by n8n demand strategy and dashboard live brief)

### 2) Start services

```bash
docker-compose up -d
```

### 3) Seed analytics history (one-time)

```bash
docker exec hedge-api python scripts/seed_analytics_history.py
```

### 4) Access apps

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`
- n8n: `http://localhost:5678`

## n8n Setup

### Automated import

```bash
bash scripts/import_n8n_workflow.sh
```

### Manual import

1. Open `http://localhost:5678`
2. Import `n8n/workflows/fuel_hedge_advisor_v2.json`
3. Import `n8n/workflows/demand_strategy_advisor.json`
4. Ensure workflows are activated/published
5. Configure credentials/env:
   - `N8N_API_KEY` must match FastAPI `N8N_WEBHOOK_SECRET`
   - `GROQ_API_KEY` must be present for LLM nodes

If n8n is unavailable, core analytics still works. Use:

```bash
bash scripts/create_test_recommendation.sh
```

## Configuration Notes

- Scheduler and pipeline resilience controls are environment-driven
  (`SCHEDULER_*`, `PIPELINE_*`, `N8N_REQUEST_*`)
- Dashboard live AI brief uses FastAPI -> Groq directly (`GROQ_*`)
- Recommendation "Agent Analysis" comes from n8n workflow outputs
- Keep unit handling consistent: ratios in computation, percents in display

## Security and Compliance

- JWT auth with httpOnly cookies
- Endpoint rate limiting by risk profile
- SQLAlchemy parameterized queries (no string-built SQL)
- RBAC on API and UI actions
- Audit logging for state-changing operations

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy async, Pydantic v2 |
| Frontend | React 18, TypeScript 5, Tailwind, React Query |
| Data | PostgreSQL 15 + TimescaleDB |
| Cache | Redis 7 |
| Workflow | n8n |
| Deployment | Render (backend), GitHub Pages (frontend) |

## Default Dev Credentials

For local development/testing only:

| Role | Email | Password |
|---|---|---|
| Admin | admin@airline.com | admin123 |
| Risk Manager | risk@airline.com | risk123 |
| Analyst | analyst@airline.com | analyst123 |

## Troubleshooting

- `404 /webhook/fuel-hedge-trigger`: workflow not active/published in n8n
- `403 Authorization data is wrong`: `N8N_API_KEY` and `N8N_WEBHOOK_SECRET` mismatch
- n8n restart login/encryption issues: verify stable `N8N_ENCRYPTION_KEY`
- Inflated percent values: confirm ratio-vs-percent normalization in payload paths

## Contributing

1. Create a feature branch from `main`
2. Make small, reviewable commits
3. Run type/syntax checks before pushing
4. Open a PR with summary and test plan

## License

MIT License.

## Disclaimer

This software supports internal risk analysis and workflow automation. Final
hedging and accounting decisions must be reviewed by qualified treasury and
accounting professionals before external reporting.
