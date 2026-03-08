"""EIA Open Data API client.

Covers: Jet Fuel spot, WTI spot, Brent spot.
Data is published daily (business days). No rate limit concerns for daily pipeline use.
Public domain — no restrictions on commercial use.
"""

import pandas as pd
import structlog
from dataclasses import dataclass
from datetime import date

from app.clients.base import BaseAPIClient
from app.exceptions import DataIngestionError

log = structlog.get_logger()

EIA_BASE_URL = "https://api.eia.gov/v2"

# EIA series IDs — verified correct as of 2025
EIA_SERIES = {
    "jet_fuel_spot": "petroleum/pri/spt/data/",  # EPD2F — US Gulf Coast Kerosene Jet Fuel
    "wti_spot": "petroleum/pri/spt/data/",  # RWTC — WTI Cushing Oklahoma
    "brent_spot": "petroleum/pri/spt/data/",  # RBRTE — Europe Brent Spot
}

EIA_PRODUCT_CODES = {
    "jet_fuel_spot": "EPD2F",
    "wti_spot": "RWTC",
    "brent_spot": "RBRTE",
}


@dataclass(frozen=True)
class EIADailyPrices:
    """Daily prices from EIA API."""

    date: date
    jet_fuel_spot: float  # USD/bbl (converted from USD/gallon)
    wti_spot: float  # USD/bbl
    brent_spot: float  # USD/bbl
    source: str = "eia"


class EIAClient(BaseAPIClient):
    """Client for EIA Open Data API."""

    def __init__(self, api_key: str | None) -> None:
        super().__init__(api_key=api_key, base_url=EIA_BASE_URL)

    async def get_latest_prices(self) -> EIADailyPrices:
        """Fetch the most recent available daily closing prices for all 3 instruments.

        EIA updates daily (usually by 17:00 ET on business days).
        On weekends/holidays, returns the last available business day price.
        """
        if not self.api_key:
            raise DataIngestionError(
                "EIA_API_KEY not configured. Get a free key at: "
                "https://www.eia.gov/opendata/register.php",
                source="EIAClient",
            )

        results: dict[str, float] = {}
        results_date: date | None = None

        for field_name, product_code in EIA_PRODUCT_CODES.items():
            data = await self._fetch(
                "GET",
                "/petroleum/pri/spt/data/",
                params={
                    "api_key": self.api_key,
                    "frequency": "daily",
                    "data[0]": "value",
                    "facets[product][]": product_code,
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": 1,
                    "offset": 0,
                },
            )

            rows = data.get("response", {}).get("data", [])
            if not rows:
                raise DataIngestionError(
                    f"EIA returned no data for product {product_code}",
                    source="EIAClient",
                )

            row = rows[0]
            price = float(row["value"])
            period = date.fromisoformat(row["period"])

            # Jet fuel from EIA is USD/gallon — convert to USD/bbl (1 bbl = 42 gallons)
            if field_name == "jet_fuel_spot":
                price = price * 42.0

            results[field_name] = price
            if results_date is None:
                results_date = period

        assert results_date is not None
        log.info(
            "eia_fetch_complete",
            date=str(results_date),
            jet_fuel=round(results["jet_fuel_spot"], 2),
            wti=round(results["wti_spot"], 2),
            brent=round(results["brent_spot"], 2),
        )

        return EIADailyPrices(
            date=results_date,
            jet_fuel_spot=results["jet_fuel_spot"],
            wti_spot=results["wti_spot"],
            brent_spot=results["brent_spot"],
        )

    async def get_historical(self, start: date, end: date) -> pd.DataFrame:
        """Fetch historical daily prices for all 3 instruments.

        Used for: initial DB backfill, dataset gap detection, walk-forward analytics.
        Returns DataFrame with columns: date, jet_fuel_spot, wti_spot, brent_spot.
        """
        if not self.api_key:
            raise DataIngestionError("EIA_API_KEY not configured", source="EIAClient")

        length = (end - start).days + 10  # buffer for weekends
        frames = {}

        for field_name, product_code in EIA_PRODUCT_CODES.items():
            data = await self._fetch(
                "GET",
                "/petroleum/pri/spt/data/",
                params={
                    "api_key": self.api_key,
                    "frequency": "daily",
                    "data[0]": "value",
                    "facets[product][]": product_code,
                    "sort[0][column]": "period",
                    "sort[0][direction]": "asc",
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "length": min(length, 5000),
                    "offset": 0,
                },
            )

            rows = data.get("response", {}).get("data", [])
            df = pd.DataFrame(rows)[["period", "value"]].rename(
                columns={"period": "date", "value": field_name}
            )
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df[field_name] = pd.to_numeric(df[field_name])
            if field_name == "jet_fuel_spot":
                df[field_name] = df[field_name] * 42.0  # USD/gal → USD/bbl

            frames[field_name] = df.set_index("date")

        combined = pd.concat(frames.values(), axis=1).reset_index()
        combined.columns = ["date"] + list(EIA_PRODUCT_CODES.keys())
        return combined.dropna().sort_values("date")
