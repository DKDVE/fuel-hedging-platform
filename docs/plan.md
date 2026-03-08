# ✈ Fuel Hedging Platform — Cursor AI Implementation Master Plan
> **Version 1.0 · March 2026**  
> Standards-First · Modular Architecture · Zero-Vulnerability · Production-Ready  
> Synthesised from Tech Specs v1.0–v3.0 · 8 Phases · Ready to paste into Cursor Composer

---

## How to Use This Document

1. Work through phases **in order**. Each phase has prerequisites.
2. **Create `.cursorrules` in Phase 0 before anything else** — Cursor reads it automatically in every session.
3. Copy the **CURSOR PROMPT** blocks verbatim into Cursor Composer (`Cmd/Ctrl+Shift+I`).
4. After each phase: read generated files, run tests, commit to git. Never skip ahead with failing tests.
5. One phase per Cursor Composer session for best results.

---

## Quick Reference

| Phase | Name | Est. Time | Prerequisite |
|-------|------|-----------|--------------|
| 0 | Scaffold & `.cursorrules` | 2–3 hrs | None — start here |
| 1A | Database Models | 2–3 hrs | Phase 0 |
| 1B | Repository Pattern | 2–3 hrs | Phase 1A |
| 2A | Domain Objects & Protocols | 1–2 hrs | Phase 0 |
| 2B | Analytics Modules | 4–6 hrs | Phase 2A + 1A |
| 3 | Auth & FastAPI Core | 3–4 hrs | Phase 1B |
| 4 | Data Ingestion & Scheduler | 3–4 hrs | Phase 3 + 2B |
| 5A | Recommendations Router | 2–3 hrs | Phase 4 |
| 5B | All Remaining Routers | 3–4 hrs | Phase 5A |
| 6A | Frontend Foundation | 2–3 hrs | Phase 3 (for types) |
| 6B | All 6 Pages | 5–7 hrs | Phase 6A + 5B |
| 7 | N8N Agent Migration | 3–4 hrs | Phase 5A |
| 8 | CI/CD & Deployment | 2–3 hrs | All phases |

**Total estimated build time: 35–50 hours across 2–3 weeks.**

---

# GLOBAL STANDARDS & ENGINEERING PRINCIPLES

> These rules apply to **every file** in the project. Cursor enforces them via `.cursorrules`.

---

## 1. Code Quality Non-Negotiables

| Rule | Standard | Enforcement |
|------|----------|-------------|
| Type Safety — Python | All functions fully annotated. No implicit `Any`. Run `mypy --strict`. | CI: mypy step |
| Type Safety — TypeScript | `strict: true` in tsconfig. No `any`. No `!.` without a guard. | CI: `tsc --noEmit` |
| Immutability | Python: `@dataclass(frozen=True)` for domain objects. TS: `readonly` arrays for price ticks. | mypy + code review |
| Pure Functions | Analytics modules have zero side effects. All I/O at service layer only. | Architecture rule |
| Single Responsibility | Each module does one thing. Max 200 lines Python, 150 lines TSX. | Code review |
| Dependency Injection | FastAPI services receive db, config, clients via `Depends()`. Never instantiate inside logic. | Architecture rule |
| No Magic Numbers | All domain constants in `constants.py` and `constants.ts`. Never inline. | Linter rule |
| Error Handling | Custom exception hierarchy. Never `catch Exception` silently. | mypy + review |
| Logging | `structlog` with JSON output. Never `print()`. Every analytics run logs: input hash, output hash, duration, model version. | structlog setup |
| Configuration | All config via Pydantic `Settings`. Zero hardcoded values. App crashes at startup if env var missing. | Pydantic Settings |

---

## 2. Security Standards

| Category | Mandatory Rule | Vulnerability Prevented |
|----------|---------------|------------------------|
| Input Validation | Every endpoint uses Pydantic `BaseModel` with `ConfigDict(extra='forbid')` | Mass assignment, injection |
| Authentication | JWT HS256 in `httpOnly + Secure + SameSite=Strict` cookies. Never localStorage. | XSS token theft |
| Authorization | `require_permission(Permission.X)` on every route. Granular permissions, not just roles. | Privilege escalation |
| Secrets | All secrets via env vars. `config.py` raises `ValueError` at startup if missing. Never in code/git/logs. | Credential exposure |
| Rate Limiting | Auth: 5/min. Writes: 20/min. Reads: 120/min. Redis backend. | Brute force, DoS |
| SQL | SQLAlchemy ORM only. No string-formatted SQL. No raw `execute()` with user input. | SQL injection |
| Dependency Security | `pip-audit` + `npm audit` in CI. Block merge on HIGH/CRITICAL CVEs. | Supply chain attacks |
| CORS | Exact origin from `FRONTEND_ORIGIN` env var. Never `*`. | Cross-origin data exfiltration |
| Error Responses | Return only `{detail, error_code}`. Never stack traces, DB query text, or internal paths. | Information disclosure |
| Audit Trail | Every state-changing action writes to `audit_log`: user_id, role, action, before/after state, ip, timestamp. | Non-repudiation |

---

## 3. Architecture Principles

| Principle | Applied To |
|-----------|------------|
| **Layered Architecture**: Routers (HTTP only) → Services (business logic) → Repositories (DB only). No layer skipping. | All FastAPI modules |
| **Domain-Driven Design**: Core objects (`HedgeRecommendation`, `VaRResult`, `ForecastResult`) are frozen dataclasses with no HTTP/SQL knowledge. | `analytics/domain.py` |
| **Repository Pattern**: All DB queries in `repositories/`. Services call repo methods, not `db.execute()`. | All SQLAlchemy access |
| **Interface Segregation**: Analytics modules behind `Protocol` classes — interchangeable implementations. | `analytics/protocols.py` |
| **Configuration as Code**: Constraints (HR cap, collateral limit) stored in DB config table, loaded at runtime. Admin updates via UI. | `config` table |
| **Idempotent Operations**: All ingestion and analytics runs are idempotent. Re-running same date → same result, no duplicates. Use upsert. | Ingestion pipeline |
| **Fail Fast**: Config validation at startup. Type errors caught by mypy. Circuit breaker on external APIs. | `config.py` + API clients |
| **Observability**: Every pipeline run emits structured log: `{run_id, date, duration_ms, mape, var_usd, optimizer_status, model_versions}`. | scheduler + structlog |

---

## 4. Domain Constants

> Source: Phase 1–2 Report + Phase 3 Methodology. These values must never be inlined.

```python
# constants.py — single source of truth
HR_HARD_CAP                 = 0.80   # Maximum hedge ratio (regulatory hard limit)
HR_SOFT_WARN                = 0.70   # Diminishing returns warning threshold (H1)
COLLATERAL_LIMIT            = 0.15   # Max collateral as % of cash reserves
IFRS9_R2_MIN_PROSPECTIVE    = 0.80   # Minimum R² for hedge designation
IFRS9_R2_WARN               = 0.65   # Below this: flag dedesignation risk
IFRS9_RETRO_LOW             = 0.80   # Retrospective effectiveness lower bound
IFRS9_RETRO_HIGH            = 1.25   # Retrospective effectiveness upper bound
MAPE_TARGET                 = 8.0    # Target MAPE % for ensemble forecaster
MAPE_ALERT                  = 10.0   # Model degradation alert threshold
VAR_REDUCTION_TARGET        = 0.40   # Target VaR reduction vs unhedged
MAX_COVERAGE_RATIO          = 1.10   # Over-hedging limit (110% of uplift volume)
PIPELINE_TIMEOUT_MINUTES    = 15     # Daily pipeline SLA
```

---

## 5. Dataset Reference

- **File**: `data/fuel_hedging_dataset.csv`
- **Rows**: 1,827 daily observations (2020-01-01 to 2024-12-31)
- **Columns**: `Date`, `Jet_Fuel_Spot_USD_bbl`, `Heating_Oil_Futures_USD_bbl`, `Brent_Crude_Futures_USD_bbl`, `WTI_Crude_Futures_USD_bbl`, `Crack_Spread_USD_bbl`, `Volatility_Index_pct`
- **Training split**: 2020–2023 (1,461 rows)
- **Validation split**: 2024 (366 rows)

---

# PHASE 0 — PROJECT SCAFFOLD & `.cursorrules`

**Goal**: Create the complete project skeleton and tooling configuration. The `.cursorrules` file is the most critical deliverable — it gives Cursor persistent domain context for every subsequent session. No feature code yet.

---

## Files to Create

```
fuel-hedging-platform/
├── .cursorrules                     ← MOST IMPORTANT — create first
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yml               ← local dev full stack
├── docker-compose.test.yml          ← isolated test environment
├── render.yaml
├── pyproject.toml
├── frontend/
│   ├── package.json
│   ├── tsconfig.json                ← strict: true
│   ├── vite.config.ts
│   └── src/  (empty)
└── python_engine/
    ├── pyproject.toml
    ├── alembic.ini
    └── app/
        ├── __init__.py
        ├── constants.py             ← ALL domain constants
        ├── config.py                ← Pydantic Settings
        └── exceptions.py           ← Custom exception hierarchy
```

---

## The `.cursorrules` File — Full Content

Create this file at the project root before anything else.

```
# ============================================================
# .cursorrules — Fuel Hedging Platform
# Cursor reads this automatically in every session.
# DO NOT SHORTEN — every line prevents a bug or vulnerability.
# ============================================================

## PROJECT IDENTITY
- Aviation fuel hedging optimization platform for an airline
- Backend: FastAPI 0.110 + Python 3.11 + SQLAlchemy 2.0 async + Pydantic v2
- Frontend: React 18 + TypeScript 5 + TailwindCSS 3 + React Query v5 + Recharts
- Auth: JWT (HS256) in httpOnly cookies — NEVER localStorage
- Database: PostgreSQL 15 + TimescaleDB extension
- Deployment: GitHub Pages (frontend) + Render.com (backend)

## DOMAIN CONSTANTS — never inline these values in code
HR_HARD_CAP = 0.80
HR_SOFT_WARN = 0.70
COLLATERAL_LIMIT = 0.15
IFRS9_R2_MIN_PROSPECTIVE = 0.80
IFRS9_R2_WARN = 0.65
IFRS9_RETRO_LOW = 0.80
IFRS9_RETRO_HIGH = 1.25
MAPE_TARGET = 8.0
MAPE_ALERT = 10.0
VAR_REDUCTION_TARGET = 0.40
MAX_COVERAGE_RATIO = 1.10
PIPELINE_TIMEOUT_MINUTES = 15

## DATASET
- File: data/fuel_hedging_dataset.csv
- 1,827 daily observations: 2020-01-01 to 2024-12-31
- Columns: Date, Jet_Fuel_Spot_USD_bbl, Heating_Oil_Futures_USD_bbl,
           Brent_Crude_Futures_USD_bbl, WTI_Crude_Futures_USD_bbl,
           Crack_Spread_USD_bbl, Volatility_Index_pct
- Training split: 2020–2023 (1,461 rows)
- Validation split: 2024 (366 rows)

## PYTHON CODING RULES
- All functions must have full type annotations (args + return type)
- Use @dataclass(frozen=True) for all domain objects
- Use Pydantic BaseModel for all API request/response schemas
- model_config = ConfigDict(extra='forbid') on all Pydantic models
- Custom exceptions only — never raise Exception() or ValueError() directly
- Use structlog for all logging — never print()
- Use httpx.AsyncClient for all external HTTP — never requests
- Repository pattern: all DB access in repositories/ — never in routers or services
- Dependency injection via FastAPI Depends() — never instantiate services inside functions
- All DB operations must be async (await) — never sync SQLAlchemy in async context
- Use alembic for all schema changes — never modify DB schema in application code

## TYPESCRIPT CODING RULES
- strict: true in tsconfig.json — no exceptions
- No 'any' type — use 'unknown' and narrow, or define proper types
- No non-null assertions (!.) without a preceding type guard
- API types in src/types/api.ts — must exactly match backend Pydantic response schemas
- All API calls through src/lib/api.ts (axios instance with interceptors)
- Custom hooks for all SSE/WebSocket/data-fetching logic
- React Hook Form + Zod for all forms
- Error boundaries on every page component

## SECURITY RULES — never violate
- NEVER put secrets, API keys, or tokens in code, comments, or git
- NEVER use string formatting to build SQL queries
- NEVER use localStorage for sensitive data
- ALWAYS validate and sanitize all inputs before processing
- ALWAYS use parameterized queries via SQLAlchemy ORM
- Rate limit every endpoint: auth 5/min, writes 20/min, reads 120/min
- Return only {detail, error_code} in error responses — no stack traces
- httpOnly + Secure + SameSite=Strict on all auth cookies

## API CONVENTIONS
- Base URL prefix: /api/v1/  (versioned from day one)
- Auth: Bearer JWT in Authorization header for programmatic clients
        httpOnly cookie 'access_token' for browser clients
- All monetary values: USD, 2 decimal places, as float
- All dates: ISO 8601 UTC strings (e.g. '2024-03-15T06:00:00Z')
- Pagination: ?page=1&limit=50 (max limit 200)
- Errors: HTTP 400 validation, 401 unauthenticated, 403 forbidden,
          404 not found, 409 conflict, 422 schema invalid, 500 internal

## FILE NAMING
- Python: snake_case files/functions; PascalCase classes
- React: PascalCase components (Button.tsx); camelCase hooks (useLivePrices.ts)
- Tests: test_{module}.py (Python); {Component}.test.tsx (React)

## AGENT OUTPUT CONTRACT — all 5 n8n agents must return this exact shape
{
  agent_id: string,        // 'basis_risk'|'liquidity'|'operational'|'ifrs9'|'macro'
  risk_level: 'LOW'|'MODERATE'|'HIGH'|'CRITICAL',
  recommendation: string,
  metrics: Record<string, number>,
  constraints_satisfied: boolean,
  action_required: boolean,
  ifrs9_eligible: boolean | null,
  generated_at: string     // ISO 8601 UTC
}

## ARCHITECTURE REMINDER
- Routers:     HTTP handling only — call service layer, return response
- Services:    Business logic — call repositories + analytics modules
- Repositories: DB access only — no business logic
- Analytics:   Pure functions — no I/O, no DB, no HTTP
- Models:      SQLAlchemy ORM in db/models.py
- Schemas:     Pydantic request/response in schemas/ (separate from models)
```

---

## CURSOR PROMPT — Phase 0: Scaffold

```
Create the complete project scaffold for a fuel hedging platform following every rule in .cursorrules.

1. docker-compose.yml with 4 services: api (FastAPI), postgres (PostgreSQL 15 + TimescaleDB),
   n8n (background worker), redis (for rate limiting). Named volumes for postgres and n8n data.
   All services on bridge network 'hedge-net'. API depends_on postgres with healthcheck.

2. python_engine/app/constants.py — ALL domain constants from .cursorrules with type annotations.
   Add a docstring on each explaining its source (H1 hypothesis, IFRS9 standard, Phase 1 spec).

3. python_engine/app/config.py using Pydantic BaseSettings. Fields:
   DATABASE_URL, JWT_SECRET_KEY, JWT_ALGORITHM='HS256',
   ACCESS_TOKEN_EXPIRE_MINUTES=30, REFRESH_TOKEN_EXPIRE_DAYS=7,
   EIA_API_KEY, CME_API_KEY, ICE_API_KEY, OPENAI_API_KEY, N8N_WEBHOOK_SECRET,
   FRONTEND_ORIGIN, REDIS_URL, ENVIRONMENT='development', LOG_LEVEL='INFO', SENTRY_DSN=None.
   Raise ValueError with clear messages for any missing required field.
   Export a single `get_settings` function with @lru_cache.

4. python_engine/app/exceptions.py — custom exception hierarchy:
   HedgePlatformError (base) →
     ConstraintViolationError (HR/collateral breaches),
     DataIngestionError (API failures, data quality failures),
     ModelError (MAPE exceeded, optimizer non-convergence),
     AuthorizationError (permission denied),
     AuditError (audit write failures).
   Each exception has: message (str), error_code (snake_case str), context (dict, optional).

5. pyproject.toml with all Python deps pinned to exact versions:
   fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, pydantic[email],
   python-jose[cryptography], passlib[bcrypt], httpx, structlog, slowapi, redis,
   apscheduler, pandas, numpy, scipy, statsmodels, scikit-learn, xgboost,
   tensorflow-cpu, pytest, pytest-asyncio, pytest-cov, mypy, ruff.

6. frontend/tsconfig.json with strict: true, strictNullChecks: true, noUncheckedIndexedAccess: true.

7. .pre-commit-config.yaml with hooks: ruff, mypy, detect-secrets, prettier, eslint.

8. .gitignore covering: .env, __pycache__, .mypy_cache, node_modules, dist, models/*.h5,
   models/*.pkl, models/*.json (model artifacts committed separately via CI).
```

---

# PHASE 1 — DATABASE LAYER

**Goal**: Build the complete database layer before any API or business logic. Every phase reads/writes through this layer.

---

## Module Structure

```
python_engine/app/
├── db/
│   ├── __init__.py
│   ├── base.py           ← DeclarativeBase, async engine, session factory
│   ├── models.py         ← ALL SQLAlchemy ORM models
│   └── seed.py           ← Dev seed: admin user + default config values
├── repositories/
│   ├── __init__.py
│   ├── base.py           ← Generic async CRUD base class
│   ├── users.py
│   ├── recommendations.py
│   ├── positions.py
│   ├── audit.py
│   ├── analytics.py
│   ├── market_data.py
│   └── config.py
└── alembic/versions/
    └── 001_initial_schema.py
```

---

## Database Design Rules

- Every table has: `id` (UUID PK, default `uuid4`), `created_at`, `updated_at` (auto-managed)
- **No integer IDs** — UUIDs prevent enumeration attacks
- **Monetary columns**: `Numeric(15,2)` — never `Float` (floating point precision errors in finance)
- **Hedge ratio**: `Numeric(5,4)` — 4 decimal places (e.g. `0.6750` = 67.50%)
- All JSONB columns have CHECK constraints validating required keys exist
- `price_ticks` is a **TimescaleDB hypertable** partitioned by `time`
- All foreign keys use `ondelete='RESTRICT'` — no accidental cascading deletes

---

## Models Reference

| Model | Key Columns | Critical Constraints |
|-------|-------------|----------------------|
| `User` | id UUID, email UNIQUE, hashed_password, role ENUM, is_active BOOL, last_login | role in ('analyst','risk_manager','cfo','admin') |
| `PlatformConfig` | id UUID, key VARCHAR UNIQUE, value JSONB, description, updated_by FK | key in allowed_keys CHECK |
| `PriceTick` *(hypertable)* | time TIMESTAMP, jet_fuel_spot, heating_oil_futures, brent_futures, wti_futures, crack_spread, volatility_index, quality_flag | UNIQUE(time, source); NOT NULL prices |
| `AnalyticsRun` | id UUID, run_date DATE UNIQUE, mape, forecast_json, var_results, basis_metrics, optimizer_result, model_versions, duration_seconds, status | status in ('RUNNING','COMPLETED','FAILED') |
| `HedgeRecommendation` | id UUID, run_id FK, optimal_hr, instrument_mix JSONB, proxy_weights JSONB, var_hedged, var_unhedged, var_reduction_pct, collateral_usd, agent_outputs JSONB, status, sequence_number SERIAL | status in ('PENDING','APPROVED','REJECTED','DEFERRED','EXPIRED'); CHECK optimal_hr <= 0.80 |
| `Approval` | id UUID, recommendation_id FK, approver_id FK, decision, response_lag_minutes, override_reason, ip_address INET | decision in ('APPROVE','REJECT','DEFER'); ondelete RESTRICT |
| `HedgePosition` | id UUID, recommendation_id FK, instrument_type, proxy, notional_usd, hedge_ratio, entry_price, expiry_date, collateral_usd, ifrs9_r2, status | instrument_type in ('FUTURES','OPTIONS','COLLAR','SWAP') |
| `AuditLog` | id UUID, user_id FK, action, resource_type, resource_id UUID, before_state JSONB, after_state JSONB, ip_address INET, user_agent | created_at indexed; action indexed |

---

## CURSOR PROMPT — Phase 1A: Database Models

```
Create python_engine/app/db/models.py with ALL SQLAlchemy 2.0 async ORM models.
Follow every rule in .cursorrules.

Requirements:
- Use DeclarativeBase from sqlalchemy.orm
- Use mapped_column() and Mapped[] syntax (SQLAlchemy 2.0 — not Column())
- UUID primary keys using uuid.uuid4 as default
- All monetary columns: Numeric(15,2) — never Float
- Timestamps: DateTime(timezone=True) with server_default=func.now()
- All ENUM types defined as Python Enum classes first, then passed to SQLAlchemy Enum()
- Add __tablename__ and __repr__ to every model
- Add class-level docstring explaining each model's domain purpose
- Import all models in db/__init__.py so Alembic can detect them

Create db/base.py with:
- Async engine created from config.DATABASE_URL
- AsyncSessionLocal factory using async_sessionmaker
- get_db() async generator dependency for FastAPI injection
- DeclarativeBase subclass with the UUID + timestamp mixin built in

Create alembic/versions/001_initial_schema.py:
- upgrade(): creates all tables in correct FK dependency order
- downgrade(): drops all tables in reverse order
- Mark price_ticks as TimescaleDB hypertable in upgrade() using:
  op.execute("SELECT create_hypertable('price_ticks', 'time')")
```

---

## CURSOR PROMPT — Phase 1B: Repository Pattern

```
Create python_engine/app/repositories/base.py with a generic async repository:

class BaseRepository(Generic[ModelT]):
    def __init__(self, db: AsyncSession)
    async def get_by_id(self, id: UUID) -> ModelT | None
    async def create(self, obj: ModelT) -> ModelT
    async def update(self, obj: ModelT) -> ModelT
    async def delete(self, id: UUID) -> bool
    async def count(self) -> int

Then create concrete repositories extending BaseRepository for:
users, recommendations, positions, audit, analytics, market_data, config.

Add domain-specific methods:
- RecommendationRepository: get_pending(), update_status(), get_history(limit)
- MarketDataRepository: upsert_tick() using ON CONFLICT DO UPDATE (idempotent)
- AuditRepository: log_action() — must NEVER raise; if write fails, log to stderr only
- AnalyticsRepository: get_mape_history(n_days), get_by_date(date)
- ConfigRepository: get(key), set(key, value, user_id), get_constraints_snapshot()

Rules:
- All methods are async
- Use select() statements, not session.query() (SQLAlchemy 2.0 style)
- Never catch generic Exception — let DB errors propagate to service layer
- Upsert methods use insert().on_conflict_do_update() for idempotency
```

---

# PHASE 2 — ANALYTICS ENGINE

**Goal**: Implement all quantitative analytics as pure, testable Python modules with no I/O dependencies.

---

## Module Structure

```
python_engine/app/analytics/
├── __init__.py
├── protocols.py          ← Abstract Protocol interfaces for all engines
├── domain.py             ← Frozen dataclasses: ForecastResult, VaRResult,
│                           OptimizationResult, BasisRiskMetric
├── forecaster/
│   ├── __init__.py
│   ├── arima.py          ← ArimaForecaster (pure)
│   ├── lstm.py           ← LSTMForecaster (inference only on Render)
│   ├── xgboost_model.py  ← XGBoostForecaster (pure)
│   └── ensemble.py       ← EnsembleForecaster: combines 3, returns ForecastResult
├── optimizer/
│   ├── __init__.py
│   ├── constraints.py    ← Constraint definitions (loaded from DB config, not hardcoded)
│   └── hedge_optimizer.py← HedgeOptimizer: scipy SLSQP, returns OptimizationResult
├── risk/
│   ├── __init__.py
│   ├── var_engine.py     ← HistoricalSimVaR: non-parametric, returns VaRResult
│   └── stress_test.py    ← StressTestEngine: 5 scenario definitions
└── basis/
    ├── __init__.py
    └── basis_risk.py     ← BasisRiskAnalyzer: rolling R², crack spread, proxy selection
```

---

## Domain Objects

```python
# analytics/domain.py — all objects are frozen (immutable after creation)
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass(frozen=True)
class ForecastResult:
    forecast_values: tuple[float, ...]    # 30-day ahead prices
    mape: float                            # Mean Absolute Percentage Error %
    mape_passes_target: bool               # mape < MAPE_TARGET
    model_weights: dict[str, float]        # {'arima': 0.25, 'lstm': 0.45, 'xgb': 0.30}
    horizon_days: int
    generated_at: datetime
    model_versions: dict[str, str]

@dataclass(frozen=True)
class VaRResult:
    hedge_ratio: float
    var_pct: float                         # VaR as % of notional
    var_usd: float
    cvar_usd: float                        # Conditional VaR (Expected Shortfall)
    confidence: float                      # e.g. 0.95
    holding_period_days: int
    n_observations: int

@dataclass(frozen=True)
class OptimizationResult:
    optimal_hr: float
    instrument_mix: dict[str, float]       # futures/options/collars/swaps
    proxy_weights: dict[str, float]        # heating_oil/brent/wti
    objective_value: float
    solver_converged: bool
    collateral_usd: float
    collateral_pct_of_reserves: float
    solve_time_seconds: float
    constraint_violations: list[str]       # empty if all satisfied

@dataclass(frozen=True)
class BasisRiskMetric:
    r2_heating_oil: float
    r2_brent: float
    r2_wti: float
    crack_spread_current: float
    crack_spread_zscore: float
    risk_level: Literal['LOW', 'MODERATE', 'HIGH', 'CRITICAL']
    recommended_proxy: Literal['heating_oil', 'brent', 'wti']
    ifrs9_eligible: bool                   # r2_heating_oil >= IFRS9_R2_MIN_PROSPECTIVE
```

---

## Critical Implementation Rules

- **Optimizer constraints** come from the DB config dict (passed in as parameter) — not from `constants.py`. This allows admin to update limits at runtime without redeployment.
- **LSTM on Render**: always load from `/models/lstm_model.h5` — never train. Training only runs in GitHub Actions `lstm-retrain.yml` workflow.
- **Fixed random seeds** for reproducibility: `numpy.random.seed(42)`, `tf.random.set_seed(42)`, XGBoost `random_state=42`.
- **Analytics modules never raise for business rule violations** — they return the result with a flag (e.g. `mape_passes_target=False`, `solver_converged=False`). The service layer decides what to do.
- **VaR engine**: raises `ModelError` only if `n_observations < 252`. Otherwise always returns a result.

---

## CURSOR PROMPT — Phase 2A: Domain Objects & Protocols

```
Create python_engine/app/analytics/domain.py with all frozen dataclasses shown above.

Create python_engine/app/analytics/protocols.py with @runtime_checkable Protocol classes:

class Forecaster(Protocol):
    def predict(self, df: pd.DataFrame) -> ForecastResult: ...

class RiskEngine(Protocol):
    def compute_var(self, df: pd.DataFrame, hedge_ratio: float, notional: float) -> VaRResult: ...
    def var_curve(self, df: pd.DataFrame, notional: float) -> list[VaRResult]: ...

class Optimizer(Protocol):
    def optimize(self, var_metrics: dict, constraints: dict) -> OptimizationResult: ...

class BasisAnalyzer(Protocol):
    def analyze(self, df: pd.DataFrame) -> BasisRiskMetric: ...

Add comprehensive docstrings. All Protocol classes are @runtime_checkable.
```

---

## CURSOR PROMPT — Phase 2B: Analytics Modules

```
Create all 4 analytics modules implementing the Protocol interfaces from Phase 2A.

1. forecaster/ensemble.py — EnsembleForecaster:
   - Sub-forecasters injected in __init__ (dependency injection — do not instantiate inside)
   - Weights configurable, default {'arima':0.25,'lstm':0.45,'xgb':0.30}
   - MAPE calculated on last horizon_days of input vs forecast
   - Returns ForecastResult; never raises for business rule violations

2. risk/var_engine.py — HistoricalSimVaR:
   - Non-parametric historical simulation on full dataset
   - var_curve() returns list[VaRResult] at 0%, 20%, 40%, 60%, 70%, 80%, 100% HR
   - Include marginal_reduction_pct between consecutive points for H1 validation
   - Raises ModelError (not generic exception) if n_observations < 252

3. optimizer/hedge_optimizer.py — HedgeOptimizer:
   - Constraints dict passed at call time — loaded from DB by service layer
   - 8 decision variables: hedge_ratio, pct_futures, pct_options, pct_collars, pct_swaps,
     w_heating_oil, w_brent, w_wti
   - Returns OptimizationResult with constraint_violations list
   - If solver does not converge: return result with solver_converged=False — never raise

4. basis/basis_risk.py — BasisRiskAnalyzer:
   - Rolling 30/90/180-day R² for heating oil, Brent, WTI vs jet fuel
   - Crack spread z-score (current vs 5-year mean/std)
   - risk_level: LOW(<1σ), MODERATE(1-2σ), HIGH(2-3σ), CRITICAL(>3σ)
   - ifrs9_eligible = r2_heating_oil >= IFRS9_R2_MIN_PROSPECTIVE (from constants)

Write unit tests in tests/test_analytics/ for each module.
Use pytest fixtures with fixed seed=42 data sliced from fuel_hedging_dataset.csv.
Test: boundary conditions, minimum observations, HR at hard cap, optimizer non-convergence.
```

---

# PHASE 3 — AUTH & FASTAPI CORE

**Goal**: Build the FastAPI application with complete middleware stack and authentication. All subsequent phases add routers onto this foundation.

---

## Module Structure

```
python_engine/app/
├── main.py
├── middleware/
│   ├── __init__.py
│   ├── security_headers.py   ← HSTS, CSP, X-Frame-Options, etc.
│   ├── request_id.py         ← Injects X-Request-ID for log correlation
│   └── audit.py              ← Logs every state-changing request
├── auth/
│   ├── __init__.py
│   ├── tokens.py             ← JWT create/decode/refresh
│   ├── permissions.py        ← Permission enum + require_permission() dependency
│   ├── password.py           ← bcrypt hash/verify
│   └── cookie.py             ← httpOnly cookie helpers
├── routers/v1/
│   ├── __init__.py
│   └── auth.py               ← POST /login, POST /refresh, POST /logout
└── schemas/
    ├── __init__.py
    ├── auth.py               ← LoginRequest, TokenResponse, UserResponse
    └── common.py             ← PaginatedResponse, ErrorResponse, HealthResponse
```

---

## Middleware Stack — Exact Order

| Order | Middleware | Purpose |
|-------|-----------|---------|
| 1 (outermost) | `RequestIDMiddleware` | Adds `X-Request-ID` UUID to every request/response; injects into structlog context |
| 2 | `SecurityHeadersMiddleware` | HSTS, CSP (`default-src 'self'; connect-src 'self' wss:`), X-Frame-Options DENY, nosniff |
| 3 | `CORSMiddleware` | Exact origin from `config.FRONTEND_ORIGIN`. Never wildcard. `allow_credentials=True`. |
| 4 | `RateLimitMiddleware` | slowapi + Redis. Global limits; per-route limits enforced at route level. |
| 5 (innermost) | `AuditMiddleware` | Logs every POST/PATCH/DELETE to audit_log. Async write, non-blocking. |

---

## Permission System

```python
# auth/permissions.py
class Permission(str, Enum):
    READ_ANALYTICS    = 'read:analytics'
    READ_POSITIONS    = 'read:positions'
    READ_AUDIT        = 'read:audit'
    APPROVE_REC       = 'approve:recommendation'
    ESCALATE_REC      = 'escalate:recommendation'
    EDIT_CONFIG       = 'edit:config'
    MANAGE_USERS      = 'manage:users'
    TRIGGER_PIPELINE  = 'trigger:pipeline'
    ROLLBACK_MODEL    = 'rollback:model'

ROLE_PERMISSIONS = {
    'analyst':      {READ_ANALYTICS, READ_POSITIONS},
    'risk_manager': {READ_ANALYTICS, READ_POSITIONS, READ_AUDIT, APPROVE_REC},
    'cfo':          {READ_ANALYTICS, READ_POSITIONS, READ_AUDIT, APPROVE_REC, ESCALATE_REC},
    'admin':        set(Permission),  # all permissions
}
```

---

## CURSOR PROMPT — Phase 3: Auth & Application Core

```
Build the FastAPI application core following the structure above.

main.py:
- Use lifespan context manager (not deprecated on_event handlers)
- Startup: validate config, init DB pool, init Redis, start APScheduler,
  load model artifacts from /models/ directory into app.state
- Shutdown: close DB pool, stop scheduler, flush structlog
- Apply middleware in exact order: RequestID → Security → CORS → RateLimit → Audit
- Mount all v1 routers under /api/v1/
- Disable docs_url and redoc_url when ENVIRONMENT == 'production'
- Global exception handlers:
    HedgePlatformError → 400 with {detail, error_code}
    AuthorizationError → 403 with {detail, error_code}
    RequestValidationError → 422 with field-level detail
    unhandled Exception → log full traceback via structlog, return 500 with generic message only

auth/tokens.py:
- create_access_token(user_id: UUID, role: str) → str
- create_refresh_token(user_id: UUID) → str
- decode_token(token: str) → TokenPayload  (raises AuthorizationError on invalid/expired)
- Tokens include: sub, role, jti (unique ID for future revocation), exp, iat

auth/permissions.py:
- Permission enum and ROLE_PERMISSIONS dict as shown above
- require_permission(permission: Permission) → FastAPI dependency function
  Raises AuthorizationError with error_code='insufficient_permissions' if role lacks permission

POST /api/v1/auth/login:
- Accept LoginRequest{email, password}, validated by Pydantic
- Verify password with bcrypt — constant-time comparison
- Return 200 with UserResponse in body
- Set httpOnly + Secure + SameSite=Strict cookies: access_token, refresh_token
- Write audit log entry: action='login', resource_type='user'
- Rate limit: 5 attempts per minute per IP

GET /api/v1/health — public, no auth:
- Returns {status, version, environment, db_connected, redis_connected, uptime_seconds}

GET /api/v1/health/sources — public:
- Returns last fetch timestamp + HTTP status for EIA, CME, ICE, n8n
- Used by nightly-validation.yml GitHub Actions workflow
```

---

# PHASE 4 — DATA INGESTION & SCHEDULER

**Goal**: Automated market data pipeline and APScheduler. All external API calls isolated in client modules with circuit breaker patterns.

---

## Module Structure

```
python_engine/app/
├── clients/
│   ├── __init__.py
│   ├── base.py           ← BaseAPIClient: retry, circuit breaker, timeout
│   ├── eia.py            ← EIAClient: jet fuel spot prices
│   ├── cme.py            ← CMEClient: heating oil + WTI futures
│   └── ice.py            ← ICEClient: Brent crude futures
├── ingestion/
│   ├── __init__.py
│   ├── pipeline.py       ← IngestionPipeline: orchestrates all 3 clients
│   ├── quality.py        ← DataQualityChecker: nulls, 3σ outliers, staleness
│   └── normalizer.py     ← Normalizes raw API responses → PriceTick domain objects
└── scheduler/
    ├── __init__.py
    ├── scheduler.py      ← APScheduler AsyncIOScheduler setup
    └── jobs/
        ├── daily.py      ← run_daily_pipeline()
        ├── weekly.py     ← run_weekly_retrain() — ARIMA + XGBoost only on Render
        └── monthly.py    ← run_monthly_stress_test()
```

---

## Data Quality Rules

| Check | Failure Action |
|-------|---------------|
| Null/None prices | `quality_flag='NULL_DETECTED'`; use previous-day value; never use 0 |
| 3σ outlier | `quality_flag='OUTLIER_SUSPECTED'`; store value but flag; send alert |
| Staleness > 2 hours | `quality_flag='STALE'`; pause analytics pipeline; send alert |
| Crack spread mismatch | Recalculate if `\|raw - computed\| > 0.01`; log original + recalculated |
| Gap > 3 business days | Log missing dates; attempt backfill via EIA historical endpoint |

---

## CURSOR PROMPT — Phase 4: Ingestion Pipeline & Scheduler

```
Build the complete data ingestion pipeline and APScheduler.

clients/base.py — BaseAPIClient:
- Uses httpx.AsyncClient (async required — never requests library)
- Constructor: __init__(self, api_key: str, base_url: str, timeout: int = 10)
- _fetch(method, path, params) → dict: retry with exponential backoff (3 attempts: 1s, 2s, 4s)
- Circuit breaker: consecutive_failures counter + opened_at timestamp
  If circuit open: raise DataIngestionError immediately, no network attempt
  Half-open after 60s: allow one test request
- Log every attempt: {client_name, method, path, status_code, duration_ms, request_id}
- Clients return typed domain objects — never raw HTTP responses

ingestion/quality.py — DataQualityChecker:
- check(ticks: list[PriceTick], historical_df: pd.DataFrame) → QualityReport
- QualityReport is a frozen dataclass: passed (bool), issues (list[str]),
  flagged_columns (dict[str,str]), recommendations (list[str])
- Pure function — no side effects, no DB access, no logging

scheduler/jobs/daily.py — run_daily_pipeline():
Step 1: Ingest from all 3 clients in parallel using asyncio.gather()
Step 2: Run quality check — if QualityReport.passed is False, log WARNING but continue
Step 3: Upsert to price_ticks (idempotent — same date = update, not insert)
Step 4: Load full dataset from DB → pd.DataFrame (all columns, sorted by date)
Step 5: Run analytics sequentially:
        forecast = ensemble_forecaster.predict(df)
        var_curve = var_engine.var_curve(df, notional_usd)
        basis = basis_analyzer.analyze(df)
        constraints = await config_repo.get_constraints_snapshot()
        optimization = optimizer.optimize(var_metrics, constraints)
Step 6: Store AnalyticsRun record with all results + model_versions + duration_seconds
Step 7: POST to n8n webhook via httpx: {run_id, analytics_summary, trigger_type='scheduled'}
Wrap in try/except: on any failure, update AnalyticsRun.status='FAILED', log structlog ERROR
If total duration > 14 minutes: log WARNING (approaching 15-min SLA)
If total duration > 15 minutes: log ERROR + trigger alert
```

---

# PHASE 5 — API ROUTERS

**Goal**: All 28 API endpoints. Routers call service layer only. Zero business logic in routers.

---

## Complete Endpoint Map

| Prefix | Method + Path | Permission | Response |
|--------|--------------|------------|----------|
| `/api/v1/analytics` | GET `/forecast/latest` | READ_ANALYTICS | ForecastResponse |
| | GET `/var/curve?notional_usd=` | READ_ANALYTICS | VaRCurveResponse |
| | GET `/var/latest` | READ_ANALYTICS | VaRResult |
| | GET `/basis-risk/latest` | READ_ANALYTICS | BasisRiskMetric |
| | GET `/hypothesis-status` | READ_ANALYTICS | H1–H4 status + metrics |
| | GET `/walk-forward?periods=` | READ_ANALYTICS | WalkForwardResponse |
| | GET `/mape-history?days=` | READ_ANALYTICS | list[{date, mape, model_version}] |
| `/api/v1/recommendations` | GET `/` | READ_ANALYTICS | PaginatedResponse |
| | GET `/{id}` | READ_ANALYTICS | RecommendationDetail (with agent outputs) |
| | GET `/pending` | APPROVE_REC | list[RecommendationSummary] |
| | GET `/latest` | READ_ANALYTICS | RecommendationSummary \| null |
| | PATCH `/{id}/decision` | APPROVE_REC | RecommendationSummary |
| | POST `/` *(n8n webhook)* | API key header | {id, status} |
| `/api/v1/positions` | GET `/open` | READ_POSITIONS | list[HedgePositionResponse] |
| | GET `/collateral-summary` | READ_POSITIONS | CollateralSummary |
| | GET `/expiring?days=` | READ_POSITIONS | list[HedgePositionResponse] |
| `/api/v1/audit` | GET `/approvals` | READ_AUDIT | PaginatedResponse |
| | GET `/ifrs9` | READ_AUDIT | list[IFRS9Record] |
| | GET `/kpi-history?days=` | READ_AUDIT | list[KpiRecord] |
| | GET `/export?format=csv` | READ_AUDIT | StreamingResponse |
| `/api/v1/config` | GET `/constraints` | READ_ANALYTICS | ConstraintsConfig |
| | PATCH `/constraints` | EDIT_CONFIG | ConstraintsConfig |
| | GET `/users` | MANAGE_USERS | list[UserResponse] |
| | POST `/users` | MANAGE_USERS | UserResponse |
| | PATCH `/users/{id}` | MANAGE_USERS | UserResponse |
| `/api/v1/stream` | GET `/prices` | READ_ANALYTICS | SSE stream |
| | GET `/positions` | READ_POSITIONS | SSE stream |
| | WS `/ws/approvals` | APPROVE_REC | WebSocket |

---

## Service Layer Structure

```
python_engine/app/services/
├── analytics_service.py       ← Loads dataset, runs analytics modules, stores results
├── recommendation_service.py  ← Approval workflow, WebSocket broadcast, escalation
├── position_service.py        ← Creates positions from approved recs, tracks collateral
├── audit_service.py           ← Audit records, compliance reports
├── config_service.py          ← Platform config reads/writes, cache invalidation
└── stream_service.py          ← SSE queue broker + WebSocket connection manager
```

---

## CURSOR PROMPT — Phase 5A: Recommendations Router (most critical)

```
Build the recommendations router and service — this is the core approval workflow.

routers/v1/recommendations.py:
- GET /pending: returns PENDING recommendations, cached 30s, permission APPROVE_REC
- PATCH /{id}/decision:
    Validates body: DecisionPayload{decision: Literal['APPROVE','REJECT','DEFER'], reason: str = ''}
    model_config = ConfigDict(extra='forbid') — reject unknown fields
    Calls recommendation_service.decide()
    Broadcasts WebSocket event to all connected clients
    Writes audit log entry
    Rate limit: 20/minute per user
- POST / (n8n webhook):
    Auth via X-N8N-API-Key header (not JWT) — validate against config.N8N_WEBHOOK_SECRET
    Validates payload against strict AgentOutputPayload Pydantic model
    Creates recommendation via recommendation_service.create_from_agent_output()
    Triggers SSE event 'new_recommendation' to all price stream subscribers

services/recommendation_service.py:
- create_from_agent_output(payload) → HedgeRecommendation:
    Load current constraints from ConfigRepository
    Validate optimal_hr <= HR_HARD_CAP — if violated: status='CONSTRAINT_VIOLATED'
    Validate collateral_pct <= COLLATERAL_LIMIT — if violated: status='CONSTRAINT_VIOLATED'
    Write audit log entry with before_state=None, after_state=recommendation dict

- decide(rec_id, decision, reason, user, ip_address) → HedgeRecommendation:
    Fetch recommendation — raise ConstraintViolationError (404 behaviour) if not found
    Raise ConstraintViolationError if status != 'PENDING' (error_code='already_decided')
    Update status in DB via RecommendationRepository
    If APPROVED: create HedgePosition records via PositionService
    If DEFERRED: schedule one-time APScheduler job to re-escalate after 24h
    Broadcast WebSocket event: {type:'recommendation_update', id:rec_id, status:decision}
    Write audit log: action='recommendation_decision', before_state, after_state, user_id, ip

- escalate_pending(): triggered by APScheduler 4h after recommendation created, still PENDING
    Set escalation_flag=True on recommendation
    Broadcast WebSocket event: {type:'escalation_required', id:rec_id}
```

---

## CURSOR PROMPT — Phase 5B: SSE & WebSocket Streaming

```
Build real-time streaming infrastructure in services/stream_service.py and routers/v1/stream.py.

PriceEventBroker (in stream_service.py):
- Manages asyncio.Queue per subscriber (max 100 subscribers, max 50 items per queue)
- subscribe() → asyncio.Queue
- unsubscribe(queue: asyncio.Queue)
- publish(tick: PriceTick): puts to all queues; if queue full, drops oldest item (never blocks)

ApprovalWebSocketManager (in stream_service.py):
- connect(ws: WebSocket, user_id: UUID, role: str)
- disconnect(ws: WebSocket)
- broadcast_to_role(role: str, event: dict): send only to connections with matching role
- broadcast_all(event: dict): send to all connections

GET /api/v1/stream/prices (SSE):
- Authenticate via JWT from cookie (browser SSE cannot send custom headers)
- Subscribe to PriceEventBroker
- Generator: yields 'data: {json}\n\n' per tick, ': keepalive\n\n' every 30s (prevents proxy timeout)
- On client disconnect (GeneratorExit or asyncio.CancelledError): unsubscribe from broker
- Response headers: Cache-Control: no-cache, X-Accel-Buffering: no, Content-Type: text/event-stream

WS /api/v1/stream/ws/approvals:
- First message MUST be {type:'auth', token:'<jwt>'} — validate with decode_token()
- If auth fails: send {type:'error', message:'unauthorized'} and ws.close(code=4001)
- After auth: register in ApprovalWebSocketManager with user_id and role
- Heartbeat: server sends {type:'ping'} every 30s; if no pong within 10s: close connection
- On disconnect: remove from ApprovalWebSocketManager
```

---

# PHASE 6 — REACT FRONTEND

**Goal**: All 6 pages following atomic design. `types/api.ts` is the single source of truth. Real-time features use custom hooks.

---

## Directory Structure

```
frontend/src/
├── types/
│   ├── api.ts            ← ALL API types (match backend Pydantic schemas exactly)
│   ├── domain.ts         ← Derived frontend types
│   └── index.ts
├── lib/
│   ├── api.ts            ← Axios instance + interceptors + typed helpers
│   └── utils.ts          ← formatCurrency, formatPct, formatDate, cn()
├── constants/
│   └── index.ts          ← Mirror of domain constants (HR_CAP, COLLATERAL_LIMIT, etc.)
├── contexts/
│   ├── AuthContext.tsx   ← User state, login/logout
│   └── ThemeContext.tsx  ← Dark/light mode
├── hooks/
│   ├── useLivePrices.ts      ← SSE → PriceTick[]
│   ├── useApprovals.ts       ← WebSocket → approval events
│   ├── useRecommendations.ts ← React Query: pending, latest, history
│   ├── useAnalytics.ts       ← React Query: forecast, VaR, hypothesis status
│   ├── usePositions.ts       ← React Query + SSE: open positions, collateral
│   └── usePermissions.ts     ← Returns Set<Permission> for current user
├── components/
│   ├── ui/               ← Atoms: Button, Badge, Input, Select, Card, Skeleton
│   ├── metrics/          ← Molecules: VaRGauge, HedgeRatioDial, CollateralMeter, MAPECard
│   ├── charts/           ← Recharts wrappers: ForecastChart, VaRCurveChart, WalkForwardChart
│   ├── tables/           ← TanStack Table: PositionsTable, AuditTable, ApprovalsTable
│   ├── agents/           ← AgentStatusCard, AgentConsensusPanel
│   └── layout/           ← AppShell, Sidebar, Header, ErrorBoundary, LoadingSpinner
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── Recommendation.tsx
│   ├── Analytics.tsx
│   ├── Positions.tsx
│   ├── AuditLog.tsx
│   └── Settings.tsx
└── App.tsx
```

---

## Key API Types

```typescript
// types/api.ts — create this before any component code
export type RiskLevel  = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
export type RecStatus  = 'PENDING' | 'APPROVED' | 'REJECTED' | 'DEFERRED' | 'EXPIRED' | 'CONSTRAINT_VIOLATED';
export type Decision   = 'APPROVE' | 'REJECT' | 'DEFER';
export type UserRole   = 'analyst' | 'risk_manager' | 'cfo' | 'admin';

export interface PriceTick {
  time: string;                 // ISO 8601 UTC
  jet_fuel_spot: number;
  heating_oil_futures: number;
  brent_futures: number;
  wti_futures: number;
  crack_spread: number;
  volatility_index: number;
  quality_flag: string | null;
}

export interface OptimizationResult {
  optimal_hr: number;           // 0.0 – 0.80
  instrument_mix: Record<'futures'|'options'|'collars'|'swaps', number>;
  proxy_weights: Record<'heating_oil'|'brent'|'wti', number>;
  solver_converged: boolean;
  collateral_usd: number;
  collateral_pct_of_reserves: number;
  constraint_violations: string[];
}

export interface RecommendationDetail {
  id: string;
  created_at: string;
  status: RecStatus;
  optimal_hr: number;
  instrument_mix: OptimizationResult['instrument_mix'];
  var_hedged: number;
  var_unhedged: number;
  var_reduction_pct: number;
  collateral_usd: number;
  agent_outputs: AgentOutput[];
  sequence_number: number;
  escalation_flag: boolean;
}

export interface HypothesisResult {
  id: 'H1' | 'H2' | 'H3' | 'H4';
  passed: boolean;
  metric_name: string;
  metric_value: number;
  threshold: string;
  last_tested: string;
}
```

---

## CURSOR PROMPT — Phase 6A: Frontend Foundation

```
Build the React frontend foundation before any page components.

1. src/types/api.ts — complete types matching backend Pydantic schemas exactly.
   Include all types shown above plus: ForecastResponse, VaRResult, BasisRiskMetric,
   AgentOutput, HedgePosition, CollateralSummary, ApprovalRecord, IFRS9Record,
   KpiRecord, ConstraintsConfig, UserResponse, PaginatedResponse<T>.
   Rule: monetary numbers in USD; percentages as decimal (0.0–1.0) unless field
   name ends in _pct (then 0.0–100.0).

2. src/lib/api.ts:
   - Axios instance: baseURL from import.meta.env.VITE_API_BASE_URL
   - withCredentials: true (sends httpOnly cookies automatically)
   - Request interceptor: add X-Request-ID header (uuid)
   - Response interceptor: on 401, attempt POST /api/v1/auth/refresh once,
     retry original request; on second 401, dispatch logout and redirect to /login
   - Typed helpers: apiGet<T>(path), apiPost<T>(path, body), apiPatch<T>(path, body)

3. src/hooks/useLivePrices.ts:
   - SSE connection to /api/v1/stream/prices
   - Returns PriceTick[] (last 500 ticks)
   - Auto-reconnect on disconnect: max 5 retries, exponential backoff (1s, 2s, 4s, 8s, 16s)
   - Expose: prices (PriceTick[]), connected (boolean), error (string | null)

4. src/hooks/useApprovals.ts:
   - WebSocket to /api/v1/stream/ws/approvals
   - On connect: send {type:'auth', token: accessToken} as first message
   - Handle {type:'ping'}: respond {type:'pong'}
   - On {type:'recommendation_update'}: invalidate React Query ['recommendations'] cache
   - Reconnect on close, max 5 retries

5. src/hooks/usePermissions.ts:
   - Reads user from AuthContext
   - Returns { hasPermission(p: Permission): boolean, role: UserRole }
   - Permission enum mirrors backend exactly

6. src/constants/index.ts:
   - HR_CAP = 0.80, HR_SOFT_WARN = 0.70, COLLATERAL_LIMIT = 0.15
   - Used in components for visual threshold indicators (e.g. CollateralMeter turns red above 0.12)
```

---

## CURSOR PROMPT — Phase 6B: All 6 Pages

```
Build all 6 pages using hooks and types from Phase 6A. Follow atomic design strictly.

Dashboard.tsx:
- LivePriceTicker: horizontal bar showing last 20 ticks, colour-coded by direction (green up, red down)
- 4 KPI cards top row: VaRGauge (radial/gauge chart), HedgeRatioDial (arc gauge, turns amber at 0.70),
  CollateralMeter (linear bar, turns red above 12%, hard limit line at 15%), MAPECard (number + trend)
  Each card: ErrorBoundary wrapper, Skeleton loading state, value, threshold indicator
- ForecastChart: Recharts ComposedChart — jet fuel actual (line) + 30-day forecast (dashed) + confidence bands (area)
- AgentStatusGrid: 5 cards, one per agent — last run time, RiskLevel badge, action_required flag (pulsing red dot)
- Data: useLivePrices (ticker) + useAnalytics (KPIs + forecast + agent status)

Recommendation.tsx:
- Prominently show latest PENDING recommendation (or "No pending recommendation" empty state)
- RecommendationCard: optimal HR as large number, instrument_mix as donut chart, proxy_weights as bar chart
- AgentConsensusPanel: 5 expandable agent cards showing recommendation text + metrics
- ApprovalButtons: ONLY render if usePermissions().hasPermission('approve:recommendation')
  Use React Query useMutation; optimistic update (show new status immediately before server confirms)
  SLA countdown: shows "X hours Y minutes until escalation" — updates every second with setInterval
- AuditTrailTimeline: shows approval/rejection history for this recommendation below the card

Analytics.tsx:
- H1–H4 cards in 2×2 grid: green border + "VALIDATED" badge if passed, red + "FAILED" if not
  Each shows: hypothesis name, metric name, current value, threshold string
- WalkForwardChart: Recharts LineChart — dynamic HR vs static HR VaR over rolling periods
- VaRCurveChart: shows VaR at 7 hedge ratios (0%, 20%, 40%, 60%, 70%, 80%, 100%)
  Add a vertical dashed line at 70% with label "Diminishing Returns (H1)"
- MAPETrendChart: 90-day rolling MAPE with horizontal dashed line at 8% target

Positions.tsx: open positions TanStack Table + collateral bar + proxy weights pie + expiry calendar.
AuditLog.tsx: paginated TanStack Table + IFRS9 compliance table + CSV export button.
Settings.tsx: React Hook Form + Zod for constraint editor. Validate HR cap input 0.50–0.80.
  Show inline warning "HR above 70% — diminishing returns per H1 hypothesis" if user sets > 0.70.
  Admin-only: user management table with activate/deactivate toggle.
```

---

# PHASE 7 — N8N AGENT MIGRATION

**Goal**: Migrate all 37 nodes from TSLA to fuel hedging domain. Each agent system prompt replaced with the fuel hedging persona.

---

## Migration Sequence

| Step | Nodes | Action | Validation |
|------|-------|--------|------------|
| 7.1 | 4 HTTP Request nodes | Replace URLs with EIA, CME, ICE APIs. Add API key from n8n credential store — never hardcoded. | Each returns JSON with timestamp within last 24h |
| 7.2 | Data aggregator (Code) | Merge 4 responses; compute `Crack_Spread = Jet_Fuel_Spot - Heating_Oil_Futures`; classify volatility regime. | Output contains all 7 dataset columns + regime flag |
| 7.3 | Market intelligence hub | HTTP GET to `/api/v1/analytics/forecast/latest` + `/basis-risk/latest`. Use `$env.FASTAPI_INTERNAL_URL`. | Returns formatted_analysis with VaR, MAPE, crack spread, proxy R² |
| 7.4 | All 5 Agent nodes | Replace system prompts entirely with fuel hedging personas from `.cursorrules`. Output must be valid JSON matching AgentOutput interface. | Each agent returns parseable JSON — test with JSON.parse() in a Code node |
| 7.5 | Investment Committee | Synthesize 5 agent outputs. Output: top_strategy, consensus_risk_level, key_concerns, recommended_hr, rationale. | consensus_risk_level is valid RiskLevel enum value |
| 7.6 | Risk Management (CRO) | Final gate: check HR <= HR_HARD_CAP, collateral <= COLLATERAL_LIMIT, IFRS9 eligibility. If any breach: output status='BLOCKED'. | Correctly blocks test payload with HR=0.85 |
| 7.7 | Post-committee Code node | HTTP POST to `/api/v1/recommendations` with `X-N8N-API-Key` header. | FastAPI creates PENDING rec; visible on React dashboard |
| 7.8 | Telegram nodes | Remove entirely. Replace with HTTP GET poll to `/api/v1/recommendations/{id}` checking status every 60s via Wait + IF loop. | n8n detects APPROVED and terminates loop |
| 7.9 | Wait 1–4 nodes | Reconfigure: wait 4h for approval. If still PENDING: HTTP PATCH to escalation endpoint. | Escalation flag visible on React dashboard |

---

## CURSOR PROMPT — Phase 7: N8N Migration

```
Migrate n8n/workflows/fuel_hedge_advisor_v1.json to fuel_hedge_advisor_v2.json.
Keep v1.json as backup — do not modify it.

For Code nodes calling FastAPI:
- Use $env.FASTAPI_INTERNAL_URL (Render internal network URL — not public URL)
  This avoids external network round-trip and reduces latency by ~200ms
- All HTTP calls use try/catch — on non-200 response: set workflow variable
  pipeline_error=true and route to error handler node (not continue)

For all 5 Agent system prompts, replace with this pattern:
"You are the [AGENT_NAME] for a commercial airline fuel hedging desk.
[Domain-specific instructions from .cursorrules agent personas]
You MUST respond with ONLY valid JSON. No markdown. No explanation.
Schema: {agent_id, risk_level, recommendation, metrics,
         constraints_satisfied, action_required, ifrs9_eligible, generated_at}"

Add a workflow-level error handler node that:
- Catches any node failure anywhere in the workflow
- POSTs to FastAPI /api/v1/admin/pipeline-alert with: {workflow_id, failed_node, error_message, timestamp}
- Ensures analytics_runs record is updated to status='FAILED'
- This prevents silent failures in the overnight pipeline
```

---

# PHASE 8 — CI/CD & DEPLOYMENT

**Goal**: Complete GitHub Actions automation. Push to main → tests → build → deploy. No manual steps.

---

## GitHub Actions Workflows

| Workflow | Trigger | Jobs | SLA |
|----------|---------|------|-----|
| `ci.yml` | Every PR to main/staging | backend-tests → analytics-smoke-test → frontend-build → **security-scan** | < 5 min |
| `deploy-frontend.yml` | Push to main (`frontend/**`) | build → configure-pages → upload-artifact → deploy-pages | < 3 min |
| `deploy-backend.yml` | Push to main (`python_engine/**` or `models/**`) | wait-for-ci → migrate → deploy-api → healthcheck-poll → deploy-n8n | < 6 min |
| `lstm-retrain.yml` | Cron: Sunday 02:00 UTC | checkout → install → update-dataset → train → validate-mape (<12%) → commit-artifacts | < 20 min |
| `nightly-validation.yml` | Cron: Mon–Fri 23:00 UTC | fetch-kpis → validate-thresholds → post-to-slack → **fail-on-breach** | < 3 min |

---

## Render Services

| Service | Type | Plan | Cost |
|---------|------|------|------|
| `hedge-api` (FastAPI) | Web Service | Starter | $7/mo |
| `hedge-postgres` | Managed DB | Starter | $7/mo |
| `hedge-n8n` | Background Worker | Starter | $7/mo |
| `hedge-redis` | Redis | Free (25MB) | $0 |
| Frontend | GitHub Pages | Static | $0 |

**Total: ~$21/month prototype cost**

---

## Required GitHub Secrets

| Secret | Value | Used By |
|--------|-------|---------|
| `RENDER_DEPLOY_HOOK_API` | Render API service deploy hook URL | `deploy-backend.yml` |
| `RENDER_DEPLOY_HOOK_N8N` | Render n8n service deploy hook URL | `deploy-backend.yml` |
| `RENDER_DATABASE_URL` | Render PostgreSQL connection string | `deploy-backend.yml` (migrations) |
| `VITE_API_BASE_URL` | `https://hedge-api.onrender.com` | `deploy-frontend.yml` |
| `VITE_WS_URL` | `wss://hedge-api.onrender.com` | `deploy-frontend.yml` |
| `EIA_API_KEY` | EIA API key | `lstm-retrain.yml` |
| `CME_API_KEY` | CME API key | `nightly-validation.yml` |
| `OPENAI_API_KEY` | OpenAI API key | `nightly-validation.yml` |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook | `nightly-validation.yml`, `lstm-retrain.yml` |
| `GH_PAT` | GitHub PAT (repo + workflow scope) | `lstm-retrain.yml` (to push model commits) |

---

## CURSOR PROMPT — Phase 8: CI/CD & Deployment

```
Create all 5 GitHub Actions workflow files per the table above with these additions:

1. ci.yml — add security-scan job after frontend-build:
   - Run: pip-audit --requirement python_engine/requirements.txt --output json
   - Run: cd frontend && npm audit --audit-level=high --json
   - Parse outputs: if any HIGH or CRITICAL vulnerability found, fail workflow
   - This is non-negotiable — supply chain vulnerabilities must block deployment

2. deploy-backend.yml — add migration safety check before alembic upgrade:
   - Run: alembic check
   - If this reports schema drift: fail the deployment with clear error message
   - Only proceed to alembic upgrade head if check passes

3. render.yaml using service definitions from the table above:
   - All envVars use sync: false for secrets (set manually in Render dashboard)
   - Use fromDatabase: {name: hedge-postgres, property: connectionString} for DATABASE_URL
   - hedge-api healthCheckPath: /api/v1/health
   - n8n: add disk mount at /home/node/.n8n, sizeGB: 1

4. .github/CODEOWNERS:
   python_engine/app/constants.py    @your-github-username
   python_engine/app/analytics/      @your-github-username
   .cursorrules                       @your-github-username
   Require review from these owners on any PR touching these files.

5. docs/RUNBOOK.md with procedures:
   - Add a new user
   - Rollback a model artifact
   - Update constraint limits
   - Handle nightly-validation.yml breach alert
   - Manually trigger the daily pipeline
   - What to do if Render health check fails
```

---

# PRE-COMMIT SECURITY CHECKLIST

> Complete this before your first `git push`.

- [ ] `.env` file in `.gitignore` — verify: `git check-ignore -v .env`
- [ ] No API keys, passwords, or tokens in any code file
- [ ] `detect-secrets` pre-commit hook installed: `pre-commit install`
- [ ] Baseline scan run: `detect-secrets scan > .secrets.baseline`
- [ ] All 10 GitHub Secrets added to repo Settings → Secrets and variables → Actions
- [ ] `CODEOWNERS` file created with your GitHub username
- [ ] Render environment variables set manually in dashboard (`sync: false` in render.yaml)
- [ ] `JWT_SECRET_KEY` generated: `openssl rand -hex 32` — never reuse across environments
- [ ] `N8N_WEBHOOK_SECRET` generated: `openssl rand -hex 32` — different from JWT secret

---

# TESTING REFERENCE

| Phase | Command | Minimum to Pass Before Next Phase |
|-------|---------|-----------------------------------|
| After Phase 1 | `pytest tests/test_db/ -v` | All repo CRUD tests pass; migrations apply cleanly |
| After Phase 2 | `pytest tests/test_analytics/ -v` | MAPE < 15% on smoke test; optimizer converges; VaR curve monotone |
| After Phase 3 | `pytest tests/test_auth/ -v` | Login returns httpOnly cookie; protected route returns 403 without token |
| After Phase 4 | `pytest tests/test_ingestion/ -v` | Mock API clients return PriceTick; quality checker flags 3σ outlier |
| After Phase 5 | `pytest tests/ -v --cov --cov-fail-under=70` | 70% coverage; approval workflow e2e passes |
| After Phase 6 | `npm test -- --run` | ApprovalButtons renders only for correct role; SSE hook reconnects |
| After Phase 7 | Manual n8n test | All 5 agents return valid JSON; FastAPI creates PENDING recommendation |
| After Phase 8 | Push to main; watch Actions tab | All 5 workflows green; GitHub Pages URL live; Render health check passes |

---

*Document: Cursor AI Implementation Master Plan v1.0 — March 2026*  
*Total files this plan creates: ~120 Python files · ~80 TypeScript/TSX files · 5 GitHub Actions workflows · 2 Docker Compose files · 1 render.yaml · 2 n8n workflow JSONs*  
*Synthesised from: Phase 1–2 Report, Phase 3 Methodology Report, Tech Specs v1.0–v3.0*
