"""One-time backfill script. Run after first deployment:
    python scripts/backfill_prices.py

Sources:
  - EIA API: jet_fuel_spot, wti_spot, brent_spot (2020-01-01 to today)
  - yfinance: heating_oil_futures (2020-01-01 to today)

Upserts to price_ticks table — safe to run multiple times (idempotent).
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from app.clients.eia import EIAClient
from app.clients.yfinance_client import YFinanceClient
from app.config import get_settings

log = structlog.get_logger()

START_DATE = date(2020, 1, 1)


async def main() -> None:
    """Main backfill logic."""
    settings = get_settings()
    eia = EIAClient(api_key=settings.EIA_API_KEY)
    yf = YFinanceClient()

    log.info("starting_backfill", start=str(START_DATE), end=str(date.today()))

    # Fetch historical data from both sources
    eia_df = await eia.get_historical(START_DATE, date.today())
    loop = asyncio.get_event_loop()
    yf_df = await loop.run_in_executor(
        None, yf.get_historical, START_DATE, date.today()
    )

    # Merge on date
    merged = eia_df.merge(yf_df, on="date", how="inner")
    merged["crack_spread"] = merged["jet_fuel_spot"] - merged["heating_oil_futures"]

    log.info("backfill_data_ready", rows=len(merged))

    # TODO: upsert to price_ticks table using PriceTickRepository
    # (wire in after DB layer is confirmed working)
    # For now: save to CSV as verification
    output_dir = Path(__file__).parent.parent.parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "backfill_verification.csv"
    
    merged.to_csv(output_path, index=False)
    log.info("backfill_complete", output=str(output_path), rows=len(merged))


if __name__ == "__main__":
    asyncio.run(main())
