"""yfinance client for Heating Oil futures (HO=F) — NYMEX front-month.

Used ONLY for the daily pipeline (once per day). Never called for intraday data.

Note: yfinance uses Yahoo Finance's unofficial API.
Usage: Daily pipeline only (1 call/day). Not used for intraday simulation.
Fallback: If yfinance fails, use previous day's value with quality_flag='STALE'.
"""

import pandas as pd
import structlog
from dataclasses import dataclass
from datetime import date, timedelta

from app.exceptions import DataIngestionError

log = structlog.get_logger()

HO_TICKER = "HO=F"  # NYMEX Heating Oil front-month futures, USD/gallon


@dataclass(frozen=True)
class YFinanceDailyPrice:
    """Daily price from yfinance."""

    date: date
    heating_oil_futures: float  # USD/bbl (converted from USD/gallon)
    source: str = "yfinance"


class YFinanceClient:
    """Thin wrapper around yfinance for Heating Oil futures.

    No BaseAPIClient inheritance — yfinance manages its own HTTP.
    Circuit breaker implemented manually.
    """

    def __init__(self) -> None:
        self._consecutive_failures = 0
        self._failure_threshold = 3

    def get_latest_price(self) -> YFinanceDailyPrice:
        """Fetch the most recent closing price for HO=F.

        Returns yesterday's close (most recent settled price).
        yfinance is synchronous — run in executor if needed in async context.
        """
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(HO_TICKER)
            # Fetch last 5 days to ensure we get the latest settled price
            hist = ticker.history(period="5d")

            if hist.empty:
                raise DataIngestionError(
                    f"yfinance returned empty history for {HO_TICKER}",
                    source="YFinanceClient",
                )

            latest = hist.iloc[-1]
            price_per_gallon = float(latest["Close"])
            price_per_bbl = price_per_gallon * 42.0  # 1 bbl = 42 gallons

            result_date = hist.index[-1].date()

            self._consecutive_failures = 0
            log.info(
                "yfinance_fetch_complete",
                ticker=HO_TICKER,
                date=str(result_date),
                price_per_gallon=round(price_per_gallon, 4),
                price_per_bbl=round(price_per_bbl, 2),
            )

            return YFinanceDailyPrice(
                date=result_date,
                heating_oil_futures=price_per_bbl,
            )

        except Exception as e:
            self._consecutive_failures += 1
            log.error(
                "yfinance_fetch_failed",
                ticker=HO_TICKER,
                error=str(e),
                consecutive_failures=self._consecutive_failures,
            )
            raise DataIngestionError(
                f"yfinance failed for {HO_TICKER}: {e}",
                source="YFinanceClient",
            ) from e

    def get_historical(self, start: date, end: date) -> pd.DataFrame:
        """Fetch historical daily Heating Oil futures prices.

        Used for: initial backfill of 2020-2024 dataset.
        Returns DataFrame with columns: date, heating_oil_futures.
        """
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(HO_TICKER)
            hist = ticker.history(
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
            )

            if hist.empty:
                raise DataIngestionError(
                    f"yfinance returned empty history for {HO_TICKER} "
                    f"between {start} and {end}",
                    source="YFinanceClient",
                )

            df = hist[["Close"]].reset_index()
            df.columns = ["date", "heating_oil_futures"]
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df["heating_oil_futures"] = df["heating_oil_futures"] * 42.0

            log.info(
                "yfinance_historical_complete",
                ticker=HO_TICKER,
                rows=len(df),
                start=str(start),
                end=str(end),
            )
            return df.sort_values("date")

        except Exception as e:
            raise DataIngestionError(
                f"yfinance historical failed for {HO_TICKER}: {e}",
                source="YFinanceClient",
            ) from e
