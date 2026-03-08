"""Analytics pipeline orchestration.

Coordinates daily analytics execution:
1. Fetch latest market data
2. Run forecasting models
3. Calculate VaR and basis risk
4. Generate hedge recommendations
5. Store results in database
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import httpx
import pandas as pd
import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import (
    BasisRiskAnalyzer,
    EnsembleForecaster,
    HedgeOptimizer,
    HistoricalSimVaR,
    StressTestEngine,
)
from app.analytics.domain import BasisRiskMetric, ForecastResult, OptimizationResult, VaRResult
from app.analytics.optimizer import build_optimizer_constraints
from app.constants import (
    IFRS9_R2_MIN_PROSPECTIVE,
    MAPE_ALERT,
    MAPE_TARGET,
    VAR_REDUCTION_TARGET,
)
from app.db.models import (
    AnalyticsRun,
    AnalyticsRunStatus,
    Approval,
    HedgePosition,
    HedgeRecommendation,
    PriceTick,
    RecommendationStatus,
)
from app.config import get_settings
from app.exceptions import ModelError
from app.repositories import AnalyticsRepository, ConfigRepository, MarketDataRepository

logger = structlog.get_logger()


class AnalyticsPipeline:
    """Daily analytics pipeline execution."""

    def __init__(
        self,
        db: AsyncSession,
        notional_usd: Decimal = Decimal("10000000"),  # $10M default
    ) -> None:
        """Initialize analytics pipeline.

        Args:
            db: Database session
            notional_usd: Notional exposure amount in USD
        """
        self.db = db
        self.notional_usd = notional_usd

        # Repositories
        self.analytics_repo = AnalyticsRepository(db)
        self.config_repo = ConfigRepository(db)
        self.market_data_repo = MarketDataRepository(db)

        # Analytics modules
        self.forecaster = EnsembleForecaster(horizon_days=30)
        self.var_engine = HistoricalSimVaR(confidence=0.95, holding_period_days=30)
        self.basis_analyzer = BasisRiskAnalyzer(window_days=90)
        self.optimizer = HedgeOptimizer()

    async def execute_daily_run(self) -> str:
        """Execute complete analytics pipeline.

        Returns:
            Run ID (UUID as string)

        Raises:
            ModelError: If analytics execution fails
        """
        run_date = datetime.utcnow().date()

        # Reuse existing run for today if present (run_date is unique)
        existing = await self.analytics_repo.get_by_date(run_date)
        if existing:
            if existing.status == AnalyticsRunStatus.RUNNING:
                raise ModelError(
                    message="Pipeline already running for today",
                    model_name="pipeline",
                    context={"run_id": str(existing.id)},
                )
            # Reuse: update existing row for re-run; clear old recommendations
            run = existing
            run_id = run.id
            run.status = AnalyticsRunStatus.RUNNING
            run.mape = Decimal("0")
            run.forecast_json = {}
            run.var_results = {}
            run.basis_metrics = {}
            run.optimizer_result = {}
            run.model_versions = {"pipeline": "1.0"}
            run.duration_seconds = Decimal("0.01")
            # Delete only recommendations with no approvals/positions (preserve audit trail)
            has_approval = select(Approval.recommendation_id).where(
                Approval.recommendation_id == HedgeRecommendation.id
            ).exists()
            has_position = select(HedgePosition.recommendation_id).where(
                HedgePosition.recommendation_id == HedgeRecommendation.id
            ).exists()
            await self.db.execute(
                delete(HedgeRecommendation).where(
                    HedgeRecommendation.run_id == run_id,
                    ~has_approval,
                    ~has_position,
                )
            )
            await self.db.commit()
        else:
            run_id = uuid4()
            run = AnalyticsRun(
                id=run_id,
                run_date=run_date,
                status=AnalyticsRunStatus.RUNNING,
                mape=Decimal("0"),
                forecast_json={},
                var_results={},
                basis_metrics={},
                optimizer_result={},
                model_versions={"pipeline": "1.0"},
                duration_seconds=Decimal("0.01"),  # placeholder; constraint requires > 0
            )
            self.db.add(run)
            await self.db.commit()

        logger.info("analytics_pipeline_start", run_id=str(run_id), date=str(run_date))

        try:
            # Step 1: Fetch historical data
            df = await self._fetch_historical_data()
            if len(df) < 252:  # Minimum 1 year
                raise ModelError(
                    message=f"Insufficient historical data: {len(df)} observations",
                    model_name="pipeline",
                    context={"min_required": 252, "actual": len(df)},
                )

            # Step 2: Run forecasting
            forecast_result = await self._run_forecasting(df)

            # Step 3: Calculate VaR
            var_result = await self._calculate_var(df)

            # Step 4: Analyze basis risk
            basis_result = await self._analyze_basis_risk(df)

            # Step 5: Generate hedge recommendation
            recommendation = await self._generate_recommendation(
                df,
                forecast_result,
                var_result,
                basis_result,
            )

            # Update run record with results — use model's actual fields
            run.status = AnalyticsRunStatus.COMPLETED
            run.mape = Decimal(str(forecast_result.mape))
            run.forecast_json = {
                "mape": forecast_result.mape,
                "forecast_values": list(forecast_result.forecast_values),
                "model_versions": forecast_result.model_versions,
            }
            run.var_results = {
                "var_usd": var_result.var_usd,
                "var_pct": var_result.var_pct,
                "hedge_ratio": var_result.hedge_ratio,
            }
            run.basis_metrics = {
                "r2_heating_oil": basis_result.r2_heating_oil,
                "r2_brent": basis_result.r2_brent,
                "ifrs9_eligible": basis_result.ifrs9_eligible,
                "risk_level": basis_result.risk_level,
            }
            run.optimizer_result = {
                "optimal_hr": recommendation.hedge_ratio,
                "instrument_mix": recommendation.instrument_mix,
                "proxy_weights": recommendation.proxy_weights,
                "collateral_usd": recommendation.collateral_usd,
                "collateral_pct_of_reserves": recommendation.collateral_pct_of_reserves,
                "var_reduction_pct": recommendation.var_reduction_pct,
            }
            run.model_versions = forecast_result.model_versions
            # duration_seconds: placeholder for now; would need pipeline_start_time to compute
            run.duration_seconds = Decimal("60.0")

            # Store recommendation — use model's actual fields
            seq_result = await self.db.execute(
                select(func.coalesce(func.max(HedgeRecommendation.sequence_number), 0) + 1)
            )
            next_seq = seq_result.scalar_one()
            hedge_rec = HedgeRecommendation(
                run_id=run_id,
                sequence_number=next_seq,
                optimal_hr=Decimal(str(recommendation.hedge_ratio)),
                instrument_mix=recommendation.instrument_mix,
                proxy_weights=recommendation.proxy_weights,
                var_hedged=Decimal(str(recommendation.var_hedged)),
                var_unhedged=Decimal(str(recommendation.var_unhedged)),
                var_reduction_pct=Decimal(str(recommendation.var_reduction_pct)),
                collateral_usd=Decimal(str(recommendation.collateral_usd)),
                agent_outputs={},
                status=RecommendationStatus.PENDING,
            )
            self.db.add(hedge_rec)

            await self.db.commit()

            logger.info(
                "analytics_pipeline_success",
                run_id=str(run_id),
                mape=forecast_result.mape,
                var_usd=var_result.var_usd,
                optimal_hr=recommendation.hedge_ratio,
            )

            # Trigger n8n workflow to run AI agents and create recommendation
            settings = get_settings()
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{settings.API_INTERNAL_URL}/api/v1/recommendations/internal/n8n-trigger",
                        json={
                            "run_id": str(run_id),
                            "analytics_summary": {
                                "mape": forecast_result.mape,
                                "var_usd": var_result.var_usd,
                                "optimal_hr": recommendation.hedge_ratio,
                            },
                            "trigger_type": "pipeline_complete",
                        },
                    )
                    resp.raise_for_status()
                    logger.info("n8n_workflow_triggered", run_id=str(run_id), status=resp.status_code)
            except Exception as n8n_err:
                logger.warning("n8n_trigger_failed", run_id=str(run_id), error=str(n8n_err))

            return str(run_id)

        except Exception as e:
            # Mark run as failed — store error in forecast_json (no error_message column)
            run.status = AnalyticsRunStatus.FAILED
            run.forecast_json = {"error": str(e)}
            await self.db.commit()

            logger.error(
                "analytics_pipeline_failed",
                run_id=str(run_id),
                error=str(e),
                exc_info=True,
            )
            raise ModelError(
                message=f"Analytics pipeline failed: {str(e)}",
                model_name="pipeline",
                context={"run_id": str(run_id)},
            )

    async def _fetch_historical_data(self, lookback_days: int = 730) -> pd.DataFrame:
        """Fetch historical price data from database.

        Args:
            lookback_days: Days of historical data to fetch

        Returns:
            DataFrame with price history
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        result = await self.db.execute(
            select(PriceTick)
            .where(PriceTick.time >= cutoff_date)
            .order_by(PriceTick.time)
        )
        ticks = result.scalars().all()

        if not ticks:
            raise ModelError(
                message="No historical data available",
                model_name="data_fetch",
            )

        # Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "Date": t.time,
                    "Jet_Fuel_Spot_USD_bbl": float(t.jet_fuel_spot),
                    "Heating_Oil_Futures_USD_bbl": float(t.heating_oil_futures),
                    "Brent_Crude_Futures_USD_bbl": float(t.brent_futures),
                    "WTI_Crude_Futures_USD_bbl": float(t.wti_futures),
                    "Crack_Spread_USD_bbl": float(t.crack_spread),
                    "Volatility_Index_pct": float(t.volatility_index),
                }
                for t in ticks
            ]
        )

        logger.info("historical_data_fetched", rows=len(df))
        return df

    async def _run_forecasting(self, df: pd.DataFrame) -> ForecastResult:
        """Run ensemble forecasting model.

        Args:
            df: Historical price data

        Returns:
            Forecast result with MAPE validation
        """
        logger.info("forecasting_start")
        result = self.forecaster.predict(df)

        if result.mape > MAPE_ALERT:
            logger.warning(
                "forecast_mape_high",
                mape=result.mape,
                threshold=MAPE_ALERT,
            )

        return result

    async def _calculate_var(
        self,
        df: pd.DataFrame,
        test_hedge_ratios: Optional[list[float]] = None,
    ) -> VaRResult:
        """Calculate VaR for different hedge ratios.

        Args:
            df: Historical price data
            test_hedge_ratios: Hedge ratios to test (default: 0.0 to 1.0)

        Returns:
            VaR result for optimal hedge ratio
        """
        logger.info("var_calculation_start")

        if test_hedge_ratios is None:
            test_hedge_ratios = [0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 1.0]

        # Calculate VaR curve
        var_curve = self.var_engine.var_curve(
            df,
            notional=float(self.notional_usd),
            hedge_ratios=test_hedge_ratios,
        )

        # Find optimal (70% HR as baseline)
        optimal_result = next((v for v in var_curve if abs(v.hedge_ratio - 0.7) < 0.01), var_curve[-1])

        # Calculate reduction vs unhedged
        unhedged_var = next((v for v in var_curve if v.hedge_ratio == 0.0), None)
        if unhedged_var:
            reduction_pct = (
                (unhedged_var.var_usd - optimal_result.var_usd) / unhedged_var.var_usd * 100
            )
            logger.info(
                "var_reduction",
                unhedged=unhedged_var.var_usd,
                hedged=optimal_result.var_usd,
                reduction_pct=reduction_pct,
            )

        return optimal_result

    async def _analyze_basis_risk(self, df: pd.DataFrame) -> BasisRiskMetric:
        """Analyze basis risk and IFRS 9 eligibility.

        Args:
            df: Historical price data

        Returns:
            Basis risk metrics
        """
        logger.info("basis_risk_start")
        result = self.basis_analyzer.analyze(df)

        if not result.ifrs9_eligible:
            logger.warning(
                "ifrs9_ineligible",
                r2=result.r2_heating_oil,
                threshold=IFRS9_R2_MIN_PROSPECTIVE,
            )

        return result

    async def _generate_recommendation(
        self,
        df: pd.DataFrame,
        forecast: ForecastResult,
        var: VaRResult,
        basis: BasisRiskMetric,
    ) -> "HedgeRecommendationData":
        """Generate hedge recommendation based on analytics.

        Args:
            df: Historical price data
            forecast: Forecast results
            var: VaR results
            basis: Basis risk results

        Returns:
            Hedge recommendation data
        """
        logger.info("optimization_start")

        # Get current constraints from config
        config_snapshot = await self.config_repo.get_constraints_snapshot()

        # Build constraints
        constraints = build_optimizer_constraints(
            config_snapshot,
            cash_reserves=50_000_000,  # TODO: Get from platform config
            forecast_consumption_bbl=100_000,  # TODO: Calculate from consumption forecast
        )

        # Calculate VaR curve for optimizer
        var_curve = self.var_engine.var_curve(df, float(self.notional_usd))
        var_metrics = {f"hr_{int(v.hedge_ratio*100)}": v.var_usd for v in var_curve}

        # Optimize
        opt_result = self.optimizer.optimize(var_metrics, constraints)

        # Calculate risk reduction
        unhedged_var = next((v for v in var_curve if v.hedge_ratio == 0.0), var_curve[0])
        hedged_var = self.var_engine.compute_var(
            df,
            hedge_ratio=opt_result.optimal_hr,
            notional=float(self.notional_usd),
        )
        var_reduction_pct = (
            (unhedged_var.var_usd - hedged_var.var_usd) / unhedged_var.var_usd * 100
        )

        # Generate rationale
        rationale_parts = [
            f"Forecast MAPE: {forecast.mape:.2f}% ({'✓' if forecast.mape_passes_target else '⚠'})",
            f"VaR reduction: {var_reduction_pct:.1f}% ({'✓' if var_reduction_pct >= VAR_REDUCTION_TARGET * 100 else '⚠'})",
            f"Basis R²: {basis.r2_heating_oil:.4f} ({'✓ IFRS 9 eligible' if basis.ifrs9_eligible else '✗ Not eligible'})",
            f"Optimal HR: {opt_result.optimal_hr:.1%}",
            f"Solver: {'Converged' if opt_result.solver_converged else 'Failed'}",
        ]

        if opt_result.constraint_violations:
            rationale_parts.append(f"⚠ {len(opt_result.constraint_violations)} constraint violations")

        rationale = " | ".join(rationale_parts)

        return HedgeRecommendationData(
            hedge_ratio=opt_result.optimal_hr,
            var_reduction_pct=var_reduction_pct,
            collateral_usd=opt_result.collateral_usd,
            collateral_pct_of_reserves=opt_result.collateral_pct_of_reserves,
            rationale=rationale,
            instrument_mix=opt_result.instrument_mix,
            proxy_weights=opt_result.proxy_weights,
            var_hedged=hedged_var.var_usd,
            var_unhedged=unhedged_var.var_usd,
        )


class HedgeRecommendationData:
    """Data class for hedge recommendations."""

    def __init__(
        self,
        hedge_ratio: float,
        var_reduction_pct: float,
        collateral_usd: float,
        rationale: str,
        instrument_mix: Optional[dict[str, float]] = None,
        proxy_weights: Optional[dict[str, float]] = None,
        var_hedged: float = 0.0,
        var_unhedged: float = 0.0,
        collateral_pct_of_reserves: float = 0.0,
    ) -> None:
        self.hedge_ratio = hedge_ratio
        self.var_reduction_pct = var_reduction_pct
        self.collateral_usd = collateral_usd
        self.collateral_pct_of_reserves = collateral_pct_of_reserves
        self.rationale = rationale
        self.instrument_mix = instrument_mix or {"futures": 0.7, "options": 0.2, "collars": 0.1, "swaps": 0.0}
        self.proxy_weights = proxy_weights or {"heating_oil": 0.75, "brent": 0.15, "wti": 0.10}
        self.var_hedged = var_hedged
        self.var_unhedged = var_unhedged
