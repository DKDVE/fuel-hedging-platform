# Fuel Hedging Platform — System Architecture

**Document Version:** 1.0  
**Last Updated:** 2025-03-07  
**Scope:** Documents the actual codebase as deployed via Docker Compose.

---

## 1. System Overview

The Aviation Fuel Hedging Platform is an optimization and risk-monitoring system for airlines. It provides real-time market price feeds, analytics pipeline execution (forecasting, VaR, basis risk, hedge optimization), AI-driven recommendations via n8n agents, and a React dashboard for CFOs and risk managers.

**Users:** Analysts, Risk Managers, CFOs, Admins (role-based access).

**Docker Services:**

| Service        | Container      | Port | Purpose                                      |
|----------------|----------------|------|----------------------------------------------|
| postgres       | hedge-postgres | 5432 | PostgreSQL 15 + TimescaleDB                  |
| redis          | hedge-redis   | 6379 | Rate limiting, session cache                 |
| api            | hedge-api     | 8000 | FastAPI backend (auth, analytics, SSE)       |
| frontend       | hedge-frontend| 5173 | React/Vite dev server (proxies to api)       |
| n8n            | hedge-n8n     | 5678 | Workflow automation, AI agent orchestration  |

---

## 2. Service Dependency Map

```
postgres (healthy)
    │
    ├──► redis (healthy)
    │         │
    │         └──► api (depends_on: postgres, redis)
    │                   │
    │                   └──► frontend (depends_on: api)
    │
    └──► n8n (standalone, calls api internally)
```

**Startup order:** postgres → redis → api → frontend. n8n starts independently.

---

## 3. Data Flow Diagrams

### Diagram A — Daily Analytics Pipeline (Manual or Scheduled)

```
User clicks "Run Pipeline" (admin)
    │
    ▼
POST /api/v1/analytics/trigger (202 Accepted)
    │
    ├──► asyncio.create_task(_run_pipeline_background)
    │         │
    │         ▼
    │    AnalyticsPipeline.execute_daily_run()
    │         │
    │         ├──► Fetch historical data (price_ticks DB: brent_futures, wti_futures)
    │         ├──► EnsembleForecaster
    │         ├──► HistoricalSimVaR
    │         ├──► BasisRiskAnalyzer
    │         ├──► HedgeOptimizer
    │         ├──► analytics_runs DB (mape, forecast_json, var_results, optimizer_result, status COMPLETED)
    │         └──► hedge_recommendations DB (optimal_hr, instrument_mix, proxy_weights, var_hedged, var_unhedged, status PENDING)
    │
    └──► (Optional) POST /internal/n8n-trigger
              │
              ▼
         n8n webhook /webhook/fuel-hedge-trigger
              │
              ▼
         n8n workflow: Fetch Forecast, VaR, Basis Risk, Optimizer
              │
              ▼
         Data Aggregator → 5 AI Agents (basis_risk, liquidity, operational, ifrs9, macro)
              │
              ▼
         Committee Synthesizer → CRO Risk Gate
              │
              ▼
         POST /api/v1/recommendations (X-N8N-API-Key)
              │
              ▼
         hedge_recommendations DB (PENDING) + PriceEventBroker broadcast
              │
              ▼
         SSE /stream/recommendations → React Dashboard banner
```

### Diagram B — Real-Time Price Stream (Continuous)

```
main.py lifespan
    │
    ▼
PriceService.start() → _price_loop (every 2s)
    │
    ├──► GBM simulation (USE_LIVE_FEED=false) or live fetch
    ├──► history deque (max 500 ticks)
    └──► queue.put_nowait(tick) → subscribers
              │
              ▼
GET /api/v1/stream/prices (SSE)
    │
    ├──► history burst (last 100 ticks)
    └──► live ticks every 2s
              │
              ▼
Vite proxy (/api/v1/stream → api:8000)
              │
              ▼
React useLivePrices → EventSource('/api/v1/stream/prices')
              │
              ▼
LivePriceTicker component → Dashboard
```

### Diagram C — User Approval Workflow

```
PENDING recommendation in DB
    │
    ▼
SSE /stream/recommendations (new_recommendation event)
    │
    ▼
React Dashboard banner "N Pending Recommendations"
    │
    ▼
CFO/Risk Manager → /recommendations
    │
    ▼
POST /recommendations/{id}/approve
    │
    ▼
RecommendationService.approve() → HedgePosition created, AuditLog
    │
    ▼
Status → APPROVED, SSE status_change event
```

---

## 4. FastAPI Conventions

**Router ordering rule:** All specific named routes (`/summary`, `/forecast/latest`, `/mape-history`, `/var-walk-forward`, `/trigger`, `/latest/status`) must be defined **before** the parameterised `/{run_id}` route. FastAPI matches routes in definition order; if `/{run_id}` comes first, paths like `mape-history` and `var-walk-forward` are captured as `run_id` and fail UUID validation (422).

---

## 5. API Endpoint Catalogue

| Method | Path | Auth | Permission | Returns | Called By |
|--------|------|------|------------|---------|-----------|
| POST | /api/v1/auth/login | No | — | LoginResponse | AuthContext |
| POST | /api/v1/auth/refresh | Cookie | — | TokenResponse | api interceptor |
| POST | /api/v1/auth/logout | Cookie | — | MessageResponse | AuthContext |
| GET | /api/v1/auth/me | Cookie | — | UserResponse | AuthContext |
| GET | /api/v1/analytics | Cookie | ANALYST | PaginatedResponse | useAnalyticsHistory |
| GET | /api/v1/analytics/summary | Cookie | ANALYST | DashboardSummaryResponse | useAnalyticsSummary |
| GET | /api/v1/analytics/mape-history | Cookie | ANALYST | list[{date, mape}] | Analytics charts |
| GET | /api/v1/analytics/var-walk-forward | Cookie | ANALYST | list[{date, dynamic_var, static_var}] | Analytics charts |
| GET | /api/v1/analytics/forecast/latest | Cookie | ANALYST | {forecast, run_id, run_date} | useLatestForecast |
| GET | /api/v1/analytics/{run_id} | Cookie | ANALYST | AnalyticsRunDetail | useAnalyticsRun |
| POST | /api/v1/analytics/trigger | Cookie | ADMIN | TriggerPipelineResponse | useTriggerAnalytics |
| GET | /api/v1/analytics/summary/statistics | Cookie | ANALYST | AnalyticsSummary | — |
| GET | /api/v1/analytics/latest/status | Cookie | — | AnalyticsRunResponse | — |
| GET | /api/v1/stream/prices | No | — | EventSourceResponse | useLivePrices |
| GET | /api/v1/stream/status | No | — | dict | — |
| GET | /api/v1/stream/recommendations | No | — | EventSourceResponse | — |
| GET | /api/v1/recommendations | Cookie | — | RecommendationListResponse | useRecommendations |
| GET | /api/v1/recommendations/pending | Cookie | approve:recommendation | list | usePendingRecommendations |
| GET | /api/v1/recommendations/{id} | Cookie | — | HedgeRecommendationResponse | useRecommendation |
| POST | /api/v1/recommendations/{id}/approve | Cookie | approve:recommendation | HedgeRecommendationResponse | useApproveRecommendation |
| POST | /api/v1/recommendations/{id}/reject | Cookie | approve:recommendation | HedgeRecommendationResponse | useRejectRecommendation |
| POST | /api/v1/recommendations/{id}/defer | Cookie | approve:recommendation | HedgeRecommendationResponse | useDeferRecommendation |
| POST | /api/v1/recommendations | Header X-N8N-API-Key | — | RecommendationCreatedResponse | n8n webhook |
| GET | /api/v1/market-data/latest | Cookie | — | LatestPricesResponse | useMarketData |
| GET | /api/v1/market-data/history | Cookie | — | PriceTickList | useMarketData |

---

## 6. Frontend Component → API Hook → Endpoint Map

| Page | Component | Hook | Endpoint |
|------|-----------|------|----------|
| Dashboard | LivePriceTicker | useLivePrices | GET /stream/prices (SSE) |
| Dashboard | KPICard (x4) | useAnalyticsSummary | GET /analytics/summary |
| Dashboard | ForecastChart | useLatestForecast | GET /analytics/forecast/latest |
| Dashboard | AgentStatusGrid | useAnalyticsSummary | GET /analytics/summary |
| Dashboard | Run Pipeline button | useTriggerAnalytics | POST /analytics/trigger |
| Dashboard | Pending recs banner | usePendingRecommendations | GET /recommendations/pending |
| Recommendations | List/table | useRecommendations | GET /recommendations |
| Recommendations | Pending list | usePendingRecommendations | GET /recommendations/pending |
| Analytics | History table | useAnalyticsHistory | GET /analytics |
| Login | Form | AuthContext.login | POST /auth/login |

---

## 7. Environment Variables Reference

| Variable | Service | Purpose | Required | Default |
|----------|---------|---------|----------|---------|
| DATABASE_URL | api | PostgreSQL connection | Yes | — |
| REDIS_URL | api | Redis for rate limiting | Yes | — |
| SECRET_KEY | api | JWT signing | Yes | — |
| ALGORITHM | api | JWT algorithm | No | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | api | Token TTL | No | 240 |
| USE_LIVE_FEED | api | Simulation vs live prices | No | false |
| N8N_INTERNAL_URL | api | n8n base URL (Docker) | No | http://n8n:5678 |
| N8N_TRIGGER_PATH | api | Webhook path for trigger | No | /webhook/fuel-hedge-trigger |
| N8N_WEBHOOK_SECRET | api | API key for n8n→API | Yes | — |
| FRONTEND_ORIGIN | api | CORS origin | No | http://localhost:5173 |
| CORS_ORIGINS | api | Additional CORS origins | No | http://localhost:5173,... |
| VITE_API_BASE_URL | frontend | Leave empty for proxy | No | "" |
| FASTAPI_INTERNAL_URL | n8n | API base for HTTP nodes | No | http://api:8000 |
| OPENAI_API_KEY | n8n | For AI agents (optional) | No | — |

---

## 8. N8N Workflow Node Map

**Workflow:** Fuel Hedging Advisor - v2 (fuel_hedge_advisor_v2.json)

| Node | Type | Input | Output |
|------|------|-------|--------|
| Daily Pipeline Trigger | Webhook | POST /webhook/fuel-hedge-trigger | run_id, analytics_summary |
| Fetch Forecast | HTTP Request | GET /api/v1/analytics/forecast/latest | forecast data |
| Fetch VaR Results | HTTP Request | GET /api/v1/analytics/var/latest | var_usd, var_reduction_pct |
| Fetch Basis Risk | HTTP Request | GET /api/v1/analytics/basis-risk/latest | r2_heating_oil, crack_spread |
| Fetch Optimizer Result | HTTP Request | GET /api/v1/analytics/optimizer/latest | optimal_hr, instrument_mix |
| Data Aggregator | Code | All fetch outputs | market_context |
| Agent: Basis Risk | Code | market_context | agent output (AGENT_OUTPUT_CONTRACT) |
| Agent: Liquidity | Code | market_context | agent output |
| Agent: Operational | Code | market_context | agent output |
| Agent: IFRS9 | Code | market_context | agent output |
| Agent: Macro | Code | market_context | agent output |
| Validate * | Code | agent output | validated output |
| Committee Synthesizer | Code | 5 agent outputs | consensus |
| CRO Risk Gate | Code | consensus | pass/fail |
| POST Recommendation | HTTP Request | POST /api/v1/recommendations | RecommendationCreatedResponse |

**Note:** Analytics endpoints /forecast/latest, /var/latest, /basis-risk/latest, /optimizer/latest may not exist; n8n uses fallbacks in Data Aggregator.

---

## 9. Database Schema Summary

| Table | Purpose | Key Columns | Writes | Reads |
|-------|---------|-------------|--------|-------|
| users | Auth, RBAC | email, role, hashed_password | auth, users | auth, all |
| platform_config | Runtime config | key, value | admin | config_repo |
| price_ticks | Market data (TimescaleDB) | time, jet_fuel_spot, source | pipeline, price_service | market_data_repo |
| analytics_runs | Pipeline runs | run_date, status, mape, var_results | analytics_pipeline | analytics_repo |
| hedge_recommendations | AI recommendations | run_id, optimal_hr, status | pipeline, n8n webhook | recommendation_repo |
| approvals | Approval decisions | recommendation_id, decision | recommendation_service | — |
| hedge_positions | Executed hedges | recommendation_id, status | recommendation_service | positions_repo |
| audit_log | Audit trail | action, resource_type | audit_repo | — |

---

## 10. Services — Singleton Pattern

**PriceEventBroker / PriceService:** The price broker is a module-level singleton accessed via `get_price_broker()` (or equivalent). Never instantiate `PriceEventBroker` directly — always use the getter so the simulation task and all SSE subscribers share the same instance. The health check reads from the same singleton to report `last_tick` and `ticks_per_minute`.

---

## 11. Known Issues

*All previously diagnosed bugs have been resolved. No known issues at this time.*

---

## 12. Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Auth | ✅ Working | JWT in httpOnly cookies |
| SSE prices | ✅ Working | Vite proxy, useLivePrices |
| Dashboard KPI cards | ✅ Working | After first successful pipeline run |
| Analytics pipeline | ✅ Working | Fixed AnalyticsRun/HedgeRecommendation field names |
| Analytics routes | ✅ Working | Named routes before `/{run_id}` |
| mape-history, var-walk-forward | ✅ Working | Return empty list when no runs |
| forecast/latest | ✅ Working | Returns null when no runs |
| Price simulation health | ✅ Working | Uses PriceService.get_status() |
| Recommendations | ⏳ Pending | Empty until n8n workflow imported and activated |

---

## 13. Developer Quick-Start

1. **Clone and configure**
   ```bash
   cd fuel_hedging_proj
   cp .env.example .env  # if exists; set OPENAI_API_KEY for n8n AI
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Verify**
   - `http://localhost:8000/health` → {"status":"healthy"}
   - `http://localhost:5173` → React app
   - `http://localhost:5678` → n8n (admin/admin123)
   - `http://localhost:8000/api/v1/docs` → Swagger

4. **Run migrations** (if applicable)
   ```bash
   docker exec hedge-api alembic upgrade head
   ```

5. **Import n8n workflow**
   - n8n UI → Workflows → Import from `n8n/workflows/fuel_hedge_advisor_v2.json`
   - Activate workflow

6. **Login**
   - Use test user (e.g. test@airline.com / testpass123) if seeded

7. **End-to-end**
   - Login as admin → Run Pipeline → Wait ~8 min → Check recommendations
