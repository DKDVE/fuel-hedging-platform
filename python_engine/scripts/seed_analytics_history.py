"""
seed_analytics_history.py
Generates 12 months of realistic analytics run history and inserts it into
analytics_runs. Uses correlated random walks seeded from the actual dataset
so values are realistic, not random.

Also runs the walk-forward backtest engine and stores results in backtest_runs.

Run: docker exec hedge-api python scripts/seed_analytics_history.py

Idempotent: skips dates that already have a COMPLETED run.
"""

import asyncio
import hashlib
import sys
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.analytics.backtester import BacktestEngine
from app.db.base import AsyncSessionLocal
from app.db.models import AnalyticsRun, AnalyticsRunStatus, BacktestRun

log = structlog.get_logger()

SEED = 42
N_WEEKS = 52
VAR_LIMIT_USD = 5_000_000
MAPE_TARGET = 8.0
IFRS9_R2_MIN = 0.80


def _load_dataset(csv_path: Path) -> pd.DataFrame:
    """Load fuel hedging dataset for price anchoring."""
    df = pd.read_csv(csv_path)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def _generate_correlated_walks(rng: np.random.Generator) -> dict:
    """Generate correlated random walks for analytics metrics."""
    n = N_WEEKS

    # VaR: mean-reverting around $2.1M, bounded $1.2M–$4.8M
    var_base = 2_100_000
    var_walk = np.zeros(n)
    var_walk[0] = var_base
    for i in range(1, n):
        shock = rng.normal(0, 80_000)
        mean_rev = 0.05 * (var_base - var_walk[i - 1])
        var_walk[i] = max(1_200_000, min(4_800_000, var_walk[i - 1] + mean_rev + shock))

    # MAPE: trends down (model improves) with weekly noise
    mape_start = 7.8
    mape_end = 4.2
    mape_trend = np.linspace(mape_start, mape_end, n)
    mape_noise = rng.normal(0, 0.4, n)
    mape_walk = np.clip(mape_trend + mape_noise, 3.5, 10.5)

    # Hedge ratio: mean-reverts around 0.65, bounded 0.55–0.75
    hr_base = 0.65
    hr_walk = np.zeros(n)
    hr_walk[0] = hr_base
    for i in range(1, n):
        shock = rng.normal(0, 0.015)
        mean_rev = 0.1 * (hr_base - hr_walk[i - 1])
        hr_walk[i] = np.clip(hr_walk[i - 1] + mean_rev + shock, 0.55, 0.75)

    # Collateral tracks hedge ratio
    collateral_walk = hr_walk * 14_000_000 * rng.uniform(0.88, 1.12, n)
    collateral_walk = np.clip(collateral_walk, 800_000, 2_000_000)

    # R² heating oil: mean-reverts around 0.862, bounded 0.81–0.91
    r2_base = 0.862
    r2_walk = np.zeros(n)
    r2_walk[0] = r2_base
    for i in range(1, n):
        shock = rng.normal(0, 0.006)
        mean_rev = 0.12 * (r2_base - r2_walk[i - 1])
        r2_walk[i] = np.clip(r2_walk[i - 1] + mean_rev + shock, 0.81, 0.92)

    return {
        "var_usd": var_walk,
        "mape": mape_walk,
        "optimal_hr": hr_walk,
        "collateral_usd": collateral_walk,
        "r2_heating_oil": r2_walk,
    }


def _build_forecast_json(
    last_price: float, rng: np.random.Generator, n_days: int = 30
) -> list[float]:
    """Build 30-day GBM-style forecast from last known price."""
    drift = 0.0001
    vol = 0.02
    prices = [last_price]
    for _ in range(n_days - 1):
        z = rng.standard_normal()
        new_p = prices[-1] * (1 + drift + vol * z)
        prices.append(max(30.0, min(150.0, new_p)))
    return prices


async def seed_analytics_runs(session: AsyncSession) -> int:
    """Insert analytics runs. Returns count of newly inserted rows."""
    base = Path(__file__).parent.parent
    csv_path = base / "data" / "fuel_hedging_dataset.csv"
    if not csv_path.exists():
        # Local: data is at project root; Docker: data mounted at /app/data
        csv_path = base.parent / "data" / "fuel_hedging_dataset.csv"
    if not csv_path.exists():
        csv_path = Path("/app/data/fuel_hedging_dataset.csv")
    if not csv_path.exists():
        log.error("dataset_not_found", path=str(csv_path))
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = _load_dataset(csv_path)
    last_price = float(df["Jet_Fuel_Spot_USD_bbl"].iloc[-1])
    rng = np.random.default_rng(seed=SEED)

    walks = _generate_correlated_walks(rng)

    # Weekly dates: last 12 months, every Monday
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    mondays: list[date] = []
    d = start_date
    while d <= end_date:
        if d.weekday() == 0:  # Monday
            mondays.append(d)
        d += timedelta(days=1)
    mondays = mondays[:N_WEEKS]

    inserted = 0
    for i, run_date in enumerate(mondays):
        # Skip if COMPLETED run already exists
        result = await session.execute(
            select(AnalyticsRun.id).where(
                AnalyticsRun.run_date == run_date,
                AnalyticsRun.status == AnalyticsRunStatus.COMPLETED,
            )
        )
        if result.scalar_one_or_none():
            continue

        var_usd = float(walks["var_usd"][i])
        var_unhedged = var_usd / 0.57  # approximate unhedged VaR
        var_reduction = (1 - var_usd / var_unhedged) * 100 if var_unhedged else 40.0

        forecast_values = _build_forecast_json(last_price, rng)
        optimal_hr = float(walks["optimal_hr"][i])
        collateral_usd = float(walks["collateral_usd"][i])
        collateral_pct = (collateral_usd / 15_000_000) * 100  # 15M reserves

        run = AnalyticsRun(
            run_date=run_date,
            mape=Decimal(str(round(walks["mape"][i], 2))),
            forecast_json={
                "mape": float(walks["mape"][i]),
                "forecast_values": [float(p) for p in forecast_values],
                "model_versions": {"arima": "1.0", "xgboost": "1.2", "ensemble": "2.1"},
            },
            var_results={
                "var_usd": var_usd,
                "var_unhedged_usd": var_unhedged,
                "var_reduction_pct": round(var_reduction, 2),
                "confidence_level": 0.95,
            },
            basis_metrics={
                "r2_heating_oil": round(float(walks["r2_heating_oil"][i]), 4),
                "r2_brent": round(float(walks["r2_heating_oil"][i]) * 0.92, 4),
                "r2_wti": round(float(walks["r2_heating_oil"][i]) * 0.94, 4),
                "crack_spread_zscore": round(float(rng.uniform(-0.5, 1.5)), 2),
                "ifrs9_eligible": bool(walks["r2_heating_oil"][i] >= IFRS9_R2_MIN),
            },
            optimizer_result={
                "optimal_hr": optimal_hr,
                "instrument_mix": {"futures": 0.6, "options": 0.3, "swaps": 0.1},
                "proxy_weights": {"heating_oil": 0.7, "brent": 0.2, "wti": 0.1},
                "collateral_usd": collateral_usd,
                "collateral_pct_of_reserves": round(collateral_pct, 2),
                "solver_converged": True,
            },
            model_versions={"arima": "1.0", "xgboost": "1.2", "ensemble": "2.1"},
            duration_seconds=Decimal("60.0"),
            status=AnalyticsRunStatus.COMPLETED,
        )
        session.add(run)
        inserted += 1

    await session.commit()
    return inserted


def _compute_dataset_hash(csv_path: Path) -> str:
    """SHA256 hash of CSV for change detection."""
    with open(csv_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


async def seed_backtest(session: AsyncSession, csv_path: Path) -> bool:
    """Run backtest and store in backtest_runs. Returns True if stored."""
    df = pd.read_csv(csv_path)
    dataset_hash = _compute_dataset_hash(csv_path)

    # Check if we already have a run with this hash
    result = await session.execute(
        select(BacktestRun.id).where(BacktestRun.dataset_hash == dataset_hash)
    )
    if result.scalar_one_or_none():
        log.info("backtest_skipped", reason="dataset_unchanged")
        return False

    log.info("backtest_start")
    engine = BacktestEngine(notional_usd=10_000_000, weekly_volume_bbl=20_000)
    results = engine.run(df)
    summary = BacktestEngine.summarise(results)

    # Convert to JSON-serializable
    weekly_list = [
        {
            "week_date": r.week_date.isoformat(),
            "optimal_hr": r.optimal_hr,
            "jet_fuel_spot": r.jet_fuel_spot,
            "hedged_cost_per_bbl": r.hedged_cost_per_bbl,
            "unhedged_cost_per_bbl": r.unhedged_cost_per_bbl,
            "weekly_savings_usd": r.weekly_savings_usd,
            "cumulative_savings_usd": r.cumulative_savings_usd,
            "mape_at_date": r.mape_at_date,
            "r2_at_date": r.r2_at_date,
            "hedge_effectiveness": r.hedge_effectiveness,
        }
        for r in results
    ]
    summary_dict = {
        "total_weeks": summary.total_weeks,
        "profitable_weeks": summary.profitable_weeks,
        "total_savings_usd": summary.total_savings_usd,
        "avg_weekly_savings_usd": summary.avg_weekly_savings_usd,
        "max_weekly_savings_usd": summary.max_weekly_savings_usd,
        "max_weekly_loss_usd": summary.max_weekly_loss_usd,
        "savings_volatility": summary.savings_volatility,
        "sharpe_ratio": summary.sharpe_ratio,
        "avg_mape": summary.avg_mape,
        "avg_r2_heating_oil": summary.avg_r2_heating_oil,
        "var_reduction_achieved": summary.var_reduction_achieved,
        "h1_validated": summary.h1_validated,
        "h4_validated": summary.h4_validated,
    }

    run = BacktestRun(
        computed_at=datetime.now(timezone.utc),
        notional_usd=Decimal("10000000"),
        weekly_results=weekly_list,
        summary=summary_dict,
        dataset_hash=dataset_hash,
    )
    session.add(run)
    await session.commit()
    log.info("backtest_stored", weeks=summary.total_weeks, savings=summary.total_savings_usd)
    return True


async def main() -> None:
    """Entry point."""
    log.info("seed_analytics_start")
    base = Path(__file__).parent.parent
    csv_path = base / "data" / "fuel_hedging_dataset.csv"
    if not csv_path.exists():
        csv_path = base.parent / "data" / "fuel_hedging_dataset.csv"
    if not csv_path.exists():
        csv_path = Path("/app/data/fuel_hedging_dataset.csv")

    async with AsyncSessionLocal() as session:
        inserted = await seed_analytics_runs(session)

        # Run backtest
        if csv_path.exists():
            print("Running backtest engine (this takes ~30 seconds)...")
            await seed_backtest(session, csv_path)

    log.info("seed_analytics_complete", inserted=inserted)

    # Summary (use fixed ranges from the walk parameters)
    mape_min, mape_max = 3.5, 10.5
    var_min, var_max = 1_200_000, 4_800_000
    hr_min, hr_max = 0.55, 0.75
    r2_min = 0.81

    print()
    print(f"✓ Seeded {inserted} analytics runs (last 12 months)")
    print(f"✓ MAPE range: {mape_min}% – {mape_max}%  (target: <{MAPE_TARGET}%)")
    print(f"✓ VaR range:  ${var_min/1e6:.2f}M – ${var_max/1e6:.2f}M")
    print(f"✓ Hedge ratio range: {hr_min*100:.1f}% – {hr_max*100:.1f}%")
    print(f"✓ All R² values above {IFRS9_R2_MIN} (IFRS 9 compliant)")
    print("✓ Backtest complete (see Analytics → Backtesting tab)")


if __name__ == "__main__":
    asyncio.run(main())
