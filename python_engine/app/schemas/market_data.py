"""Pydantic schemas for market data endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse, TimestampMixin, UUIDMixin


class PriceTickResponse(BaseModel):
    """Price tick response schema."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    time: datetime = Field(..., description="Tick timestamp (UTC)")
    source: str = Field(..., description="Data source identifier")
    jet_fuel_spot: Decimal = Field(..., description="Jet fuel spot price (USD/bbl)")
    heating_oil_futures: Decimal = Field(..., description="Heating oil futures price (USD/bbl)")
    brent_crude_futures: Decimal = Field(..., description="Brent crude futures price (USD/bbl)")
    wti_crude_futures: Decimal = Field(..., description="WTI crude futures price (USD/bbl)")
    crack_spread: Decimal = Field(..., description="Crack spread (USD/bbl)")
    volatility_index: Decimal = Field(..., description="Volatility index (%)")


class MarketDataQueryParams(BaseModel):
    """Query parameters for market data endpoints."""

    model_config = ConfigDict(extra="forbid")

    start_date: Optional[datetime] = Field(None, description="Start date (UTC)")
    end_date: Optional[datetime] = Field(None, description="End date (UTC)")
    source: Optional[str] = Field(None, description="Filter by data source")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum records to return")


class PriceTickList(BaseModel):
    """List of price ticks response."""

    model_config = ConfigDict(extra="forbid")

    items: list[PriceTickResponse]
    total: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class LatestPricesResponse(BaseModel):
    """Latest prices for all instruments."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(..., description="Data timestamp (UTC)")
    jet_fuel_spot: Decimal = Field(..., description="Current jet fuel spot (USD/bbl)")
    heating_oil_futures: Decimal = Field(..., description="Current heating oil futures (USD/bbl)")
    brent_crude_futures: Decimal = Field(..., description="Current Brent crude (USD/bbl)")
    wti_crude_futures: Decimal = Field(..., description="Current WTI crude (USD/bbl)")
    crack_spread: Decimal = Field(..., description="Current crack spread (USD/bbl)")
    volatility_index: Decimal = Field(..., description="Current volatility (%)")


class PriceStatistics(BaseModel):
    """Price statistics over a period."""

    model_config = ConfigDict(extra="forbid")

    instrument: str = Field(..., description="Instrument name")
    mean: Decimal = Field(..., description="Average price")
    median: Decimal = Field(..., description="Median price")
    std_dev: Decimal = Field(..., description="Standard deviation")
    min: Decimal = Field(..., description="Minimum price")
    max: Decimal = Field(..., description="Maximum price")
    count: int = Field(..., description="Number of observations")


class MarketDataStatsResponse(BaseModel):
    """Market data statistics response."""

    model_config = ConfigDict(extra="forbid")

    period_start: datetime
    period_end: datetime
    statistics: list[PriceStatistics]
