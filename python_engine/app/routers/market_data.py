"""Market data API endpoints.

Provides access to historical and real-time price data.
"""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select

from app.dependencies import AnalystUser, CurrentUser, DatabaseSession
from app.db.models import PriceTick
from app.repositories import MarketDataRepository
from app.schemas.market_data import (
    LatestPricesResponse,
    MarketDataQueryParams,
    MarketDataStatsResponse,
    PriceStatistics,
    PriceTickList,
    PriceTickResponse,
)

router = APIRouter()
logger = structlog.get_logger()


@router.get("/latest", response_model=LatestPricesResponse)
async def get_latest_prices(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> LatestPricesResponse:
    """Get the most recent price tick for all instruments.

    Accessible to all authenticated users.
    """
    result = await db.execute(
        select(PriceTick).order_by(desc(PriceTick.time)).limit(1)
    )
    latest = result.scalar_one_or_none()

    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NO_DATA", "message": "No price data available"},
        )

    return LatestPricesResponse(
        timestamp=latest.time,
        jet_fuel_spot=latest.jet_fuel_spot,
        heating_oil_futures=latest.heating_oil_futures,
        brent_crude_futures=latest.brent_crude_futures,
        wti_crude_futures=latest.wti_crude_futures,
        crack_spread=latest.crack_spread,
        volatility_index=latest.volatility_index,
    )


@router.get("/history", response_model=PriceTickList)
async def get_price_history(
    current_user: CurrentUser,
    db: DatabaseSession,
    start_date: Optional[datetime] = Query(None, description="Start date (UTC)"),
    end_date: Optional[datetime] = Query(None, description="End date (UTC)"),
    source: Optional[str] = Query(None, description="Data source filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records"),
) -> PriceTickList:
    """Get historical price data with optional filtering.

    Accessible to all authenticated users.
    """
    # Build query
    query = select(PriceTick)

    # Apply filters
    if start_date:
        query = query.where(PriceTick.time >= start_date)
    if end_date:
        query = query.where(PriceTick.time <= end_date)
    if source:
        query = query.where(PriceTick.source == source)

    # Order and limit
    query = query.order_by(desc(PriceTick.time)).limit(limit)

    # Execute
    result = await db.execute(query)
    ticks = result.scalars().all()

    # Count total (without limit)
    count_query = select(func.count(PriceTick.id))
    if start_date:
        count_query = count_query.where(PriceTick.time >= start_date)
    if end_date:
        count_query = count_query.where(PriceTick.time <= end_date)
    if source:
        count_query = count_query.where(PriceTick.source == source)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    logger.info(
        "price_history_fetched",
        user_id=str(current_user.id),
        records=len(ticks),
        total=total,
    )

    return PriceTickList(
        items=[PriceTickResponse.model_validate(t) for t in ticks],
        total=total,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/statistics", response_model=MarketDataStatsResponse)
async def get_price_statistics(
    current_user: AnalystUser,
    db: DatabaseSession,
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics"),
) -> MarketDataStatsResponse:
    """Calculate price statistics over a period.

    Requires ANALYST role or higher.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()

    # Fetch data
    result = await db.execute(
        select(PriceTick)
        .where(PriceTick.time >= start_date)
        .order_by(PriceTick.time)
    )
    ticks = result.scalars().all()

    if not ticks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NO_DATA", "message": "No data for specified period"},
        )

    # Convert to DataFrame for statistics
    df = pd.DataFrame(
        [
            {
                "jet_fuel": float(t.jet_fuel_spot),
                "heating_oil": float(t.heating_oil_futures),
                "brent": float(t.brent_crude_futures),
                "wti": float(t.wti_crude_futures),
                "crack_spread": float(t.crack_spread),
                "volatility": float(t.volatility_index),
            }
            for t in ticks
        ]
    )

    # Calculate statistics for each instrument
    instruments = {
        "jet_fuel": "Jet Fuel Spot",
        "heating_oil": "Heating Oil Futures",
        "brent": "Brent Crude Futures",
        "wti": "WTI Crude Futures",
        "crack_spread": "Crack Spread",
        "volatility": "Volatility Index",
    }

    statistics = []
    for col, name in instruments.items():
        stats = PriceStatistics(
            instrument=name,
            mean=df[col].mean(),
            median=df[col].median(),
            std_dev=df[col].std(),
            min=df[col].min(),
            max=df[col].max(),
            count=len(df),
        )
        statistics.append(stats)

    logger.info(
        "statistics_calculated",
        user_id=str(current_user.id),
        days=days,
        observations=len(df),
    )

    return MarketDataStatsResponse(
        period_start=start_date,
        period_end=end_date,
        statistics=statistics,
    )


@router.get("/sources", response_model=list[str])
async def get_data_sources(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> list[str]:
    """Get list of available data sources.

    Accessible to all authenticated users.
    """
    result = await db.execute(
        select(PriceTick.source).distinct()
    )
    sources = [row[0] for row in result.all()]

    return sources
