"""Data ingestion service for loading market data.

Handles:
- CSV import from historical dataset
- External API clients (EIA, CME, ICE)
- Data quality validation
- Circuit breaker pattern
"""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PriceTick
from app.exceptions import DataIngestionError
from app.repositories import MarketDataRepository

logger = structlog.get_logger()


class CSVDataLoader:
    """Load historical price data from CSV files."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize CSV loader with database session."""
        self.db = db
        self.repo = MarketDataRepository(db)

    async def load_from_csv(
        self,
        csv_path: Path,
        source: str = "historical_csv",
        batch_size: int = 100,
    ) -> dict[str, int]:
        """Load price data from CSV file into database.

        Args:
            csv_path: Path to CSV file
            source: Data source identifier
            batch_size: Number of rows to insert per batch

        Returns:
            Dictionary with import statistics

        Raises:
            DataIngestionError: If CSV format is invalid or data quality fails
        """
        if not csv_path.exists():
            raise DataIngestionError(
                message=f"CSV file not found: {csv_path}",
                source="csv_loader",
                context={"path": str(csv_path)},
            )

        logger.info("csv_load_start", path=str(csv_path), source=source)

        try:
            # Read CSV with pandas for validation
            df = pd.read_csv(csv_path)

            # Validate required columns
            required_cols = [
                "Date",
                "Jet_Fuel_Spot_USD_bbl",
                "Heating_Oil_Futures_USD_bbl",
                "Brent_Crude_Futures_USD_bbl",
                "WTI_Crude_Futures_USD_bbl",
                "Crack_Spread_USD_bbl",
                "Volatility_Index_pct",
            ]

            missing_cols = set(required_cols) - set(df.columns)
            if missing_cols:
                raise DataIngestionError(
                    message=f"Missing required columns: {missing_cols}",
                    source="csv_loader",
                    context={"missing": list(missing_cols)},
                )

            # Data quality checks
            null_counts = df[required_cols].isnull().sum()
            if null_counts.any():
                logger.warning(
                    "csv_null_values",
                    null_counts=null_counts.to_dict(),
                )

            # Convert to records
            records_imported = 0
            records_skipped = 0
            records_updated = 0

            for i in range(0, len(df), batch_size):
                batch = df.iloc[i : i + batch_size]

                for _, row in batch.iterrows():
                    try:
                        # Parse date and ensure UTC for timestamptz column
                        tick_time = pd.to_datetime(row["Date"])
                        if tick_time.tzinfo is None:
                            tick_time = tick_time.tz_localize("UTC")

                        # Check if record exists
                        existing = await self.db.execute(
                            select(PriceTick).where(
                                PriceTick.time == tick_time,
                                PriceTick.source == source,
                            )
                        )
                        existing_tick = existing.scalar_one_or_none()

                        # Create or update tick
                        tick_data = {
                            "time": tick_time,
                            "source": source,
                            "jet_fuel_spot": Decimal(str(row["Jet_Fuel_Spot_USD_bbl"])),
                            "heating_oil_futures": Decimal(
                                str(row["Heating_Oil_Futures_USD_bbl"])
                            ),
                            "brent_futures": Decimal(
                                str(row["Brent_Crude_Futures_USD_bbl"])
                            ),
                            "wti_futures": Decimal(
                                str(row["WTI_Crude_Futures_USD_bbl"])
                            ),
                            "crack_spread": Decimal(str(row["Crack_Spread_USD_bbl"])),
                            "volatility_index": Decimal(
                                str(row["Volatility_Index_pct"])
                            ),
                        }

                        if existing_tick:
                            # Update existing
                            for key, value in tick_data.items():
                                setattr(existing_tick, key, value)
                            records_updated += 1
                        else:
                            # Insert new
                            tick = PriceTick(**tick_data)
                            self.db.add(tick)
                            records_imported += 1

                    except Exception as e:
                        logger.warning(
                            "csv_row_skip",
                            row_index=i,
                            error=str(e),
                        )
                        records_skipped += 1
                        continue

                # Commit batch
                await self.db.commit()
                logger.info(
                    "csv_batch_complete",
                    batch_num=i // batch_size + 1,
                    records_in_batch=len(batch),
                )

            stats = {
                "imported": records_imported,
                "updated": records_updated,
                "skipped": records_skipped,
                "total": len(df),
            }

            logger.info("csv_load_complete", **stats)
            return stats

        except Exception as e:
            await self.db.rollback()
            raise DataIngestionError(
                message=f"CSV load failed: {str(e)}",
                source="csv_loader",
                context={"error": str(e)},
            )


class DataQualityChecker:
    """Validate data quality for ingested price ticks."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize quality checker with database session."""
        self.db = db

    async def check_latest_prices(self, lookback_hours: int = 48) -> dict[str, bool]:
        """Check data quality for recent price ticks.

        Args:
            lookback_hours: Hours to look back for quality checks

        Returns:
            Dictionary with quality check results
        """
        checks = {
            "has_recent_data": False,
            "no_null_values": False,
            "prices_positive": False,
            "volatility_reasonable": False,
        }

        try:
            # Get recent ticks
            cutoff_time = datetime.utcnow() - pd.Timedelta(hours=lookback_hours)

            result = await self.db.execute(
                select(PriceTick)
                .where(PriceTick.time >= cutoff_time)
                .order_by(PriceTick.time.desc())
                .limit(100)
            )
            recent_ticks = result.scalars().all()

            if not recent_ticks:
                logger.warning("no_recent_data", lookback_hours=lookback_hours)
                return checks

            checks["has_recent_data"] = True

            # Convert to DataFrame for analysis
            df = pd.DataFrame(
                [
                    {
                        "time": t.time,
                        "jet_fuel": float(t.jet_fuel_spot),
                        "heating_oil": float(t.heating_oil_futures),
                        "brent": float(t.brent_futures),
                        "wti": float(t.wti_futures),
                        "crack_spread": float(t.crack_spread),
                        "volatility": float(t.volatility_index),
                    }
                    for t in recent_ticks
                ]
            )

            # Check for nulls
            checks["no_null_values"] = not df.isnull().any().any()

            # Check positive prices
            price_cols = ["jet_fuel", "heating_oil", "brent", "wti"]
            checks["prices_positive"] = (df[price_cols] > 0).all().all()

            # Check volatility is reasonable (0-100%)
            checks["volatility_reasonable"] = (
                (df["volatility"] >= 0) & (df["volatility"] <= 100)
            ).all()

            # Log any failures
            failed_checks = [k for k, v in checks.items() if not v]
            if failed_checks:
                logger.warning("quality_checks_failed", failed=failed_checks)
            else:
                logger.info("quality_checks_passed")

            return checks

        except Exception as e:
            logger.error("quality_check_error", error=str(e))
            return checks


async def import_historical_csv(
    db: AsyncSession,
    csv_path: Optional[Path] = None,
) -> dict[str, int]:
    """Import historical fuel hedging dataset from CSV.

    Args:
        db: Database session
        csv_path: Path to CSV file (defaults to data/fuel_hedging_dataset.csv)

    Returns:
        Import statistics
    """
    if csv_path is None:
        # Default to project data directory
        csv_path = Path(__file__).parent.parent.parent / "data" / "fuel_hedging_dataset.csv"

    loader = CSVDataLoader(db)
    stats = await loader.load_from_csv(csv_path, source="historical_csv")

    # Run quality checks
    checker = DataQualityChecker(db)
    quality_results = await checker.check_latest_prices(lookback_hours=24 * 365 * 5)  # 5 years

    if not all(quality_results.values()):
        logger.warning("import_quality_issues", quality=quality_results)

    return stats
