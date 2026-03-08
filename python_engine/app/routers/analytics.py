"""Analytics runs API endpoints.

Provides access to analytics pipeline execution history and manual triggering.

DIAGNOSIS: Run Pipeline button failures.
- Endpoint must return 202 immediately; pipeline runs in background.
- Check for RUNNING pipeline before starting; return 409 if already running.
- Frontend calls POST /analytics/trigger (not /analytics/run).
"""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import get_settings
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.dependencies import AdminUser, AnalystUser, AnalyticsOrN8nAuth, CurrentUser, DatabaseSession, require_permission
from app.db.models import AnalyticsRun, AnalyticsRunStatus, BacktestRun, HedgeRecommendation
from app.repositories import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsRunDetail,
    AnalyticsRunQueryParams,
    AnalyticsRunResponse,
    AnalyticsSummary,
    DashboardSummaryResponse,
    LoadCsvResponse,
    TriggerAnalyticsRequest,
    TriggerPipelineResponse,
)
from app.schemas.common import PaginatedResponse
from app.analytics.scenarios import SCENARIOS, SCENARIOS_BY_ID
from app.repositories import ConfigRepository
from app.services.analytics_pipeline import AnalyticsPipeline
from app.services.data_ingestion import import_historical_csv
from app.services.price_service import get_price_service
from app.services.scenario_service import ScenarioService
from app.analytics.optimizer import build_optimizer_constraints

router = APIRouter()

# Singleton scenario service
_scenario_service: ScenarioService | None = None


def get_scenario_service() -> ScenarioService:
    """Get or create the ScenarioService singleton."""
    global _scenario_service
    if _scenario_service is None:
        _scenario_service = ScenarioService()
    return _scenario_service
logger = structlog.get_logger()


@router.get("", response_model=PaginatedResponse[AnalyticsRunResponse])
async def list_analytics_runs(
    current_user: AnalystUser,
    db: DatabaseSession,
    status_filter: Optional[AnalyticsRunStatus] = Query(None, alias="status"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> PaginatedResponse[AnalyticsRunResponse]:
    """List analytics runs with filtering and pagination.

    Requires ANALYST role or higher.
    """
    # Build query
    query = select(AnalyticsRun)

    # Apply filters
    filters = []
    if status_filter:
        filters.append(AnalyticsRun.status == status_filter)
    if start_date:
        filters.append(AnalyticsRun.run_date >= start_date)
    if end_date:
        filters.append(AnalyticsRun.run_date <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # Count total
    count_query = select(func.count(AnalyticsRun.id)).where(and_(*filters)) if filters else select(func.count(AnalyticsRun.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(desc(AnalyticsRun.run_date)).offset(offset).limit(limit)

    # Execute
    result = await db.execute(query)
    runs = result.scalars().all()

    # Calculate pages
    pages = (total + limit - 1) // limit

    logger.info(
        "analytics_runs_listed",
        user_id=str(current_user.id),
        count=len(runs),
        total=total,
    )

    def _run_to_response(r: AnalyticsRun) -> AnalyticsRunResponse:
        return AnalyticsRunResponse(
            id=r.id,
            run_date=r.run_date,
            status=r.status,
            forecast_mape=r.mape,
            var_95_usd=(r.var_results or {}).get("var_usd"),
            basis_r2=(r.basis_metrics or {}).get("r2_heating_oil"),
            optimal_hr=(r.optimizer_result or {}).get("optimal_hr"),
            pipeline_start_time=None,
            pipeline_end_time=None,
            error_message=(r.forecast_json or {}).get("error") if r.status == AnalyticsRunStatus.FAILED else None,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )

    return PaginatedResponse(
        items=[_run_to_response(r) for r in runs],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: AnalystUser,
    db: DatabaseSession,
) -> DashboardSummaryResponse:
    """Get dashboard KPI summary from latest COMPLETED analytics run.

    Requires ANALYST role or higher.
    Returns zeros if no completed run exists yet.
    """
    repo = AnalyticsRepository(db)
    run = await repo.get_latest_completed()
    if run is None:
        return DashboardSummaryResponse(
            current_var_usd=0.0,
            current_hedge_ratio=0.0,
            collateral_pct=0.0,
            mape_pct=0.0,
            var_reduction_pct=0.0,
            ifrs9_compliance_status="no_data",
            last_updated="",
            agent_outputs=[],
        )
    var_data = run.var_results or {}
    opt_data = run.optimizer_result or {}
    var_usd = float(var_data.get("var_usd", 0) or 0)
    optimal_hr = float(opt_data.get("optimal_hr", 0) or 0)
    collateral = float(opt_data.get("collateral_pct_of_reserves", 0) or opt_data.get("collateral_pct", 0) or 0)
    var_reduction = float(opt_data.get("var_reduction_pct", 0) or 0)
    mape = float(run.mape or 0)
    basis_metrics = run.basis_metrics or {}
    ifrs9 = "compliant" if basis_metrics.get("ifrs9_eligible", False) else "non_compliant"
    last_updated = run.updated_at.isoformat() if run.updated_at else run.created_at.isoformat()
    r2_ho = float(basis_metrics.get("r2_heating_oil", 0.85) or 0.85)

    # Total notional from open positions
    from app.repositories import PositionRepository
    pos_repo = PositionRepository(db)
    total_notional = await pos_repo.get_total_open_notional()

    # Fetch agent outputs from latest recommendation for this run (from n8n)
    agent_outputs: list[dict] = []
    rec_result = await db.execute(
        select(HedgeRecommendation)
        .where(HedgeRecommendation.run_id == run.id)
        .order_by(desc(HedgeRecommendation.sequence_number))
    )
    for rec in rec_result.scalars().all():
        if rec.agent_outputs:
            agents = rec.agent_outputs.get("agents") if isinstance(rec.agent_outputs, dict) else rec.agent_outputs
            if isinstance(agents, list) and len(agents) > 0:
                agent_outputs = [a if isinstance(a, dict) else {} for a in agents]
                break

    return DashboardSummaryResponse(
        current_var_usd=var_usd,
        current_hedge_ratio=optimal_hr,
        collateral_pct=collateral,
        mape_pct=mape,
        var_reduction_pct=var_reduction,
        ifrs9_compliance_status=ifrs9,
        last_updated=last_updated,
        agent_outputs=agent_outputs,
        r2_heating_oil=r2_ho,
        total_notional_usd=float(total_notional) if total_notional else None,
    )


@router.get("/mape-history")
async def get_mape_history(
    current_user: AnalystUser,
    db: DatabaseSession,
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Returns MAPE history for the last N days. Frontend expects data_points + summary."""
    repo = AnalyticsRepository(db)
    runs = await repo.get_completed_since(days=days)
    data_points = [
        {"date": str(r.run_date), "mape": float(r.mape)}
        for r in runs
        if r.mape is not None
    ]
    # Compute summary
    mapes = [d["mape"] for d in data_points]
    avg_mape = sum(mapes) / len(mapes) if mapes else 0.0
    min_mape = min(mapes) if mapes else 0.0
    max_mape = max(mapes) if mapes else 0.0
    target = 8.0
    alert = 10.0
    within_target = sum(1 for m in mapes if m < target) if mapes else 0
    violations = sum(1 for m in mapes if m >= alert) if mapes else 0
    within_target_pct = (within_target / len(mapes) * 100) if mapes else 0.0
    return {
        "data_points": data_points,
        "target_threshold": target,
        "alert_threshold": alert,
        "summary": {
            "avg_mape": round(avg_mape, 2),
            "min_mape": round(min_mape, 2),
            "max_mape": round(max_mape, 2),
            "within_target_pct": round(within_target_pct, 1),
            "violations": violations,
        },
    }


@router.get("/var-walk-forward")
async def get_var_walk_forward(
    current_user: AnalystUser,
    db: DatabaseSession,
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Returns walk-forward VaR comparison data. Frontend expects data_points + summary."""
    repo = AnalyticsRepository(db)
    runs = await repo.get_completed_since(days=days)
    data_points = []
    for r in runs:
        var_data = r.var_results or {}
        opt_data = r.optimizer_result or {}
        dynamic_var = var_data.get("var_usd")
        var_reduction_pct = float(opt_data.get("var_reduction_pct", 0) or 0)
        # Derive static (unhedged) VaR from dynamic_var and reduction %
        if dynamic_var is not None:
            dynamic_var = float(dynamic_var)
            static_var = (
                dynamic_var / (1 - var_reduction_pct / 100)
                if var_reduction_pct < 100
                else dynamic_var
            )
            data_points.append({
                "date": str(r.run_date),
                "dynamic_var": round(dynamic_var, 2),
                "static_var": round(static_var, 2),
                "improvement_pct": round(var_reduction_pct, 2),
                "retrained": False,
            })
    # Compute summary
    dynamic_vars = [d["dynamic_var"] for d in data_points]
    static_vars = [d["static_var"] for d in data_points]
    avg_dynamic = sum(dynamic_vars) / len(dynamic_vars) if dynamic_vars else 0.0
    avg_static = sum(static_vars) / len(static_vars) if static_vars else 0.0
    improvement = (
        ((avg_static - avg_dynamic) / avg_static * 100) if avg_static > 0 else 0.0
    )
    return {
        "data_points": data_points,
        "summary": {
            "avg_dynamic_var": round(avg_dynamic, 2),
            "avg_static_var": round(avg_static, 2),
            "improvement_pct": round(improvement, 2),
        },
    }


def _build_forecast_data_points(run) -> list[dict]:
    """Build data_points array for frontend charts from analytics run."""
    fc = run.forecast_json or {}
    values = fc.get("forecast_values") or []
    if not values:
        return []
    from datetime import timedelta
    base_date = run.run_date
    data_points = []
    for i, fv in enumerate(values):
        d = base_date + timedelta(days=i)
        # Add ±5% as placeholder confidence band
        f = float(fv)
        data_points.append({
            "date": str(d),
            "actual": None,
            "forecast": f,
            "lower_bound": f * 0.95,
            "upper_bound": f * 1.05,
        })
    return data_points


@router.get("/forecast/latest")
async def get_latest_forecast(
    _auth: AnalyticsOrN8nAuth,
    db: DatabaseSession,
) -> dict:
    """Returns the latest forecast from the most recent completed analytics run.
    Accepts JWT or X-N8N-API-Key (for n8n workflow). Returns null if no runs exist."""
    repo = AnalyticsRepository(db)
    run = await repo.get_latest_completed()
    if run is None:
        return {"forecast": None, "message": "No analytics runs completed yet", "data_points": []}
    fc = run.forecast_json or {}
    latest_price = fc.get("latest_price") or fc.get("mean")
    values = fc.get("forecast_values") or []
    if values:
        latest_price = float(values[-1]) if values else 94.5
    return {
        "forecast": fc,
        "latest_price": float(latest_price) if latest_price is not None else 94.5,
        "volatility_regime": fc.get("volatility_regime", "MODERATE"),
        "mape": float(run.mape),
        "trend_direction": fc.get("trend_direction", "FLAT"),
        "pct_change_30d": fc.get("pct_change_30d", 0.0),
        "run_id": str(run.id),
        "run_date": str(run.run_date),
        "data_points": _build_forecast_data_points(run),
    }


@router.get("/var/latest")
async def get_latest_var(
    _auth: AnalyticsOrN8nAuth,
    db: DatabaseSession,
) -> dict:
    """Returns VaR results from the most recent completed run. For n8n workflow."""
    repo = AnalyticsRepository(db)
    run = await repo.get_latest_completed()
    if run is None:
        return {"var_usd": 0.0, "var_unhedged_usd": 0.0, "var_reduction_pct": 0.0}
    var = run.var_results or {}
    return {
        "var_usd": float(var.get("var_usd", 0) or 0),
        "var_unhedged_usd": float(var.get("var_unhedged_usd", 0) or 0),
        "var_reduction_pct": float(var.get("var_reduction_pct", 0) or 0),
        "run_id": str(run.id),
        "run_date": str(run.run_date),
    }


@router.get("/basis-risk/latest")
async def get_latest_basis_risk(
    _auth: AnalyticsOrN8nAuth,
    db: DatabaseSession,
) -> dict:
    """Returns basis risk metrics from the most recent completed run. For n8n workflow."""
    repo = AnalyticsRepository(db)
    run = await repo.get_latest_completed()
    if run is None:
        return {
            "heating_oil_latest": 88.2,
            "crack_spread_current": 6.3,
            "r2_heating_oil": 0.87,
            "r2_brent": 0.75,
            "crack_spread_zscore": 0.5,
        }
    basis = run.basis_metrics or {}
    return {
        "heating_oil_latest": float(basis.get("heating_oil_latest", 88.2) or 88.2),
        "crack_spread_current": float(basis.get("crack_spread_current", 6.3) or 6.3),
        "r2_heating_oil": float(basis.get("r2_heating_oil", 0.87) or 0.87),
        "r2_brent": float(basis.get("r2_brent", 0.75) or 0.75),
        "crack_spread_zscore": float(basis.get("crack_spread_zscore", 0.5) or 0.5),
        "run_id": str(run.id),
        "run_date": str(run.run_date),
    }


@router.get("/optimizer/latest")
async def get_latest_optimizer(
    _auth: AnalyticsOrN8nAuth,
    db: DatabaseSession,
) -> dict:
    """Returns optimizer result from the most recent completed run. For n8n workflow."""
    repo = AnalyticsRepository(db)
    run = await repo.get_latest_completed()
    if run is None:
        return {
            "optimal_hr": 0.70,
            "instrument_mix": {"futures": 0.7, "options": 0.2, "collars": 0.1, "swaps": 0.0},
            "proxy_weights": {"heating_oil": 0.75, "brent": 0.15, "wti": 0.10},
            "collateral_usd": 850000,
            "collateral_pct_of_reserves": 12.5,
            "solver_converged": True,
        }
    opt = run.optimizer_result or {}
    return {
        "optimal_hr": float(opt.get("optimal_hr", 0.70) or 0.70),
        "instrument_mix": opt.get("instrument_mix") or {"futures": 0.7, "options": 0.2, "collars": 0.1, "swaps": 0.0},
        "proxy_weights": opt.get("proxy_weights") or {"heating_oil": 0.75, "brent": 0.15, "wti": 0.10},
        "collateral_usd": float(opt.get("collateral_usd", 850000) or 850000),
        "collateral_pct_of_reserves": float(opt.get("collateral_pct_of_reserves", 12.5) or opt.get("collateral_pct", 12.5) or 12.5),
        "solver_converged": opt.get("solver_converged", True) is not False,
        "run_id": str(run.id),
        "run_date": str(run.run_date),
    }


@router.post("/load-csv", response_model=LoadCsvResponse)
async def load_historical_csv(
    current_user: AnalystUser,
    db: DatabaseSession,
) -> LoadCsvResponse:
    """Load historical fuel hedging dataset from CSV into the database.

    Requires ANALYST role or higher.
    Uses data/fuel_hedging_dataset.csv (mounted at /app/data in Docker).
    """
    stats = await import_historical_csv(db)
    await db.commit()

    logger.info(
        "csv_loaded_via_api",
        user_id=str(current_user.id),
        imported=stats["imported"],
        updated=stats["updated"],
        skipped=stats["skipped"],
    )

    return LoadCsvResponse(
        imported=stats["imported"],
        updated=stats["updated"],
        skipped=stats["skipped"],
        total=stats["total"],
    )


@router.post("/seed-backtest")
async def seed_backtest_data(
    current_user: AdminUser,
) -> dict:
    """Seed analytics runs and backtest data (for Backtesting tab). Admin only.

    Idempotent: skips dates that already have data. Takes ~30 seconds.
    """
    from scripts.seed_analytics_history import main as seed_main

    logger.info("seed_backtest_triggered", user_id=str(current_user.id))
    await seed_main()
    return {"message": "Backtest data seeded successfully. Refresh the Backtesting tab."}


@router.get("/latest/status", response_model=Optional[AnalyticsRunResponse])
async def get_latest_run_status(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> Optional[AnalyticsRunResponse]:
    """Get the most recent analytics run status. Accessible to all authenticated users."""
    result = await db.execute(
        select(AnalyticsRun).order_by(desc(AnalyticsRun.run_date)).limit(1)
    )
    latest_run = result.scalar_one_or_none()
    if not latest_run:
        return None
    # Map to AnalyticsRunResponse schema
    return AnalyticsRunResponse(
        id=latest_run.id,
        run_date=latest_run.run_date,
        status=latest_run.status,
        forecast_mape=latest_run.mape,
        var_95_usd=(latest_run.var_results or {}).get("var_usd"),
        basis_r2=(latest_run.basis_metrics or {}).get("r2_heating_oil"),
        optimal_hr=(latest_run.optimizer_result or {}).get("optimal_hr"),
        pipeline_start_time=None,
        pipeline_end_time=None,
        error_message=(latest_run.forecast_json or {}).get("error") if latest_run.status == AnalyticsRunStatus.FAILED else None,
        created_at=latest_run.created_at,
        updated_at=latest_run.updated_at,
    )


@router.get("/scenarios")
async def list_scenarios(
    current_user=Depends(require_permission("view:analytics")),
) -> list[dict]:
    """Returns all available stress test scenarios."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "price_shock_pct": s.price_shock_pct,
            "vol_multiplier": s.vol_multiplier,
            "duration_days": s.duration_days,
            "historical_reference": s.historical_reference,
            "color": s.color,
        }
        for s in SCENARIOS
    ]


@router.post("/scenarios/{scenario_id}/run")
async def run_stress_scenario(
    scenario_id: str,
    db: DatabaseSession,
    current_user=Depends(require_permission("view:analytics")),
) -> dict:
    """
    Run a stress scenario simulation against current market conditions.
    view:analytics permission required (analyst, risk_manager, cfo, admin).
    Does NOT write to DB. Returns simulation results only.
    Responds in < 3 seconds — synchronous optimizer run.
    """
    scenario = SCENARIOS_BY_ID.get(scenario_id)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": f"Scenario '{scenario_id}' not found",
                "available": list(SCENARIOS_BY_ID.keys()),
            },
        )

    # Get current price from live tick or fallback
    last_tick = get_price_service().get_last_tick()
    current_price = last_tick.jet_fuel_spot if last_tick else 84.96

    # Load dataset for optimizer
    from pathlib import Path
    import pandas as pd

    # Resolve path: app/routers -> app -> python_engine; data is at python_engine/data (Docker: /app/data)
    base = Path(__file__).resolve().parent.parent.parent
    csv_path = base / "data" / "fuel_hedging_dataset.csv"
    if not csv_path.exists():
        csv_path = Path("data/fuel_hedging_dataset.csv")
    df = pd.read_csv(csv_path, parse_dates=["Date"])

    # Get current constraints from DB
    config_repo = ConfigRepository(db)
    config_snapshot = await config_repo.get_constraints_snapshot()
    constraints = build_optimizer_constraints(
        config_snapshot,
        cash_reserves=50_000_000,
        forecast_consumption_bbl=100_000,
    )

    scenario_service = get_scenario_service()
    result = scenario_service.run_scenario(scenario, current_price, df, constraints)
    return result


@router.get("/{run_id}", response_model=AnalyticsRunDetail)
async def get_analytics_run(
    run_id: UUID,
    current_user: AnalystUser,
    db: DatabaseSession,
) -> AnalyticsRunDetail:
    """Get detailed analytics run information.

    Requires ANALYST role or higher.
    """
    repo = AnalyticsRepository(db)
    run = await repo.get_by_id(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": "Analytics run not found"},
        )

    # Duration from model field (no pipeline_start_time/end_time columns)
    duration_seconds = float(run.duration_seconds) if run.duration_seconds else None

    # Count recommendations
    rec_result = await db.execute(
        select(func.count(HedgeRecommendation.id)).where(
            HedgeRecommendation.run_id == run_id
        )
    )
    recommendations_count = rec_result.scalar_one()

    # Build response — map model fields to schema (AnalyticsRunResponse expects some aliases)
    response_data = {
        "id": run.id,
        "run_date": run.run_date,
        "status": run.status,
        "forecast_mape": run.mape,
        "var_95_usd": (run.var_results or {}).get("var_usd"),
        "basis_r2": (run.basis_metrics or {}).get("r2_heating_oil"),
        "optimal_hr": (run.optimizer_result or {}).get("optimal_hr"),
        "pipeline_start_time": None,
        "pipeline_end_time": None,
        "error_message": (run.forecast_json or {}).get("error") if run.status == AnalyticsRunStatus.FAILED else None,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }
    response_data.update({
        "duration_seconds": duration_seconds,
        "recommendations_count": recommendations_count,
    })

    logger.info(
        "analytics_run_retrieved",
        user_id=str(current_user.id),
        run_id=str(run_id),
    )

    return AnalyticsRunDetail(**response_data)


def _trigger_n8n_immediate(run_id: str, triggered_by: str) -> None:
    """Trigger n8n workflow immediately (fire-and-forget). Runs when user clicks Run Pipeline."""
    async def _do_trigger() -> None:
        try:
            settings = get_settings()
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.N8N_INTERNAL_URL}{settings.N8N_TRIGGER_PATH}",
                    json={
                        "run_id": run_id,
                        "analytics_summary": {"triggered_by": triggered_by},
                        "trigger_type": "manual_from_dashboard",
                        "triggered_at": datetime.now(timezone.utc).isoformat(),
                    },
                    headers={"X-N8N-API-Key": settings.N8N_WEBHOOK_SECRET},
                )
                resp.raise_for_status()
                logger.info("n8n_triggered_immediate", run_id=run_id, status=resp.status_code)
        except Exception as e:
            logger.warning("n8n_immediate_trigger_failed", run_id=run_id, error=str(e))

    asyncio.create_task(_do_trigger())


async def _run_pipeline_background(notional_usd: Decimal) -> None:
    """Run pipeline in background with fresh DB session."""
    async with AsyncSessionLocal() as session:
        try:
            pipeline = AnalyticsPipeline(session, notional_usd=notional_usd)
            await pipeline.execute_daily_run()
        except Exception as e:
            logger.error("pipeline_background_failed", error=str(e))


@router.post("/test-n8n-trigger", include_in_schema=False)
async def test_n8n_trigger_dev(
    current_user=Depends(require_permission("trigger:pipeline")),
    settings=Depends(get_settings),
) -> dict:
    """
    Dev-only: sends a minimal test payload to n8n webhook without running
    the full analytics pipeline. Used to verify n8n workflow is working.
    Only available when ENVIRONMENT=development.
    """
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=404, detail="Not found")
    import uuid
    test_payload = {
        "run_id": str(uuid.uuid4()),
        "trigger_type": "test",
        "analytics_summary": {"var_usd": 2100000, "mape": 4.4, "optimal_hr": 0.68},
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.N8N_INTERNAL_URL}{settings.N8N_TRIGGER_PATH}",
                json=test_payload,
                headers={"X-N8N-API-Key": settings.N8N_WEBHOOK_SECRET},
            )
        return {"n8n_status": resp.status_code, "payload_sent": test_payload}
    except httpx.ConnectError:
        return {"error": "n8n not reachable", "hint": "Is n8n running? Is workflow activated?"}


@router.post("/trigger", response_model=TriggerPipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_analytics_run(
    trigger_data: TriggerAnalyticsRequest,
    current_user: AdminUser,
    db: DatabaseSession,
) -> TriggerPipelineResponse:
    """Manually trigger analytics pipeline execution.

    Requires ADMIN role.
    Returns 202 Accepted immediately — pipeline runs in background (~8 min).
    Returns 409 Conflict if pipeline is already running.
    """
    repo = AnalyticsRepository(db)
    running = await repo.get_running_pipeline()
    if running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "Pipeline is already running",
                "error_code": "pipeline_already_running",
                "started_at": str(running.created_at),
            },
        )

    notional = trigger_data.notional_usd if trigger_data.notional_usd else Decimal("10000000")
    asyncio.create_task(_run_pipeline_background(notional))

    # n8n is triggered by the pipeline when it completes (~8 min) — not immediately.
    # Immediate trigger would fetch empty data since analytics run does not exist yet.

    logger.info(
        "analytics_triggered_manually",
        user_id=str(current_user.id),
        notional=float(notional),
    )

    return TriggerPipelineResponse(
        status="accepted",
        message="Pipeline started. Analytics results will be available in approximately 8 minutes.",
        run_id="",  # Run ID not known until pipeline creates record
        triggered_at=datetime.now(timezone.utc).isoformat(),
        triggered_by=current_user.email,
    )


@router.get("/summary/statistics", response_model=AnalyticsSummary)
async def get_analytics_summary(
    current_user: AnalystUser,
    db: DatabaseSession,
    days: int = Query(30, ge=1, le=365, description="Number of days for summary"),
) -> AnalyticsSummary:
    """Get analytics pipeline summary statistics.

    Requires ANALYST role or higher.
    """
    from datetime import datetime, timedelta

    cutoff_date = datetime.utcnow().date() - timedelta(days=days)

    # Total runs
    total_result = await db.execute(
        select(func.count(AnalyticsRun.id)).where(
            AnalyticsRun.run_date >= cutoff_date
        )
    )
    total_runs = total_result.scalar_one()

    # Successful runs
    success_result = await db.execute(
        select(func.count(AnalyticsRun.id)).where(
            and_(
                AnalyticsRun.run_date >= cutoff_date,
                AnalyticsRun.status == AnalyticsRunStatus.COMPLETED,
            )
        )
    )
    successful_runs = success_result.scalar_one()

    # Failed runs
    failed_runs = total_runs - successful_runs

    # Average MAPE (successful runs only) — use mape column
    mape_result = await db.execute(
        select(func.avg(AnalyticsRun.mape)).where(
            and_(
                AnalyticsRun.run_date >= cutoff_date,
                AnalyticsRun.status == AnalyticsRunStatus.COMPLETED,
                AnalyticsRun.mape.isnot(None),
            )
        )
    )
    average_mape = mape_result.scalar_one()

    # Average duration — use duration_seconds column
    duration_result = await db.execute(
        select(func.avg(AnalyticsRun.duration_seconds)).where(
            and_(
                AnalyticsRun.run_date >= cutoff_date,
                AnalyticsRun.status == AnalyticsRunStatus.COMPLETED,
                AnalyticsRun.duration_seconds.isnot(None),
            )
        )
    )
    average_duration_seconds = float(duration_result.scalar_one()) if duration_result.scalar_one() else None

    logger.info(
        "analytics_summary_retrieved",
        user_id=str(current_user.id),
        days=days,
        total_runs=total_runs,
    )

    return AnalyticsSummary(
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        average_mape=Decimal(str(average_mape)) if average_mape else None,
        average_var_reduction=None,  # TODO: Calculate from recommendations
        average_duration_seconds=average_duration_seconds,
    )


@router.get("/backtest/latest")
async def get_backtest_latest(
    current_user: AnalystUser,
    db: DatabaseSession,
) -> dict:
    """Get latest backtest run results for charting.

    Returns summary + weekly_results for the Backtesting tab.
    """
    result = await db.execute(
        select(BacktestRun)
        .order_by(desc(BacktestRun.computed_at))
        .limit(1)
    )
    run = result.scalar_one_or_none()
    if run is None:
        return {
            "summary": None,
            "weekly_results": [],
            "computed_at": None,
            "notional_usd": None,
        }
    return {
        "summary": run.summary,
        "weekly_results": run.weekly_results,
        "computed_at": run.computed_at.isoformat() if run.computed_at else None,
        "notional_usd": float(run.notional_usd),
    }


